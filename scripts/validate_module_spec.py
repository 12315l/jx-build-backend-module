#!/usr/bin/env python3
"""Validate a module specification; never fill missing business decisions."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from _common import Report, absolute, read_text, print_report


ALLOWED_STATUS = {"draft", "ready", "authorized", "implemented", "verified"}
ALLOWED_PROFILES = {"quick_crud", "standard_relation", "business_workflow", "statistics_query"}
ALLOWED_OPERATION_MODES = {"create_new", "enhance_existing", "audit_only"}
ALLOWED_TABLE_STRATEGIES = {"create_table", "alter_existing", "reuse_existing", "no_table"}
ALLOWED_QUERY_IMPL = {"mybatis_plus", "custom_dao", "mapper_xml"}
ALLOWED_ACTION_ACCESS = {"authenticated", "authority", "public"}
PLACEHOLDER_RE = re.compile(r"(__FILL__|unresolved|\$\{[^}]+\}|\bXX\b)", re.IGNORECASE)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="只读校验低代码后台模块规格")
    parser.add_argument("spec_file")
    parser.add_argument("--gate", choices=("analysis", "generation"), default="generation")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser.parse_args()


def load_document(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    text = read_text(path)
    if path.suffix.lower() == ".json":
        try:
            data = json.loads(text)
            return data if isinstance(data, dict) else None, None if isinstance(data, dict) else "根节点必须是对象"
        except json.JSONDecodeError as exc:
            return None, f"JSON 解析失败：{exc}"
    try:
        import yaml  # type: ignore
    except ImportError:
        return None, "缺少 PyYAML；请在 Skill 运行环境安装 PyYAML，或提供 JSON 规格"
    try:
        data = yaml.safe_load(text)
    except Exception as exc:  # parser-specific error type is optional
        return None, f"YAML 解析失败：{exc}"
    return data if isinstance(data, dict) else None, None if isinstance(data, dict) else "根节点必须是映射对象"


def get(data: dict[str, Any], path: str, default: Any = None) -> Any:
    current: Any = data
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return default
        current = current[part]
    return current


def unresolved(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip() or bool(PLACEHOLDER_RE.search(value))
    return False


def walk(value: Any, path: str = "") -> list[tuple[str, Any]]:
    rows: list[tuple[str, Any]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else str(key)
            rows.extend(walk(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            rows.extend(walk(child, f"{path}[{index}]"))
    else:
        rows.append((path, value))
    return rows


def validate(path: Path, gate: str) -> Report:
    report = Report("validate-module-spec", str(path))
    if not path.is_file():
        report.add("blocker", "SPEC_MISSING", "模块规格文件不存在", str(path))
        return report
    data, error = load_document(path)
    if error or data is None:
        report.add("blocker", "SPEC_PARSE_FAILED", error or "无法读取规格")
        return report

    required_roots = (
        "specification",
        "module_identity",
        "roles",
        "persistence",
        "template_capability_switches",
        "queries",
        "business_actions",
        "requirement_traceability",
        "verification",
    )
    missing_roots = [key for key in required_roots if key not in data]
    if missing_roots:
        report.add("blocker", "ROOT_SECTIONS_MISSING", "规格缺少必需根节点", "、".join(missing_roots))
    else:
        report.add("pass", "ROOT_SECTIONS_PRESENT", "规格必需根节点完整")

    status = get(data, "specification.status")
    if status not in ALLOWED_STATUS:
        report.add("blocker", "INVALID_STATUS", "规格状态无效", str(status))
    else:
        report.add("pass", "STATUS_VALID", "规格状态有效", str(status))

    profile = get(data, "module_identity.generation_profile")
    operation_mode = get(data, "module_identity.operation_mode")
    table_strategy = get(data, "module_identity.table_strategy")
    if profile not in ALLOWED_PROFILES:
        report.add("blocker" if gate == "generation" else "warning", "PROFILE_UNRESOLVED", "生成档位尚未确认", str(profile))
    if operation_mode not in ALLOWED_OPERATION_MODES:
        report.add("blocker" if gate == "generation" else "warning", "OPERATION_MODE_UNRESOLVED", "实施方式尚未确认", str(operation_mode))
    if table_strategy not in ALLOWED_TABLE_STRATEGIES:
        report.add("blocker" if gate == "generation" else "warning", "TABLE_STRATEGY_UNRESOLVED", "数据表策略尚未确认", str(table_strategy))

    pascal = get(data, "module_identity.pascal_name")
    camel = get(data, "module_identity.camel_name")
    snake = get(data, "module_identity.snake_name")
    name_errors = []
    if not isinstance(pascal, str) or not re.fullmatch(r"[A-Z][A-Za-z0-9]*", pascal):
        name_errors.append("pascal_name")
    if not isinstance(camel, str) or not re.fullmatch(r"[a-z][A-Za-z0-9]*", camel):
        name_errors.append("camel_name")
    if not isinstance(snake, str) or not re.fullmatch(r"[a-z][a-z0-9_]*", snake):
        name_errors.append("snake_name")
    if name_errors:
        report.add("blocker" if gate == "generation" else "warning", "NAMES_UNRESOLVED", "模块四种命名尚未完成", "、".join(name_errors))
    else:
        report.add("pass", "NAMES_VALID", "模块命名格式有效")

    all_placeholders = [item_path for item_path, value in walk(data) if isinstance(value, str) and PLACEHOLDER_RE.search(value)]
    if all_placeholders:
        report.add(
            "blocker" if gate == "generation" else "warning",
            "PLACEHOLDERS_PRESENT",
            "规格仍包含模板变量或未决标记",
            "、".join(all_placeholders[:20]),
        )
    else:
        report.add("pass", "NO_PLACEHOLDERS", "规格不含模板变量或未决标记")

    switches = get(data, "template_capability_switches", {})
    unresolved_switches = [key for key, value in switches.items() if not isinstance(value, bool)] if isinstance(switches, dict) else ["all"]
    if unresolved_switches:
        report.add(
            "blocker" if gate == "generation" else "warning",
            "CAPABILITY_SWITCHES_UNRESOLVED",
            "模板能力开关必须逐项决定为启用或关闭",
            "、".join(unresolved_switches),
        )
    else:
        report.add("pass", "CAPABILITY_SWITCHES_RESOLVED", "模板能力开关已全部决定")

    roles = get(data, "roles", [])
    valid_roles = [role for role in roles if isinstance(role, dict) and role.get("role_name") and role.get("operations")]
    if not valid_roles:
        report.add("blocker" if gate == "generation" else "warning", "ROLES_INCOMPLETE", "未形成有效角色、操作和数据范围规格")
    else:
        report.add("pass", "ROLES_PRESENT", "已定义角色操作", str(len(valid_roles)))

    fields = get(data, "persistence.fields", [])
    table_required = table_strategy in {"create_table", "alter_existing"} and profile != "statistics_query"
    valid_fields = []
    field_errors = []
    for index, field in enumerate(fields if isinstance(fields, list) else []):
        if not isinstance(field, dict):
            field_errors.append(f"fields[{index}]")
            continue
        needed = ("business_name", "property_name", "column_name", "java_type", "sql_type")
        missing = [key for key in needed if unresolved(field.get(key))]
        if missing:
            field_errors.append(f"fields[{index}]:{','.join(missing)}")
        else:
            valid_fields.append(field)
    if table_required and not valid_fields:
        report.add("blocker" if gate == "generation" else "warning", "FIELDS_INCOMPLETE", "持久化模块缺少完整业务字段", "；".join(field_errors[:10]))
    elif field_errors:
        report.add("blocker" if gate == "generation" else "warning", "FIELD_ROWS_INCOMPLETE", "存在未完成字段定义", "；".join(field_errors[:10]))
    else:
        report.add("pass", "FIELDS_ACCEPTABLE", "字段定义满足当前表策略", str(len(valid_fields)))

    association_fields = [
        field
        for field in valid_fields
        if isinstance(field.get("association"), dict)
        and field["association"].get("enabled") is True
        and not unresolved(field["association"].get("target_module"))
        and not unresolved(field["association"].get("target_entity"))
        and not unresolved(field["association"].get("target_property"))
    ]
    if profile == "standard_relation" and not association_fields:
        report.add(
            "blocker" if gate == "generation" else "warning",
            "RELATION_ASSOCIATION_MISSING",
            "关联档位必须明确至少一个真实关联模块、实体和目标属性",
        )
    elif association_fields:
        report.add("pass", "RELATION_ASSOCIATIONS_PRESENT", "已定义真实关联字段", str(len(association_fields)))

    queries = get(data, "queries", [])
    query_errors = []
    valid_queries = []
    for index, query in enumerate(queries if isinstance(queries, list) else []):
        if not isinstance(query, dict):
            query_errors.append(f"queries[{index}]")
            continue
        needed = ("query_id", "name", "endpoint", "http_method", "request_type", "implementation")
        missing = [key for key in needed if unresolved(query.get(key))]
        if query.get("implementation") not in ALLOWED_QUERY_IMPL:
            missing.append("implementation")
        if missing:
            query_errors.append(f"queries[{index}]:{','.join(sorted(set(missing)))}")
        else:
            valid_queries.append(query)
    if not valid_queries:
        report.add("blocker" if gate == "generation" else "warning", "QUERIES_INCOMPLETE", "未形成有效查询规格", "；".join(query_errors[:10]))
    elif query_errors:
        report.add("blocker" if gate == "generation" else "warning", "QUERY_ROWS_INCOMPLETE", "存在未完成查询定义", "；".join(query_errors[:10]))
    else:
        report.add("pass", "QUERIES_VALID", "查询规格结构有效", str(len(valid_queries)))

    frontend = get(data, "frontend_contract", {})
    frontend_in_scope = isinstance(frontend, dict) and frontend.get("in_scope") is True
    frontend_contract_complete = not frontend_in_scope
    if frontend_in_scope:
        frontend_errors = []
        if frontend.get("source_status") not in {"existing", "planned"}:
            frontend_errors.append("source_status")
        if not frontend.get("frontend_roots"):
            frontend_errors.append("frontend_roots")
        pagination = frontend.get("pagination", {})
        if not isinstance(pagination, dict) or unresolved(pagination.get("list_key")) or unresolved(pagination.get("total_key")):
            frontend_errors.append("pagination")
        response_mappings = frontend.get("response_mappings", [])
        valid_response_mappings = [
            row
            for row in response_mappings
            if isinstance(row, dict)
            and not unresolved(row.get("frontend_property"))
            and row.get("backend_source") in {"entity", "vo", "aggregate", "frontend_transform"}
            and not unresolved(row.get("evidence"))
        ]
        if not valid_response_mappings:
            frontend_errors.append("response_mappings")
        if frontend.get("source_status") == "existing" and not (frontend.get("page_files") or frontend.get("service_files")):
            frontend_errors.append("existing_source_files")
        permission_errors = []
        for index, row in enumerate(frontend.get("button_permissions", [])):
            if not isinstance(row, dict) or not any(row.values()):
                continue
            required = ("action", "controller_authority", "permission_sql_code", "frontend_token")
            if any(unresolved(row.get(key)) for key in required) or row.get("substring_collision_checked") is not True:
                permission_errors.append(str(index))
        if permission_errors:
            frontend_errors.append("button_permissions:" + ",".join(permission_errors))
        if frontend_errors:
            report.add(
                "blocker" if gate == "generation" else "warning",
                "FRONTEND_CONTRACT_INCOMPLETE",
                "前端在范围内，但请求响应或权限契约尚未完成",
                "、".join(frontend_errors),
            )
        else:
            frontend_contract_complete = True
            report.add("pass", "FRONTEND_CONTRACT_COMPLETE", "前端数据与权限契约结构完整")
    else:
        report.add("pass", "FRONTEND_CONTRACT_NOT_REQUIRED", "本模块未将前端契约纳入当前规格范围")

    actions = get(data, "business_actions", [])
    valid_actions = []
    action_errors = []
    for index, action in enumerate(actions if isinstance(actions, list) else []):
        if not isinstance(action, dict):
            action_errors.append(f"business_actions[{index}]")
            continue
        needed = ("action_id", "name", "endpoint", "http_method", "access", "allowed_roles")
        missing = [key for key in needed if unresolved(action.get(key))]
        if action.get("access") not in ALLOWED_ACTION_ACCESS:
            missing.append("access")
        if action.get("access") == "authority" and unresolved(action.get("authority")):
            missing.append("authority")
        if missing:
            action_errors.append(f"business_actions[{index}]:{','.join(sorted(set(missing)))}")
        else:
            valid_actions.append(action)
    if action_errors:
        report.add(
            "blocker" if gate == "generation" else "warning",
            "ACTION_ROWS_INCOMPLETE",
            "存在未完成的业务动作访问或权限定义",
            "；".join(action_errors[:10]),
        )
    if profile == "business_workflow" and not valid_actions:
        report.add("blocker" if gate == "generation" else "warning", "WORKFLOW_ACTIONS_MISSING", "业务流程档位必须定义专用动作")

    if profile == "business_workflow":
        state_enabled = get(data, "state_machine.enabled") is True
        transactions = get(data, "transactions", [])
        if not state_enabled:
            report.add("blocker" if gate == "generation" else "warning", "STATE_MACHINE_MISSING", "业务流程档位必须明确状态机")
        else:
            state_property = get(data, "state_machine.state_property")
            state_field = next((field for field in valid_fields if field.get("property_name") == state_property), None)
            states = get(data, "state_machine.states", [])
            state_codes = [state.get("code") for state in states if isinstance(state, dict) and not unresolved(state.get("code"))]
            state_errors = []
            if state_field is None:
                state_errors.append("state_property_not_in_fields")
            if not state_codes or len(state_codes) != len(set(map(str, state_codes))):
                state_errors.append("state_codes_missing_or_duplicate")
            if state_field is not None:
                java_type = str(state_field.get("java_type") or "")
                numeric_types = {"Integer", "Long", "Short", "Byte", "BigDecimal", "Double", "Float"}
                if java_type in numeric_types and any(not isinstance(code, (int, float)) or isinstance(code, bool) for code in state_codes):
                    state_errors.append("state_code_type")
                if java_type == "String" and any(not isinstance(code, str) for code in state_codes):
                    state_errors.append("state_code_type")
            known_codes = {str(code) for code in state_codes}
            for action in valid_actions:
                referenced = list(action.get("source_states") or []) + [action.get("target_state")]
                if any(str(code) not in known_codes for code in referenced if code is not None and code != ""):
                    state_errors.append(f"action_state:{action.get('action_id')}")
            action_ids = {str(action.get("action_id")) for action in valid_actions}
            transitions = get(data, "state_machine.transitions", [])
            for transition in transitions if isinstance(transitions, list) else []:
                if not isinstance(transition, dict):
                    state_errors.append("transition")
                    continue
                if str(transition.get("action_id")) not in action_ids:
                    state_errors.append(f"transition_action:{transition.get('transition_id')}")
                referenced = list(transition.get("from_states") or []) + [transition.get("to_state")]
                if any(str(code) not in known_codes for code in referenced if code is not None and code != ""):
                    state_errors.append(f"transition_state:{transition.get('transition_id')}")
            if state_errors:
                report.add(
                    "blocker" if gate == "generation" else "warning",
                    "STATE_MACHINE_INCONSISTENT",
                    "状态字段、保存值、业务动作或转换定义不一致",
                    "、".join(sorted(set(state_errors))),
                )
            else:
                report.add("pass", "STATE_MACHINE_CONSISTENT", "状态字段、保存值、动作与转换定义一致", str(len(state_codes)))
        if not isinstance(transactions, list) or not transactions:
            report.add("warning", "TRANSACTIONS_UNRESOLVED", "业务流程档位尚未定义事务；若确为单记录动作需给出说明")

    mandatory_files = get(data, "generated_files.mandatory", [])
    bad_paths = []
    for value in mandatory_files if isinstance(mandatory_files, list) else []:
        if not isinstance(value, str):
            bad_paths.append(str(value))
            continue
        normalized = value.replace("\\", "/")
        if not normalized.startswith("base-framework/src/main/java/system/store/functionModule/"):
            bad_paths.append(value)
        if not normalized.endswith((".java", ".sql")):
            bad_paths.append(value)
    if bad_paths:
        report.add("blocker", "OUTPUT_PATH_INVALID", "存在超出固定业务输出根或类型不正确的必选文件", "、".join(bad_paths[:10]))
    elif mandatory_files:
        report.add("pass", "OUTPUT_PATHS_VALID", "必选业务文件均位于固定 Java/SQL 输出范围")
    else:
        report.add("blocker" if gate == "generation" else "warning", "OUTPUT_FILES_MISSING", "未定义必选输出文件")

    conditional = get(data, "generated_files.conditional", {})
    bad_conditional_paths = []
    if isinstance(conditional, dict):
        for key in ("dto_files", "vo_files"):
            for value in conditional.get(key, []) if isinstance(conditional.get(key, []), list) else []:
                normalized = value.replace("\\", "/") if isinstance(value, str) else ""
                if not normalized.startswith("base-framework/src/main/java/system/store/functionModule/") or not normalized.endswith(".java"):
                    bad_conditional_paths.append(str(value))
        mapper_xml = conditional.get("mapper_xml")
        if mapper_xml:
            normalized = mapper_xml.replace("\\", "/") if isinstance(mapper_xml, str) else ""
            if not normalized.startswith("base-framework/src/main/resources/mapper/function/") or not normalized.endswith(".xml"):
                bad_conditional_paths.append(str(mapper_xml))
    if bad_conditional_paths:
        report.add("blocker", "CONDITIONAL_OUTPUT_PATH_INVALID", "DTO、VO 或 Mapper XML 输出路径不符合平台约定", "、".join(bad_conditional_paths[:10]))
    elif isinstance(conditional, dict):
        report.add("pass", "CONDITIONAL_OUTPUT_PATHS_VALID", "条件输出文件路径符合平台约定")

    unresolved_questions = get(data, "unresolved_questions", [])
    if unresolved_questions:
        report.add("blocker" if gate == "generation" else "warning", "UNRESOLVED_QUESTIONS", "规格仍有未决问题", str(len(unresolved_questions)))
    if gate == "generation":
        authorized = get(data, "specification.implementation_authorized") is True
        if status not in {"authorized", "implemented", "verified"} or not authorized:
            report.add("blocker", "IMPLEMENTATION_NOT_AUTHORIZED", "规格尚未达到实施授权门禁")
    else:
        report.add("pass", "ANALYSIS_GATE", "当前仅执行分析门禁，不授权写入项目")

    report.add("unverified", "SEMANTIC_VALIDATION", "脚本验证结构与硬规则；业务真实性、代码证据和状态含义仍需由 Skill 复核")
    report.data = {
        "spec_file": str(path),
        "gate": gate,
        "status": status,
        "generation_profile": profile,
        "operation_mode": operation_mode,
        "table_strategy": table_strategy,
        "valid_role_count": len(valid_roles),
        "valid_field_count": len(valid_fields),
        "valid_query_count": len(valid_queries),
        "valid_action_count": len(valid_actions),
        "frontend_contract_in_scope": frontend_in_scope,
        "frontend_contract_complete": frontend_contract_complete,
        "placeholder_paths": all_placeholders,
        "generation_allowed": gate == "generation" and not any(item.level == "blocker" for item in report.findings),
    }
    return report


def main() -> int:
    args = parse_args()
    return print_report(validate(absolute(args.spec_file), args.gate), args.format)


if __name__ == "__main__":
    raise SystemExit(main())
