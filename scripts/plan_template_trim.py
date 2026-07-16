#!/usr/bin/env python3
"""Create a read-only KeyModule capability trimming plan from a module specification."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from _common import Report, absolute, read_text, relative, resolve_backend, print_report
from validate_module_spec import get, load_document


CAPABILITIES: dict[str, dict[str, Any]] = {
    "public_details": {"endpoint": "/free/details", "service": ["searchDetails"], "permissions": []},
    "public_page": {"endpoint": "/free/page", "service": ["searchFreePage"], "permissions": []},
    "admin_page": {"endpoint": "/page", "service": ["searchPage"], "permissions": [":base"]},
    "create": {"endpoint": "/create", "service": ["createNewRow"], "permissions": [":create"]},
    "edit": {"endpoint": "/edit", "service": ["editRow"], "permissions": [":edit"]},
    "remove": {"endpoint": "/remove", "service": ["removeRows"], "permissions": [":remove"]},
    "recover": {"endpoint": "/recover", "service": ["recoverRows"], "permissions": []},
    "batch_status": {"endpoint": "/batch/status", "service": ["updateStatus"], "permissions": []},
    "batch_sort": {"endpoint": "/batch/sort", "service": ["updateSort"], "permissions": []},
    "low_code_metadata": {"endpoint": "/metadata", "service": ["getModuleMetadata"], "permissions": []},
    "excel_export": {"endpoint": "/export", "service": [], "permissions": [":export"], "entity_token": "ExcelProperty"},
    "excel_import": {"endpoint": "/import", "service": [], "permissions": [":import"], "entity_token": "ExcelProperty"},
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="按模块规格生成 KeyModule 能力裁剪计划；不修改代码")
    parser.add_argument("project_root")
    parser.add_argument("spec_file")
    parser.add_argument("--module-name", help="可选；默认读取规格 pascal_name")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser.parse_args()


def plan(project_root: Path, spec_file: Path, override_name: str | None) -> Report:
    report = Report("plan-template-trim", f"{project_root}::{spec_file}")
    data, error = load_document(spec_file) if spec_file.is_file() else (None, "规格文件不存在")
    if error or data is None:
        report.add("blocker", "SPEC_PARSE_FAILED", error or "无法读取规格", str(spec_file))
        return report
    backend, function_root = resolve_backend(project_root)
    if backend is None or function_root is None:
        report.add("blocker", "FUNCTION_ROOT_MISSING", "未找到 system.store.functionModule 源码根")
        return report

    pascal = (override_name or str(get(data, "module_identity.pascal_name") or "")).removesuffix("Module")
    if not pascal:
        report.add("blocker", "MODULE_NAME_MISSING", "模块名称未确认")
        return report
    module_root = function_root / f"{pascal}Module"
    controller = module_root / "controller" / f"{pascal}Controller.java"
    service = module_root / "service" / f"{pascal}Service.java"
    entity = module_root / "model" / "entity" / f"{pascal}.java"
    sql_files = sorted((module_root / "db").glob("*.sql")) if (module_root / "db").is_dir() else []
    module_exists = module_root.is_dir()
    controller_text = read_text(controller) if controller.is_file() else ""
    service_text = read_text(service) if service.is_file() else ""
    entity_text = read_text(entity) if entity.is_file() else ""
    sql_text = "\n".join(read_text(path) for path in sql_files)

    switches = get(data, "template_capability_switches", {})
    if not isinstance(switches, dict):
        report.add("blocker", "SWITCHES_MISSING", "模板能力开关节点不存在")
        return report
    unresolved = [key for key, value in switches.items() if not isinstance(value, bool)]
    if unresolved:
        report.add("blocker", "SWITCHES_UNRESOLVED", "模板能力开关尚未逐项决定", "、".join(unresolved))

    if switches.get("admin_details") is True:
        report.add(
            "warning",
            "ADMIN_DETAILS_NOT_IN_KEYMODULE",
            "当前 KeyModule 没有独立受保护的后台详情接口；必须按真实需求新增或关闭，不能误用公开详情",
        )

    actions = []
    for key, definition in CAPABILITIES.items():
        enabled = switches.get(key)
        endpoint = definition["endpoint"]
        endpoint_present = endpoint in controller_text if module_exists else None
        service_presence = {
            method: (method in service_text if module_exists else None) for method in definition.get("service", [])
        }
        permission_presence = {
            token: (token in sql_text if module_exists else None) for token in definition.get("permissions", [])
        }
        entity_token = definition.get("entity_token")
        entity_present = entity_token in entity_text if entity_token and module_exists else None

        if enabled is True:
            decision = "keep_or_implement"
            if module_exists and not endpoint_present:
                report.add("warning", "ENABLED_ENDPOINT_MISSING", f"已启用能力缺少接口：{key}", endpoint)
            elif module_exists:
                report.add("pass", "ENABLED_ENDPOINT_PRESENT", f"已启用能力接口存在：{key}", endpoint)
        elif enabled is False:
            decision = "remove"
            if module_exists and endpoint_present:
                report.add("warning", "DISABLED_ENDPOINT_PRESENT", f"已关闭能力仍存在接口，必须裁剪：{key}", endpoint)
            elif module_exists:
                report.add("pass", "DISABLED_ENDPOINT_ABSENT", f"已关闭能力接口不存在：{key}")
        else:
            decision = "resolve_before_trim"

        actions.append(
            {
                "capability": key,
                "enabled": enabled,
                "decision": decision,
                "controller_endpoint": endpoint,
                "endpoint_present": endpoint_present,
                "service_methods": service_presence,
                "permission_tokens": permission_presence,
                "entity_annotation_present": entity_present,
                "synchronize_layers": ["controller", "service", "entity", "permission_sql", "frontend_calls"],
            }
        )

    permission_sql = switches.get("permission_sql")
    if permission_sql is False and sql_text and "a_permission_table" in sql_text:
        report.add("warning", "PERMISSION_SQL_DISABLED_BUT_PRESENT", "权限 SQL 已关闭，但模块脚本仍包含权限写入")
    if permission_sql is True and module_exists and "a_permission_table" not in sql_text:
        report.add("warning", "PERMISSION_SQL_ENABLED_BUT_MISSING", "权限 SQL 已启用，但模块脚本未发现权限写入")

    permission_menu = get(data, "permission_menu", {})
    permission_menu_strategy = permission_menu.get("strategy") if isinstance(permission_menu, dict) else None
    if permission_sql is True and module_exists:
        legacy_parent_fallback = (
            "permission_name` = '系统管理'" in sql_text
            or "permission_name = '系统管理'" in sql_text
            or "IFNULL(@parent_id" in sql_text
        )
        if legacy_parent_fallback:
            report.add(
                "warning",
                "LEGACY_FIXED_PARENT_MENU",
                "KeyModule 的系统管理固定父菜单回退仍然存在，裁剪时必须替换为规格中的目录—页面—按钮结构",
            )
        if permission_menu_strategy == "create_module_directory" and "manage:dir:" not in sql_text:
            report.add(
                "warning",
                "MODULE_DIRECTORY_PERMISSION_MISSING",
                "规格要求模块自建父级目录，但当前 SQL 尚未注册目录权限",
            )
        if isinstance(permission_menu, dict) and permission_menu.get("idempotent_by_permission_code") is True:
            if "WHERE NOT EXISTS" not in sql_text.upper():
                report.add(
                    "warning",
                    "PERMISSION_SQL_REPEAT_GUARD_MISSING",
                    "权限 SQL 尚未按权限标识增加重复执行保护",
                )

    report.add("unverified", "BUSINESS_ENHANCEMENT_REQUIRED", "裁剪计划只处理 KeyModule 通用能力，业务字段、DTO/VO、专用动作、事务和复杂查询仍须按规格实现")
    report.data = {
        "module": pascal,
        "module_directory": relative(module_root, project_root),
        "module_exists": module_exists,
        "capability_actions": actions,
        "permission_sql_enabled": permission_sql,
        "permission_menu_strategy": permission_menu_strategy,
        "permission_menu": permission_menu,
        "business_actions": get(data, "business_actions", []),
        "generated_files": get(data, "generated_files", {}),
        "writes_performed": False,
    }
    return report


def main() -> int:
    args = parse_args()
    return print_report(plan(absolute(args.project_root), absolute(args.spec_file), args.module_name), args.format)


if __name__ == "__main__":
    raise SystemExit(main())
