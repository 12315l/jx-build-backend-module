#!/usr/bin/env python3
"""Validate project-level requirement-to-code traceability without writing files."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from _common import Report, absolute, print_report, read_text


FEATURE_ID = re.compile(r"^REQ-[A-Z][A-Z0-9_]*-\d{3}$")
FLOW_ID = re.compile(r"^FLOW-\d{3}$")
STEP_ID = re.compile(r"^(FLOW-\d{3})-S\d{2}$")
MODULE_ID = re.compile(r"^MODULE-\d{3}$")
DECISION_ID = re.compile(r"^DECISION-\d{3}$")
STATUSES = {"platform_existing", "partial", "to_develop", "to_remove", "verified", "to_confirm"}
OWNERSHIPS = {"business_module", "base_module", "frontend_only", "offline"}
OPERATION_TYPES = {"online", "offline", "mixed"}
PLACEHOLDER = re.compile(r"(?:__FILL__|unresolved|\$\{[^}]+\})", re.I)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="只读校验项目级需求到代码追踪文件")
    parser.add_argument("project_root")
    parser.add_argument("traceability_file")
    parser.add_argument("--gate", choices=("mapping", "verification"), default="mapping")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser.parse_args()


def load_document(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    text = read_text(path)
    if path.suffix.lower() == ".json":
        try:
            value = json.loads(text)
        except json.JSONDecodeError as exc:
            return None, f"JSON 解析失败：{exc}"
    else:
        try:
            import yaml  # type: ignore
        except ImportError:
            return None, "缺少 PyYAML；请安装 PyYAML，或使用 JSON 追踪文件"
        try:
            value = yaml.safe_load(text)
        except Exception as exc:
            return None, f"YAML 解析失败：{exc}"
    return (value, None) if isinstance(value, dict) else (None, "根节点必须是映射对象")


def missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip() or bool(PLACEHOLDER.search(value))
    return False


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def check_file(report: Report, project_root: Path, rel: Any, code: str, owner: str) -> Path | None:
    if missing(rel):
        return None
    path = project_root / str(rel)
    try:
        path.resolve().relative_to(project_root.resolve())
    except ValueError:
        report.add("blocker", "EVIDENCE_OUTSIDE_PROJECT", f"{owner} 的证据路径越出项目范围", str(rel))
        return None
    if not path.is_file():
        report.add("blocker", code, f"{owner} 引用的文件不存在", str(rel))
        return None
    return path


def require_text_marker(report: Report, path: Path | None, marker: Any, code: str, owner: str) -> None:
    if path is None or missing(marker):
        return
    if str(marker) not in read_text(path):
        report.add("blocker", code, f"{owner} 声明的代码标记未在文件中找到", f"{path}: {marker}")


def validate(project_root: Path, trace_file: Path, gate: str) -> Report:
    report = Report("validate-traceability", str(trace_file))
    if not project_root.is_dir():
        report.add("blocker", "PROJECT_ROOT_MISSING", "项目根目录不存在", str(project_root))
        return report
    if not trace_file.is_file():
        report.add("blocker", "TRACE_FILE_MISSING", "追踪文件不存在", str(trace_file))
        return report
    data, error = load_document(trace_file)
    if error or data is None:
        report.add("blocker", "TRACE_PARSE_FAILED", error or "追踪文件无法解析")
        return report

    meta = data.get("traceability") if isinstance(data.get("traceability"), dict) else {}
    for key in ("version", "status", "project_name", "requirement_version", "requirement_source"):
        if missing(meta.get(key)):
            report.add("blocker", "TRACE_METADATA_INCOMPLETE", f"追踪信息缺少 {key}")

    features = as_list(data.get("features"))
    flows = as_list(data.get("flows"))
    modules = as_list(data.get("modules"))
    decisions = as_list(data.get("decisions"))
    if not features:
        report.add("blocker", "FEATURES_EMPTY", "角色功能清单为空")
    if not flows:
        report.add("blocker", "FLOWS_EMPTY", "核心流程清单为空")

    feature_ids: set[str] = set()
    step_ids: set[str] = set()
    mapped_feature_ids: set[str] = set()
    mapped_step_ids: set[str] = set()
    coverage_counts: dict[str, int] = {status: 0 for status in sorted(STATUSES)}

    for index, item in enumerate(features, 1):
        owner = f"features[{index}]"
        if not isinstance(item, dict):
            report.add("blocker", "FEATURE_NOT_OBJECT", f"{owner} 不是对象")
            continue
        req_id = str(item.get("requirement_id") or "")
        if not FEATURE_ID.fullmatch(req_id):
            report.add("blocker", "FEATURE_ID_INVALID", f"{owner} 的需求编号不符合规则", req_id)
        elif req_id in feature_ids:
            report.add("blocker", "FEATURE_ID_DUPLICATE", "需求编号重复", req_id)
        else:
            feature_ids.add(req_id)
        for key in ("role", "name", "original_requirement", "action_type", "data_scope", "target_module"):
            if missing(item.get(key)):
                report.add("blocker", "FEATURE_INCOMPLETE", f"{req_id or owner} 缺少 {key}")
        status = str(item.get("coverage_status") or "")
        if status not in STATUSES:
            report.add("blocker", "COVERAGE_STATUS_INVALID", f"{req_id or owner} 覆盖状态无效", status)
        else:
            coverage_counts[status] += 1
        ownership = str(item.get("ownership") or "")
        if ownership not in OWNERSHIPS:
            report.add("blocker", "OWNERSHIP_INVALID", f"{req_id or owner} 归属类型无效", ownership)
        no_code = item.get("no_new_backend_code") is True
        mapping = item.get("mapping") if isinstance(item.get("mapping"), dict) else {}
        evidence = [str(v) for v in as_list(item.get("evidence_files")) if not missing(v)]
        if no_code:
            if missing(item.get("no_code_reason")):
                report.add("blocker", "NO_CODE_REASON_MISSING", f"{req_id or owner} 未说明无需新增后台代码的原因")
        elif status in {"platform_existing", "partial", "verified"}:
            if missing(mapping.get("controller_file")) or missing(mapping.get("service_file")):
                report.add("blocker", "CODE_DESTINATION_MISSING", f"{req_id or owner} 缺少 Controller 或 Service 去向")
        if status in {"platform_existing", "partial", "verified", "to_remove"} and not evidence:
            report.add("blocker", "FEATURE_EVIDENCE_MISSING", f"{req_id or owner} 的覆盖结论没有代码证据")
        if status == "to_remove" and missing(item.get("disposition")):
            report.add("blocker", "REMOVAL_DISPOSITION_MISSING", f"{req_id or owner} 未说明移除范围")
        if not as_list(item.get("acceptance_cases")):
            report.add("blocker", "FEATURE_ACCEPTANCE_MISSING", f"{req_id or owner} 没有验收用例")

        controller = check_file(report, project_root, mapping.get("controller_file"), "CONTROLLER_FILE_MISSING", req_id)
        service = check_file(report, project_root, mapping.get("service_file"), "SERVICE_FILE_MISSING", req_id)
        require_text_marker(report, controller, mapping.get("endpoint"), "ENDPOINT_NOT_FOUND", req_id)
        require_text_marker(report, service, mapping.get("service_method"), "SERVICE_METHOD_NOT_FOUND", req_id)
        for rel in [*evidence, *[str(v) for v in as_list(mapping.get("data_files")) if not missing(v)]]:
            check_file(report, project_root, rel, "EVIDENCE_FILE_MISSING", req_id)

    flow_ids: set[str] = set()
    for flow_index, flow in enumerate(flows, 1):
        if not isinstance(flow, dict):
            report.add("blocker", "FLOW_NOT_OBJECT", f"flows[{flow_index}] 不是对象")
            continue
        flow_id = str(flow.get("flow_id") or "")
        if not FLOW_ID.fullmatch(flow_id):
            report.add("blocker", "FLOW_ID_INVALID", "流程编号不符合规则", flow_id)
        elif flow_id in flow_ids:
            report.add("blocker", "FLOW_ID_DUPLICATE", "流程编号重复", flow_id)
        else:
            flow_ids.add(flow_id)
        if missing(flow.get("name")):
            report.add("blocker", "FLOW_NAME_MISSING", f"{flow_id or flow_index} 缺少流程名称")
        unknown_sources = set(map(str, as_list(flow.get("source_requirement_ids")))) - feature_ids
        if unknown_sources:
            report.add("blocker", "FLOW_SOURCE_UNKNOWN", f"{flow_id} 引用了不存在的需求", ", ".join(sorted(unknown_sources)))
        orders: set[int] = set()
        for step_index, step in enumerate(as_list(flow.get("steps")), 1):
            if not isinstance(step, dict):
                report.add("blocker", "FLOW_STEP_NOT_OBJECT", f"{flow_id} 的步骤不是对象")
                continue
            step_id = str(step.get("flow_step_id") or "")
            match = STEP_ID.fullmatch(step_id)
            if not match or match.group(1) != flow_id:
                report.add("blocker", "FLOW_STEP_ID_INVALID", f"{flow_id} 的步骤编号不符合规则", step_id)
            elif step_id in step_ids:
                report.add("blocker", "FLOW_STEP_ID_DUPLICATE", "流程步骤编号重复", step_id)
            else:
                step_ids.add(step_id)
            order = step.get("order")
            if not isinstance(order, int) or order <= 0 or order in orders:
                report.add("blocker", "FLOW_ORDER_INVALID", f"{step_id or flow_id} 的顺序必须是唯一正整数", str(order))
            else:
                orders.add(order)
            for key in ("actor", "original_step", "target_module"):
                if missing(step.get(key)):
                    report.add("blocker", "FLOW_STEP_INCOMPLETE", f"{step_id or flow_id} 缺少 {key}")
            op_type = str(step.get("operation_type") or "")
            if op_type not in OPERATION_TYPES:
                report.add("blocker", "FLOW_OPERATION_TYPE_INVALID", f"{step_id or flow_id} 的步骤类型无效", op_type)
            no_code = step.get("no_new_backend_code") is True
            mapping = step.get("mapping") if isinstance(step.get("mapping"), dict) else {}
            if no_code and missing(step.get("no_code_reason")):
                report.add("blocker", "FLOW_NO_CODE_REASON_MISSING", f"{step_id or flow_id} 未说明无需后台代码的原因")
            if op_type in {"online", "mixed"} and not no_code:
                if missing(mapping.get("controller_file")) or missing(mapping.get("service_file")):
                    report.add("blocker", "FLOW_CODE_DESTINATION_MISSING", f"{step_id or flow_id} 缺少 Controller 或 Service 去向")
            if op_type == "mixed" and missing(step.get("offline_confirmation")):
                report.add("blocker", "OFFLINE_CONFIRMATION_MISSING", f"{step_id or flow_id} 未说明线下事实由谁在线确认")
            if op_type == "offline" and not missing(step.get("state_change")):
                report.add("blocker", "OFFLINE_STATE_CHANGE", f"{step_id or flow_id} 是纯线下步骤，不能声明系统状态变化")
            if not as_list(step.get("acceptance_cases")):
                report.add("blocker", "FLOW_ACCEPTANCE_MISSING", f"{step_id or flow_id} 没有验收用例")
            controller = check_file(report, project_root, mapping.get("controller_file"), "FLOW_CONTROLLER_FILE_MISSING", step_id)
            service = check_file(report, project_root, mapping.get("service_file"), "FLOW_SERVICE_FILE_MISSING", step_id)
            require_text_marker(report, controller, mapping.get("endpoint"), "FLOW_ENDPOINT_NOT_FOUND", step_id)
            require_text_marker(report, service, mapping.get("service_method"), "FLOW_SERVICE_METHOD_NOT_FOUND", step_id)
            for rel in [*as_list(step.get("evidence_files")), *as_list(mapping.get("data_files"))]:
                check_file(report, project_root, rel, "FLOW_EVIDENCE_FILE_MISSING", step_id)

    module_ids: set[str] = set()
    for index, module in enumerate(modules, 1):
        if not isinstance(module, dict):
            report.add("blocker", "MODULE_NOT_OBJECT", f"modules[{index}] 不是对象")
            continue
        module_id = str(module.get("module_id") or "")
        if not MODULE_ID.fullmatch(module_id) or module_id in module_ids:
            report.add("blocker", "MODULE_ID_INVALID_OR_DUPLICATE", "模块编号无效或重复", module_id)
        module_ids.add(module_id)
        ownership = str(module.get("ownership") or "")
        package_root = str(module.get("package_root") or "")
        if ownership == "business_module" and not package_root.startswith("system.store.functionModule."):
            report.add("blocker", "BUSINESS_PACKAGE_ROOT_INVALID", f"{module_id} 未落入标准业务包根", package_root)
        req_refs = set(map(str, as_list(module.get("requirement_ids"))))
        step_refs = set(map(str, as_list(module.get("flow_step_ids"))))
        unknown_req = req_refs - feature_ids
        unknown_steps = step_refs - step_ids
        if unknown_req:
            report.add("blocker", "MODULE_REQUIREMENT_UNKNOWN", f"{module_id} 引用了不存在的需求", ", ".join(sorted(unknown_req)))
        if unknown_steps:
            report.add("blocker", "MODULE_FLOW_STEP_UNKNOWN", f"{module_id} 引用了不存在的流程步骤", ", ".join(sorted(unknown_steps)))
        mapped_feature_ids.update(req_refs)
        mapped_step_ids.update(step_refs)

    no_code_features = {str(item.get("requirement_id")) for item in features if isinstance(item, dict) and item.get("no_new_backend_code") is True}
    no_code_steps = {
        str(step.get("flow_step_id"))
        for flow in flows if isinstance(flow, dict)
        for step in as_list(flow.get("steps")) if isinstance(step, dict) and step.get("no_new_backend_code") is True
    }
    missing_feature_ownership = feature_ids - mapped_feature_ids - no_code_features
    missing_step_ownership = step_ids - mapped_step_ids - no_code_steps
    if missing_feature_ownership:
        report.add("blocker", "FEATURE_MODULE_MAPPING_MISSING", "存在未归入模块的角色功能", ", ".join(sorted(missing_feature_ownership)))
    if missing_step_ownership:
        report.add("blocker", "FLOW_MODULE_MAPPING_MISSING", "存在未归入模块的流程步骤", ", ".join(sorted(missing_step_ownership)))

    decision_ids: set[str] = set()
    for item in decisions:
        if not isinstance(item, dict):
            continue
        decision_id = str(item.get("decision_id") or "")
        if not DECISION_ID.fullmatch(decision_id) or decision_id in decision_ids:
            report.add("blocker", "DECISION_ID_INVALID_OR_DUPLICATE", "决策编号无效或重复", decision_id)
        decision_ids.add(decision_id)

    if gate == "verification":
        verification = data.get("verification") if isinstance(data.get("verification"), dict) else {}
        for key in ("all_features_mapped", "all_flow_steps_mapped", "evidence_paths_checked", "module_specs_created", "implementation_verified"):
            if verification.get(key) is not True:
                report.add("blocker", "VERIFICATION_GATE_INCOMPLETE", f"verification.{key} 尚未完成")
        if coverage_counts.get("partial", 0) or coverage_counts.get("to_develop", 0) or coverage_counts.get("to_confirm", 0):
            report.add("blocker", "UNFINISHED_COVERAGE", "仍有部分实现、待开发或待确认的需求，不能标记为已验证")

    if not report.findings:
        report.add("pass", "TRACEABILITY_VALID", "项目级需求到代码追踪结构完整")
    else:
        report.add("pass", "TRACEABILITY_PARSED", "追踪文件已完成结构化解析")
    report.data = {
        "feature_count": len(feature_ids),
        "flow_count": len(flow_ids),
        "flow_step_count": len(step_ids),
        "module_count": len(module_ids),
        "decision_count": len(decision_ids),
        "coverage_counts": coverage_counts,
        "gate": gate,
    }
    return report


def main() -> int:
    args = parse_args()
    return print_report(validate(absolute(args.project_root), absolute(args.traceability_file), args.gate), args.format)


if __name__ == "__main__":
    raise SystemExit(main())

