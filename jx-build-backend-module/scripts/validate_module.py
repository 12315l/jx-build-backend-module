#!/usr/bin/env python3
"""Validate a generated or existing backend module across Java, SQL, permissions, and Mapper XML."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any

from _common import Report, absolute, iter_files, read_text, relative, resolve_backend, print_report
from inspect_module import inspect as inspect_module
from plan_template_trim import CAPABILITIES
from validate_module_spec import get, load_document


FIELD_RE = re.compile(r"\bprivate\s+([A-Za-z0-9_<>?,. ]+)\s+([A-Za-z][A-Za-z0-9_]*)\s*;")
TABLE_NAME_RE = re.compile(r"@TableName\(\s*\"([^\"]+)\"\s*\)")
CREATE_TABLE_RE = re.compile(
    r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?`?([a-zA-Z0-9_]+)`?",
    re.IGNORECASE,
)
AUTHORITY_RE = re.compile(r"hasAuthority\(\s*'([^']+)'\s*\)")
XML_ID_RE = re.compile(r"<(?:select|insert|update|delete)\b[^>]*\bid=\"([^\"]+)\"", re.IGNORECASE)
DAO_METHOD_RE = re.compile(r"(?:^|\n)\s*(?:public\s+)?[\w<>, ?\[\].]+\s+(\w+)\s*\([^;{}]*\)\s*;", re.MULTILINE)
PLACEHOLDER_RE = re.compile(r"\$\{[^}]+\}|__FILL__|\bunresolved\b|\bXX\b|\bKey(Module|Controller|Service|Dao)?\b")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="只读验收低代码后台模块的目录、代码、SQL 与规格一致性")
    parser.add_argument("project_root")
    parser.add_argument("module_name", help="例如 CourseOrder 或 CourseOrderModule")
    parser.add_argument("--spec", help="可选模块规格 YAML/JSON")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser.parse_args()


def camel_to_snake(value: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", value).lower()


def entity_fields(path: Path) -> dict[str, str]:
    fields: dict[str, str] = {}
    transient = False
    in_block_comment = False
    for line in read_text(path).splitlines():
        stripped = line.strip()
        if in_block_comment:
            if "*/" in stripped:
                in_block_comment = False
            continue
        if stripped.startswith("/*"):
            if "*/" not in stripped:
                in_block_comment = True
            continue
        if stripped.startswith("//") or not stripped:
            continue
        if "@TableField" in line and "exist" in line and "false" in line:
            transient = True
            continue
        match = FIELD_RE.search(line)
        if not match:
            continue
        java_type = match.group(1).strip().split(".")[-1]
        name = match.group(2)
        if not transient and name not in {"serialVersionUID"}:
            fields[name] = java_type
        transient = False
    return fields


def sql_columns(sql_text: str) -> dict[str, str]:
    table = re.search(
        r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?`?[a-zA-Z0-9_]+`?\s*\((.*?)\)\s*(?:ENGINE|COMMENT|comment|;)",
        sql_text,
        re.IGNORECASE | re.DOTALL,
    )
    body = table.group(1) if table else ""
    columns: dict[str, str] = {}
    for line in body.splitlines():
        match = re.match(r"\s*`?([a-zA-Z0-9_]+)`?\s+([a-zA-Z]+(?:\([^)]*\))?)", line)
        if not match or match.group(1).lower() in {"primary", "unique", "key", "constraint", "index"}:
            continue
        columns[match.group(1)] = match.group(2).lower()
    return columns


def registered_authorities(sql_text: str) -> set[str]:
    authorities = set(
        re.findall(
            r"manage:dir:[a-zA-Z0-9_]+|manage:(?:page|btn):[a-zA-Z0-9_]+:[a-zA-Z0-9_]+",
            sql_text,
        )
    )
    raw_match = re.search(r"SET\s+@raw_key\s*=\s*'([^']+)'", sql_text, re.IGNORECASE)
    if not raw_match:
        return authorities
    raw_key = raw_match.group(1)
    parts = raw_key.split("_")
    key = raw_key if len(parts) == 1 else parts[0] + parts[-1][:1].upper() + parts[-1][1:]
    if "manage:dir:" in sql_text:
        authorities.add(f"manage:dir:{key}")
    if "manage:page:" in sql_text and "':base'" in sql_text:
        authorities.add(f"manage:page:{key}:base")
    for suffix in re.findall(r"manage:btn:.*?':([a-zA-Z0-9_]+)'", sql_text, re.IGNORECASE | re.DOTALL):
        authorities.add(f"manage:btn:{key}:{suffix}")
    return authorities


def java_sql_type_compatible(java_type: str, sql_type: str) -> bool:
    base_java = re.sub(r"<.*>", "", java_type).split(".")[-1]
    base_sql = sql_type.split("(")[0].lower()
    allowed = {
        "Integer": {"int", "integer", "tinyint", "smallint", "bigint"},
        "Long": {"bigint", "int", "integer"},
        "String": {"varchar", "char", "text", "longtext", "mediumtext"},
        "Date": {"datetime", "date", "timestamp"},
        "LocalDate": {"date"},
        "LocalDateTime": {"datetime", "timestamp"},
        "BigDecimal": {"decimal", "numeric"},
        "Double": {"double", "float", "decimal"},
        "Float": {"float", "double", "decimal"},
        "Boolean": {"tinyint", "bit", "boolean"},
    }
    return base_sql in allowed.get(base_java, {base_sql})


def dao_methods(dao_text: str) -> set[str]:
    methods: set[str] = set()
    for match in DAO_METHOD_RE.finditer(dao_text):
        method = match.group(1)
        prefix = dao_text[max(0, match.start() - 400) : match.start()]
        after_last_end = prefix.rsplit(";", 1)[-1]
        if any(token in after_last_end for token in ("@Select", "@Insert", "@Update", "@Delete")):
            continue
        methods.add(method)
    return methods


def validate(project_root: Path, module_name: str, spec_file: Path | None) -> Report:
    report = Report("validate-module", f"{project_root}::{module_name}")
    base = inspect_module(project_root, module_name, None)
    for item in base.findings:
        report.add(item.level, f"STRUCTURE_{item.code}", item.message, item.evidence)
    if not base.data.get("exists"):
        report.data = {"structure": base.data, "writes_performed": False}
        return report

    backend, function_root = resolve_backend(project_root)
    if backend is None or function_root is None:
        report.add("blocker", "FUNCTION_ROOT_MISSING", "未找到业务模块根")
        return report
    pascal = str(base.data.get("module_name"))
    module_root = function_root / f"{pascal}Module"
    controller = module_root / "controller" / f"{pascal}Controller.java"
    service = module_root / "service" / f"{pascal}Service.java"
    dao = module_root / "dao" / f"{pascal}Dao.java"
    entity = module_root / "model" / "entity" / f"{pascal}.java"
    sql_files = sorted((module_root / "db").glob("*.sql")) if (module_root / "db").is_dir() else []
    mapper_root = backend / "src" / "main" / "resources" / "mapper" / "function"
    mapper_files = []
    namespace_token = f"system.store.functionModule.{pascal}Module.dao."
    for path in iter_files(mapper_root, {".xml"}):
        if namespace_token in read_text(path):
            mapper_files.append(path)

    python_files = [path for path in module_root.rglob("*.py")]
    if python_files:
        report.add("blocker", "PYTHON_IN_BUSINESS_MODULE", "业务模块中禁止出现 Python 文件", "、".join(relative(path, project_root) for path in python_files))
    else:
        report.add("pass", "BUSINESS_OUTPUT_TYPES_VALID", "业务模块未包含 Python 文件")

    source_files = [path for path in module_root.rglob("*") if path.is_file() and path.suffix.lower() in {".java", ".sql", ".xml"}]
    placeholder_files = [relative(path, project_root) for path in source_files if PLACEHOLDER_RE.search(read_text(path))]
    if placeholder_files:
        report.add("blocker", "PLACEHOLDER_REMAINS", "生成文件仍包含模板占位符", "、".join(placeholder_files))
    else:
        report.add("pass", "NO_PLACEHOLDERS", "生成文件中未发现模板占位符")

    controller_text = read_text(controller) if controller.is_file() else ""
    service_text = read_text(service) if service.is_file() else ""
    dao_text = read_text(dao) if dao.is_file() else ""
    entity_text = read_text(entity) if entity.is_file() else ""
    sql_text = "\n".join(read_text(path) for path in sql_files)

    entity_map = entity_fields(entity) if entity.is_file() else {}
    column_map = sql_columns(sql_text)
    missing_columns = [name for name in entity_map if camel_to_snake(name) not in column_map]
    extra_columns = [name for name in column_map if name not in {camel_to_snake(field) for field in entity_map}]
    type_mismatches = []
    for field, java_type in entity_map.items():
        column = camel_to_snake(field)
        if column in column_map and not java_sql_type_compatible(java_type, column_map[column]):
            type_mismatches.append(f"{field}:{java_type}/{column_map[column]}")
    if missing_columns:
        report.add("blocker", "ENTITY_COLUMNS_MISSING", "实体字段在建表 SQL 中缺少对应列", "、".join(missing_columns))
    elif entity_map and column_map:
        report.add("pass", "ENTITY_SQL_FIELDS_ALIGNED", "实体字段与 SQL 列名称一致", str(len(entity_map)))
    if extra_columns:
        report.add("warning", "SQL_COLUMNS_NOT_IN_MAIN_ENTITY", "SQL 存在主实体未映射列，需确认是否刻意保留", "、".join(extra_columns))
    if type_mismatches:
        report.add("blocker", "ENTITY_SQL_TYPE_MISMATCH", "实体字段与 SQL 类型不兼容", "、".join(type_mismatches))
    if "id" in entity_map and entity_map.get("id") == "Integer" and column_map.get("id", "").startswith("bigint"):
        report.add("warning", "INTEGER_BIGINT_ID", "主键存在 Integer/BIGINT 组合，当前平台可见此历史模式，但新增模块应确认取值范围")

    table_match = TABLE_NAME_RE.search(entity_text)
    create_match = CREATE_TABLE_RE.search(sql_text)
    if table_match and create_match and table_match.group(1) != create_match.group(1):
        report.add("blocker", "TABLE_NAME_MISMATCH", "实体表名与建表 SQL 不一致", f"{table_match.group(1)} != {create_match.group(1)}")
    elif table_match and create_match:
        report.add("pass", "TABLE_NAME_ALIGNED", "实体表名与建表 SQL 一致", table_match.group(1))

    authorities = set(AUTHORITY_RE.findall(controller_text))
    sql_authorities = registered_authorities(sql_text)
    legacy_parent_fallback = bool(
        re.search(r"`?permission_name`?\s*=\s*'系统管理'", sql_text, re.IGNORECASE)
        or re.search(r"IFNULL\s*\(\s*@(?:parent|directory)[a-zA-Z0-9_]*\s*,\s*\d+\s*\)", sql_text, re.IGNORECASE)
    )
    if legacy_parent_fallback:
        report.add(
            "blocker",
            "FIXED_PARENT_MENU_FALLBACK",
            "权限 SQL 仍按显示名称查找父菜单或回退到固定编号，必须改为按权限标识创建或解析父目录",
        )
    missing_permission_sql = sorted(authorities - sql_authorities)
    if missing_permission_sql and sql_text:
        report.add("unverified", "PERMISSION_SQL_NOT_LOCAL", "Controller 权限未在模块 SQL 中找到对应注册，需继续核对全局初始化脚本或实际数据库", "、".join(missing_permission_sql))
    elif authorities and sql_text:
        report.add("pass", "PERMISSIONS_ALIGNED", "Controller 权限均可在模块 SQL 中找到", str(len(authorities)))
    elif authorities:
        report.add("unverified", "PERMISSION_SQL_NOT_LOCAL", "模块存在接口权限，但本模块无可核对的权限 SQL")

    custom_methods = dao_methods(dao_text) if dao.is_file() else set()
    xml_ids: set[str] = set()
    for path in mapper_files:
        xml_ids.update(XML_ID_RE.findall(read_text(path)))
    missing_xml_ids = sorted(custom_methods - xml_ids) if mapper_files else []
    orphan_xml_ids = sorted(xml_ids - custom_methods) if mapper_files else []
    if missing_xml_ids:
        report.add("blocker", "DAO_XML_METHOD_MISSING", "DAO 自定义方法缺少同名 Mapper XML 语句", "、".join(missing_xml_ids))
    if orphan_xml_ids:
        report.add("blocker", "XML_DAO_METHOD_MISSING", "Mapper XML 语句缺少同名 DAO 方法", "、".join(orphan_xml_ids))
    if mapper_files and not missing_xml_ids and not orphan_xml_ids:
        report.add("pass", "DAO_MAPPER_ALIGNED", "DAO 自定义方法与 Mapper XML 语句一致", str(len(xml_ids)))

    spec_data: dict[str, Any] | None = None
    if spec_file is not None:
        spec_data, error = load_document(spec_file) if spec_file.is_file() else (None, "规格文件不存在")
        if error or spec_data is None:
            report.add("blocker", "SPEC_PARSE_FAILED", error or "无法读取规格", str(spec_file))
        else:
            spec_pascal = str(get(spec_data, "module_identity.pascal_name") or "")
            if spec_pascal != pascal:
                report.add("blocker", "SPEC_MODULE_MISMATCH", "规格模块名与目标模块不一致", f"{spec_pascal} != {pascal}")
            switches = get(spec_data, "template_capability_switches", {})
            if isinstance(switches, dict):
                for key, definition in CAPABILITIES.items():
                    enabled = switches.get(key)
                    endpoint = definition["endpoint"]
                    present = endpoint in controller_text
                    if enabled is False and present:
                        report.add("blocker", "DISABLED_ENDPOINT_PRESENT", f"规格关闭的模板接口仍然存在：{key}", endpoint)
                    if enabled is True and not present:
                        report.add("blocker", "ENABLED_ENDPOINT_MISSING", f"规格启用的模板接口不存在：{key}", endpoint)
                if switches.get("permission_sql") is True and missing_permission_sql:
                    report.add("blocker", "SPEC_PERMISSION_SQL_MISSING", "规格要求权限 SQL，但接口权限未在模块 SQL 中完整注册", "、".join(missing_permission_sql))
                if switches.get("permission_sql") is True:
                    permission_menu = get(spec_data, "permission_menu", {})
                    expected_menu_codes: set[str] = set()
                    if isinstance(permission_menu, dict):
                        strategy = permission_menu.get("strategy")
                        if strategy == "create_module_directory":
                            directory = permission_menu.get("directory", {})
                            if isinstance(directory, dict) and directory.get("permission_code"):
                                expected_menu_codes.add(str(directory["permission_code"]))
                        page = permission_menu.get("page", {})
                        if isinstance(page, dict) and page.get("permission_code"):
                            expected_menu_codes.add(str(page["permission_code"]))
                        buttons = permission_menu.get("buttons", [])
                        for button in buttons if isinstance(buttons, list) else []:
                            if isinstance(button, dict) and button.get("permission_code"):
                                expected_menu_codes.add(str(button["permission_code"]))
                    missing_menu_codes = sorted(expected_menu_codes - sql_authorities)
                    if missing_menu_codes:
                        report.add(
                            "blocker",
                            "PERMISSION_MENU_RECORD_MISSING",
                            "规格中的目录、页面或按钮权限未在模块 SQL 中完整注册",
                            "、".join(missing_menu_codes),
                        )
                    elif expected_menu_codes:
                        report.add(
                            "pass",
                            "PERMISSION_MENU_RECORDS_PRESENT",
                            "规格中的目录、页面和按钮权限均已注册",
                            str(len(expected_menu_codes)),
                        )

                    if isinstance(permission_menu, dict) and permission_menu.get("idempotent_by_permission_code") is True:
                        permission_insert_count = len(
                            re.findall(r"INSERT\s+INTO\s+`?a_permission_table`?", sql_text, re.IGNORECASE)
                        )
                        guarded_insert_count = len(re.findall(r"\bNOT\s+EXISTS\s*\(", sql_text, re.IGNORECASE))
                        if permission_insert_count and guarded_insert_count < permission_insert_count:
                            report.add(
                                "blocker",
                                "PERMISSION_SQL_NOT_IDEMPOTENT",
                                "权限写入未全部按权限标识进行重复执行保护",
                                f"权限写入 {permission_insert_count} 条，存在性保护 {guarded_insert_count} 条",
                            )
                        elif permission_insert_count:
                            report.add("pass", "PERMISSION_SQL_IDEMPOTENT", "权限写入具备按权限标识重复执行保护")

                    if isinstance(permission_menu, dict) and permission_menu.get("strategy") == "create_module_directory":
                        id_lookups = len(
                            re.findall(
                                r"SELECT\s+`?id`?\s+FROM\s+`?a_permission_table`?.*?`?permission_code`?\s*=",
                                sql_text,
                                re.IGNORECASE | re.DOTALL,
                            )
                        )
                        if id_lookups < 2:
                            report.add(
                                "blocker",
                                "PERMISSION_PARENT_CHAIN_UNVERIFIED",
                                "独立模块必须在插入或复用后分别按权限标识重新取得目录和页面编号",
                                str(id_lookups),
                            )

            spec_fields = get(spec_data, "persistence.fields", [])
            missing_spec_properties = []
            missing_spec_columns = []
            for field in spec_fields if isinstance(spec_fields, list) else []:
                if not isinstance(field, dict):
                    continue
                prop = str(field.get("property_name") or "")
                column = str(field.get("column_name") or "")
                if prop and prop not in entity_map:
                    missing_spec_properties.append(prop)
                if column and column not in column_map:
                    missing_spec_columns.append(column)
            if missing_spec_properties:
                report.add("blocker", "SPEC_ENTITY_FIELDS_MISSING", "规格字段尚未写入实体", "、".join(missing_spec_properties))
            if missing_spec_columns:
                report.add("blocker", "SPEC_SQL_COLUMNS_MISSING", "规格字段尚未写入 SQL", "、".join(missing_spec_columns))

            mandatory = get(spec_data, "generated_files.mandatory", [])
            missing_files = []
            for value in mandatory if isinstance(mandatory, list) else []:
                if not isinstance(value, str):
                    continue
                candidate = project_root / Path(value)
                if not candidate.exists() and Path(value).parts and Path(value).parts[0] == backend.name:
                    candidate = backend / Path(*Path(value).parts[1:])
                if not candidate.is_file():
                    missing_files.append(value)
            if missing_files:
                report.add("blocker", "SPEC_FILES_MISSING", "规格必选文件未全部生成", "、".join(missing_files))
            elif mandatory:
                report.add("pass", "SPEC_FILES_PRESENT", "规格必选文件均存在", str(len(mandatory)))

            conditional = get(spec_data, "generated_files.conditional", {})
            conditional_paths = []
            if isinstance(conditional, dict):
                for key in ("dto_files", "vo_files"):
                    values = conditional.get(key, [])
                    if isinstance(values, list):
                        conditional_paths.extend(value for value in values if isinstance(value, str) and value)
                mapper_xml = conditional.get("mapper_xml")
                if isinstance(mapper_xml, str) and mapper_xml:
                    conditional_paths.append(mapper_xml)
            missing_conditional = []
            for value in conditional_paths:
                candidate = project_root / Path(value)
                if not candidate.exists() and Path(value).parts and Path(value).parts[0] == backend.name:
                    candidate = backend / Path(*Path(value).parts[1:])
                if not candidate.is_file():
                    missing_conditional.append(value)
            if missing_conditional:
                report.add("blocker", "SPEC_CONDITIONAL_FILES_MISSING", "规格要求的 DTO、VO 或 Mapper XML 尚未生成", "、".join(missing_conditional))
            elif conditional_paths:
                report.add("pass", "SPEC_CONDITIONAL_FILES_PRESENT", "规格要求的条件文件均存在", str(len(conditional_paths)))

            actions = get(spec_data, "business_actions", [])
            for action in actions if isinstance(actions, list) else []:
                if not isinstance(action, dict) or not action.get("name"):
                    continue
                endpoint = str(action.get("endpoint") or "")
                if endpoint and endpoint not in controller_text:
                    report.add("blocker", "BUSINESS_ACTION_ENDPOINT_MISSING", f"业务动作接口缺失：{action.get('name')}", endpoint)
                authority = str(action.get("authority") or "")
                if action.get("access") == "authority" and authority:
                    if authority not in authorities:
                        report.add("blocker", "BUSINESS_ACTION_AUTHORITY_MISSING", f"业务动作缺少指定 Controller 权限：{action.get('name')}", authority)
                    if authority not in sql_authorities:
                        report.add("blocker", "BUSINESS_ACTION_PERMISSION_SQL_MISSING", f"业务动作缺少指定权限 SQL：{action.get('name')}", authority)
                if action.get("transaction_required") is True and "@Transactional" not in service_text:
                    report.add("blocker", "REQUIRED_TRANSACTION_MISSING", f"业务动作要求事务，但 Service 未发现事务声明：{action.get('name')}")

            queries = get(spec_data, "queries", [])
            for query in queries if isinstance(queries, list) else []:
                if not isinstance(query, dict) or not query.get("name"):
                    continue
                endpoint = str(query.get("endpoint") or "")
                if endpoint and endpoint not in controller_text:
                    report.add("blocker", "QUERY_ENDPOINT_MISSING", f"规格查询接口缺失：{query.get('name')}", endpoint)

    if re.search(r"DROP\s+TABLE", sql_text, re.IGNORECASE):
        report.add("warning", "DESTRUCTIVE_SQL_PRESENT", "模块 SQL 包含删表语句，只能用于明确的新表初始化且不得自动执行")
    report.add("unverified", "BACKEND_COMPILE", "当前验收未执行 Maven 编译；编译状态需单独验证")
    report.add("unverified", "BUSINESS_INVARIANTS", "状态、数量、越权、重复操作和线下确认仍需结合规格与测试逐项验证")

    report.data = {
        "module": pascal,
        "module_directory": relative(module_root, project_root),
        "spec_file": str(spec_file) if spec_file else None,
        "entity_fields": entity_map,
        "sql_columns": column_map,
        "authorities": sorted(authorities),
        "sql_authorities": sorted(sql_authorities),
        "mapper_xml_files": [relative(path, project_root) for path in mapper_files],
        "dao_custom_methods": sorted(custom_methods),
        "mapper_statement_ids": sorted(xml_ids),
        "writes_performed": False,
        "compile_executed": False,
        "sql_executed": False,
    }
    return report


def main() -> int:
    args = parse_args()
    spec = absolute(args.spec) if args.spec else None
    return print_report(validate(absolute(args.project_root), args.module_name, spec), args.format)


if __name__ == "__main__":
    raise SystemExit(main())
