#!/usr/bin/env python3
"""Preview or safely scaffold the five KeyModule files from an authorized specification."""

from __future__ import annotations

import argparse
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any

from _common import Report, absolute, read_text, relative, resolve_backend, print_report
from validate_module_spec import get, load_document, validate as validate_spec


NAME_RE = re.compile(r"[A-Z][A-Za-z0-9]*")
PERMISSION_COLUMNS = (
    "(`permission_name`, `permission_code`, `permission_match_type`, `permission_type`, `router_path`, "
    "`api_path`, `is_allowed`, `parent_id`, `parent_router`, `icon`, `remark`, `status`, `order_by`)"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="预演或执行 KeyModule 五文件安全脚手架")
    parser.add_argument("project_root")
    parser.add_argument("spec_file")
    parser.add_argument("--execute", action="store_true", help="实际创建目标模块；默认仅预演")
    parser.add_argument(
        "--confirm-authorized",
        action="store_true",
        help="确认用户已授权实施；仅与 --execute 同时使用",
    )
    parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser.parse_args()


def sql_string(value: Any) -> str:
    if value is None or value == "":
        return "NULL"
    return "'" + str(value).replace("'", "''") + "'"


def render_permission_sql(data: dict[str, Any]) -> str:
    menu = get(data, "permission_menu", {})
    if not isinstance(menu, dict) or menu.get("enabled") is not True:
        return ""
    strategy = str(menu.get("strategy") or "")
    page = menu.get("page", {}) if isinstance(menu.get("page"), dict) else {}
    match_type = int(menu.get("match_type", 2))
    lines = ["-- 按模块规格注册目录、页面与按钮；以权限标识保证重复执行安全"]

    if strategy == "create_module_directory":
        directory = menu.get("directory", {}) if isinstance(menu.get("directory"), dict) else {}
        lines.extend(
            [
                f"SET @directory_code = {sql_string(directory.get('permission_code'))};",
                f"SET @directory_route = {sql_string(directory.get('router_path'))};",
                f"INSERT INTO `a_permission_table` {PERMISSION_COLUMNS}",
                "SELECT "
                + ", ".join(
                    [
                        sql_string(directory.get("name")),
                        "@directory_code",
                        str(match_type),
                        "0",
                        "@directory_route",
                        "NULL",
                        "0",
                        "NULL",
                        "NULL",
                        sql_string(directory.get("icon")),
                        sql_string(f"{directory.get('name', '')}目录"),
                        "1",
                        str(directory.get("order_by", 0)),
                    ]
                ),
                "WHERE NOT EXISTS (SELECT 1 FROM `a_permission_table` WHERE `permission_code` = @directory_code);",
            ]
        )
    else:
        existing_parent = menu.get("existing_parent", {}) if isinstance(menu.get("existing_parent"), dict) else {}
        lines.extend(
            [
                "-- 规格要求挂到既有目录；目录缺失时后续页面和按钮均不会写入，不允许回退到其他菜单。",
                f"SET @directory_code = {sql_string(existing_parent.get('permission_code'))};",
                f"SET @directory_route = {sql_string(page.get('parent_router'))};",
            ]
        )

    lines.extend(
        [
            "SET @directory_id = (SELECT `id` FROM `a_permission_table` WHERE `permission_code` = @directory_code ORDER BY `id` LIMIT 1);",
            f"SET @page_code = {sql_string(page.get('permission_code'))};",
            f"SET @page_route = {sql_string(page.get('router_path'))};",
            f"INSERT INTO `a_permission_table` {PERMISSION_COLUMNS}",
            "SELECT "
            + ", ".join(
                [
                    sql_string(page.get("name")),
                    "@page_code",
                    str(match_type),
                    "1",
                    "@page_route",
                    "NULL",
                    "0",
                    "@directory_id",
                    "@directory_route",
                    sql_string(page.get("icon")),
                    sql_string(f"{page.get('name', '')}页面"),
                    "1",
                    str(page.get("order_by", 0)),
                ]
            ),
            "WHERE @directory_id IS NOT NULL",
            "  AND NOT EXISTS (SELECT 1 FROM `a_permission_table` WHERE `permission_code` = @page_code);",
            "SET @page_id = (SELECT `id` FROM `a_permission_table` WHERE `permission_code` = @page_code ORDER BY `id` LIMIT 1);",
        ]
    )

    buttons = menu.get("buttons", [])
    for index, button in enumerate(buttons if isinstance(buttons, list) else []):
        if not isinstance(button, dict):
            continue
        variable = f"@button_code_{index + 1}"
        lines.extend(
            [
                f"SET {variable} = {sql_string(button.get('permission_code'))};",
                f"INSERT INTO `a_permission_table` {PERMISSION_COLUMNS}",
                "SELECT "
                + ", ".join(
                    [
                        sql_string(button.get("name")),
                        variable,
                        str(match_type),
                        "2",
                        "NULL",
                        "NULL",
                        "0",
                        "@page_id",
                        "@page_route",
                        "NULL",
                        sql_string(button.get("name")),
                        "1",
                        "0",
                    ]
                ),
                "WHERE @page_id IS NOT NULL",
                f"  AND NOT EXISTS (SELECT 1 FROM `a_permission_table` WHERE `permission_code` = {variable});",
            ]
        )
    return "\n".join(lines) + "\n"


def replacement_content(
    source: Path,
    text: str,
    pascal: str,
    camel: str,
    snake: str,
    chinese: str,
    data: dict[str, Any],
) -> str:
    if source.suffix.lower() == ".sql":
        table_sql = text.split("-- 自动注册菜单与按钮权限 SQL", 1)[0]
        table_sql = table_sql.replace("c_key_table", f"c_{snake}_table").replace("XX", chinese).rstrip()
        if get(data, "template_capability_switches.permission_sql") is not True:
            return table_sql + "\n"
        return table_sql + "\n\n" + render_permission_sql(data)
    result = text.replace("Key", pascal).replace("key", camel).replace("XX", chinese)
    return result.replace(f"c_{camel}_table", f"c_{snake}_table")


def template_plan(key_root: Path, target_root: Path, pascal: str, snake: str) -> list[tuple[Path, Path]]:
    return [
        (key_root / "controller" / "KeyController.java", target_root / "controller" / f"{pascal}Controller.java"),
        (key_root / "service" / "KeyService.java", target_root / "service" / f"{pascal}Service.java"),
        (key_root / "dao" / "KeyDao.java", target_root / "dao" / f"{pascal}Dao.java"),
        (key_root / "model" / "entity" / "Key.java", target_root / "model" / "entity" / f"{pascal}.java"),
        (key_root / "db" / "c_key_table.sql", target_root / "db" / f"c_{snake}_table.sql"),
    ]


def load_names(data: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        str(get(data, "module_identity.pascal_name") or "").strip(),
        str(get(data, "module_identity.camel_name") or "").strip(),
        str(get(data, "module_identity.snake_name") or "").strip(),
        str(get(data, "module_identity.chinese_name") or "").strip(),
    )


def build_report(project_root: Path, spec_file: Path, execute: bool, confirm_authorized: bool) -> Report:
    report = Report("scaffold-module", f"{project_root}::{spec_file}", read_only=not execute)
    if not project_root.is_dir():
        report.add("blocker", "PROJECT_ROOT_MISSING", "项目根目录不存在", str(project_root))
        return report
    data, error = load_document(spec_file) if spec_file.is_file() else (None, "规格文件不存在")
    if error or data is None:
        report.add("blocker", "SPEC_PARSE_FAILED", error or "无法读取规格", str(spec_file))
        return report

    gate_report = validate_spec(spec_file, "generation" if execute else "analysis")
    for item in gate_report.findings:
        if item.level == "blocker" or (execute and item.level == "warning"):
            report.add(item.level, f"SPEC_{item.code}", item.message, item.evidence)

    backend, function_root = resolve_backend(project_root)
    if backend is None or function_root is None:
        report.add("blocker", "FUNCTION_ROOT_MISSING", "未找到 system.store.functionModule 源码根")
        return report
    key_root = backend / "src" / "test" / "resources" / "KeyModule"
    module_maker = backend / "src" / "test" / "java" / "ModuleMaker.java"
    if not key_root.is_dir():
        report.add("blocker", "KEY_MODULE_MISSING", "未找到 KeyModule 模板", relative(key_root, project_root))
    if not module_maker.is_file():
        report.add("blocker", "MODULE_MAKER_MISSING", "未找到 ModuleMaker，无法核对当前生成契约", relative(module_maker, project_root))
    else:
        report.add("pass", "MODULE_MAKER_FOUND", "已定位 ModuleMaker 生成契约", relative(module_maker, project_root))

    pascal, camel, snake, chinese = load_names(data)
    name_errors = []
    if not NAME_RE.fullmatch(pascal):
        name_errors.append("pascal_name")
    if not re.fullmatch(r"[a-z][A-Za-z0-9]*", camel):
        name_errors.append("camel_name")
    if not re.fullmatch(r"[a-z][a-z0-9_]*", snake):
        name_errors.append("snake_name")
    if not chinese:
        name_errors.append("chinese_name")
    if name_errors:
        report.add("blocker", "MODULE_NAMES_INCOMPLETE", "脚手架所需命名不完整", "、".join(name_errors))
        return report
    if get(data, "module_identity.operation_mode") != "create_new":
        report.add("blocker", "NOT_CREATE_MODE", "脚手架只允许创建新模块；现有模块必须增量增强")

    target_root = (function_root / f"{pascal}Module").resolve()
    if target_root.parent != function_root.resolve():
        report.add("blocker", "TARGET_OUTSIDE_FUNCTION_ROOT", "目标目录超出 system.store.functionModule")
        return report
    if target_root.exists():
        report.add("blocker", "TARGET_EXISTS", "目标模块目录已存在，禁止覆盖", relative(target_root, project_root))

    plan = template_plan(key_root, target_root, pascal, snake)
    missing_sources = [source for source, _ in plan if not source.is_file()]
    if missing_sources:
        report.add("blocker", "TEMPLATE_FILES_MISSING", "KeyModule 五文件模板不完整", "、".join(relative(path, project_root) for path in missing_sources))
    else:
        report.add("pass", "TEMPLATE_FILES_COMPLETE", "KeyModule 五文件模板完整")

    if execute and not confirm_authorized:
        report.add("blocker", "CLI_AUTHORIZATION_MISSING", "执行模式必须显式提供 --confirm-authorized")
    if execute and not (
        get(data, "specification.implementation_authorized") is True
        and get(data, "specification.status") in {"authorized", "implemented", "verified"}
    ):
        report.add("blocker", "SPEC_NOT_AUTHORIZED", "规格未达到实施授权状态")

    report.data = {
        "mode": "execute" if execute else "preview",
        "backend": relative(backend, project_root) or ".",
        "module_maker": relative(module_maker, project_root),
        "key_module": relative(key_root, project_root),
        "target_module": relative(target_root, project_root),
        "canonical_package": f"system.store.functionModule.{pascal}Module",
        "replacement_map": {
            "pascal_token_Key": pascal,
            "camel_token_key": camel,
            "sql_token_key": snake,
            "business_token_XX": chinese,
        },
        "files": [
            {"source": relative(source, project_root), "target": relative(target, project_root)}
            for source, target in plan
        ],
        "sql_execution": "not_executed",
        "template_trim_required": True,
    }

    if any(item.level == "blocker" for item in report.findings):
        return report
    if not execute:
        report.add("pass", "PREVIEW_READY", "脚手架预演完成，未创建任何项目文件")
        report.add("warning", "TRIM_REQUIRED", "生成后必须按规格裁剪模板能力并完成业务字段与流程增强")
        return report

    temp_root: Path | None = None
    try:
        temp_root = Path(tempfile.mkdtemp(prefix=f".{pascal}Module.scaffold-", dir=function_root))
        if temp_root.resolve().parent != function_root.resolve():
            raise RuntimeError("temporary directory escaped function root")
        for source, target in plan:
            relative_target = target.relative_to(target_root)
            staged = temp_root / relative_target
            staged.parent.mkdir(parents=True, exist_ok=True)
            content = replacement_content(source, read_text(source), pascal, camel, snake, chinese, data)
            staged.write_text(content, encoding="utf-8", newline="\n")
        if target_root.exists():
            raise FileExistsError(str(target_root))
        temp_root.rename(target_root)
        temp_root = None
        report.add("pass", "SCAFFOLD_CREATED", "已创建 KeyModule 五文件 Java/SQL 骨架", relative(target_root, project_root))
        report.add("warning", "UNTRIMMED_TEMPLATE", "当前仅为模板骨架，尚未完成能力裁剪和业务增强，不得标记为代码完成")
    except Exception as exc:
        report.add("blocker", "SCAFFOLD_FAILED", "脚手架创建失败", str(exc))
    finally:
        if temp_root is not None and temp_root.exists() and temp_root.resolve().parent == function_root.resolve():
            shutil.rmtree(temp_root)
    return report


def main() -> int:
    args = parse_args()
    report = build_report(absolute(args.project_root), absolute(args.spec_file), args.execute, args.confirm_authorized)
    return print_report(report, args.format)


if __name__ == "__main__":
    raise SystemExit(main())
