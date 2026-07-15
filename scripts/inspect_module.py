#!/usr/bin/env python3
"""Inspect one functionModule package without writing project files."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from _common import Report, absolute, iter_files, normalize_module_name, read_text, relative, resolve_backend, print_report


PACKAGE_RE = re.compile(r"^\s*package\s+([\w.]+)\s*;", re.MULTILINE)
ENDPOINT_RE = re.compile(r"@(Get|Post|Put|Delete|Patch)Mapping(?:\(\s*\"([^\"]*)\"[^)]*\))?")
REQUEST_MAPPING_RE = re.compile(r"@RequestMapping\(\s*\"([^\"]+)\"")
AUTHORITY_RE = re.compile(r"hasAuthority\(\s*'([^']+)'\s*\)")
TABLE_RE = re.compile(r"@TableName\(\s*\"([^\"]+)\"\s*\)")
PLACEHOLDER_RE = re.compile(r"\$\{[^}]+\}|\bXX\b|\bKey(Module|Controller|Service|Dao)?\b")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="只读检查一个低代码后台业务模块")
    parser.add_argument("project_root")
    parser.add_argument("module_name", help="例如 CourseOrder 或 CourseOrderModule")
    parser.add_argument("--reference", help="可选相邻参考模块")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser.parse_args()


def expected_package(java_file: Path, java_root: Path) -> str | None:
    try:
        parts = java_file.parent.relative_to(java_root).parts
    except ValueError:
        return None
    return ".".join(parts)


def frontend_hits(project_root: Path, needles: list[str]) -> list[str]:
    hits: list[str] = []
    for child in project_root.iterdir():
        source = child / "src"
        if not (child / "package.json").is_file() or not source.is_dir():
            continue
        for path in iter_files(source, {".js", ".ts", ".vue", ".tsx", ".jsx"}, max_files=20_000):
            text = read_text(path)
            if any(needle and needle in text for needle in needles):
                hits.append(relative(path, project_root))
                if len(hits) >= 100:
                    return hits
    return hits


def inspect(project_root: Path, requested_name: str, reference: str | None) -> Report:
    pascal, directory_name = normalize_module_name(requested_name)
    report = Report("inspect-module", f"{project_root}::{directory_name or requested_name}")
    if not re.fullmatch(r"[A-Z][A-Za-z0-9]*", pascal):
        report.add("blocker", "INVALID_MODULE_NAME", "模块名必须是合法大驼峰英文名称", requested_name)
        return report

    backend, function_root = resolve_backend(project_root)
    if backend is None or function_root is None:
        report.add("blocker", "FUNCTION_ROOT_MISSING", "未找到 system.store.functionModule 源码根")
        return report
    java_root = backend / "src" / "main" / "java"
    module_root = function_root / directory_name
    duplicates = [path for path in function_root.iterdir() if path.is_dir() and path.name.lower() == directory_name.lower()]
    if len(duplicates) > 1:
        report.add("blocker", "DUPLICATE_MODULE", "发现大小写不同的同名模块", ", ".join(path.name for path in duplicates))
    if not module_root.is_dir():
        report.add("blocker", "MODULE_MISSING", "目标模块不存在；只读检查不会自动创建", relative(module_root, project_root))
        report.data = {
            "module_directory": relative(module_root, project_root),
            "canonical_package": f"system.store.functionModule.{directory_name}",
            "exists": False,
        }
        return report

    report.add("pass", "MODULE_FOUND", "已定位目标模块", relative(module_root, project_root))
    files = sorted(path for path in module_root.rglob("*") if path.is_file())
    java_files = [path for path in files if path.suffix == ".java"]
    sql_files = [path for path in files if path.suffix.lower() == ".sql"]

    expected = {
        "controller": module_root / "controller" / f"{pascal}Controller.java",
        "service": module_root / "service" / f"{pascal}Service.java",
        "dao": module_root / "dao" / f"{pascal}Dao.java",
        "entity": module_root / "model" / "entity" / f"{pascal}.java",
    }
    missing_standard = []
    for layer, path in expected.items():
        if path.is_file():
            report.add("pass", f"{layer.upper()}_FOUND", f"已找到标准 {layer} 文件", relative(path, project_root))
        else:
            missing_standard.append(layer)
            report.add("warning", f"{layer.upper()}_MISSING", f"未找到以模块主名称命名的 {layer} 文件", relative(path, project_root))
    if sql_files:
        report.add("pass", "SQL_FOUND", "模块内存在 SQL 文件", ", ".join(relative(path, project_root) for path in sql_files))
    else:
        report.add("warning", "SQL_MISSING", "模块内未发现 SQL 文件；需确认是复用表、统计模块还是缺失")

    package_mismatches = []
    placeholders = []
    endpoints = []
    authorities: set[str] = set()
    tables: set[str] = set()
    route_prefixes: set[str] = set()
    for path in java_files:
        text = read_text(path)
        package = PACKAGE_RE.search(text)
        expected_value = expected_package(path, java_root)
        if not package or package.group(1) != expected_value:
            package_mismatches.append(
                {"file": relative(path, project_root), "declared": package.group(1) if package else None, "expected": expected_value}
            )
        if PLACEHOLDER_RE.search(text):
            placeholders.append(relative(path, project_root))
        route_match = REQUEST_MAPPING_RE.search(text)
        prefix = route_match.group(1) if route_match else ""
        if prefix:
            route_prefixes.add(prefix)
        for match in ENDPOINT_RE.finditer(text):
            endpoints.append({"method": match.group(1).upper(), "path": prefix + (match.group(2) or ""), "file": relative(path, project_root)})
        authorities.update(AUTHORITY_RE.findall(text))
        tables.update(TABLE_RE.findall(text))
    for path in sql_files:
        if PLACEHOLDER_RE.search(read_text(path)):
            placeholders.append(relative(path, project_root))

    if package_mismatches:
        report.add("blocker", "PACKAGE_PATH_MISMATCH", "存在目录与 package 声明不一致的 Java 文件", str(len(package_mismatches)))
    else:
        report.add("pass", "PACKAGE_PATHS_VALID", "Java 文件目录与 package 声明一致")
    if placeholders:
        report.add("blocker", "TEMPLATE_PLACEHOLDER", "模块仍包含 KeyModule 占位内容", ", ".join(placeholders))
    else:
        report.add("pass", "NO_TEMPLATE_PLACEHOLDER", "未发现 Key、XX 或模板变量占位")

    mapper_root = backend / "src" / "main" / "resources" / "mapper" / "function"
    mapper_files = []
    namespace_token = f"system.store.functionModule.{directory_name}.dao."
    for path in iter_files(mapper_root, {".xml"}):
        text = read_text(path)
        if namespace_token in text:
            mapper_files.append(relative(path, project_root))
    if mapper_files:
        report.add("pass", "MAPPER_XML_FOUND", "已定位模块自定义 Mapper XML", ", ".join(mapper_files))
    else:
        report.add("unverified", "MAPPER_XML_ABSENT", "未发现模块 Mapper XML；简单查询可不需要")

    needles = sorted(route_prefixes) + [pascal, pascal[0].lower() + pascal[1:]]
    client_hits = frontend_hits(project_root, needles)
    frontend_contract = {
        "service_files": [path for path in client_hits if "/service/" in path.replace("\\", "/")],
        "config_files": [path for path in client_hits if "/config/" in path.replace("\\", "/")],
        "page_files": [path for path in client_hits if path.endswith(".vue")],
        "button_permission_files": [],
        "list_hook_files": [],
        "modal_hook_files": [],
    }
    for value in client_hits:
        path = project_root / Path(value)
        if not path.is_file():
            continue
        text = read_text(path)
        if "hasButtonPermission" in text:
            frontend_contract["button_permission_files"].append(value)
        if "useFetchList" in text:
            frontend_contract["list_hook_files"].append(value)
        if "useModalHandler" in text:
            frontend_contract["modal_hook_files"].append(value)
    if client_hits:
        report.add("pass", "FRONTEND_CALLS_FOUND", "发现可能关联的前端文件", str(len(client_hits)))
        if frontend_contract["service_files"] or frontend_contract["config_files"]:
            report.add(
                "pass",
                "FRONTEND_CONTRACT_EVIDENCE",
                "已分类模块服务调用与页面配置证据",
                f"service={len(frontend_contract['service_files'])}, config={len(frontend_contract['config_files'])}",
            )
    else:
        report.add("unverified", "FRONTEND_CALLS_NOT_FOUND", "未发现可确认的前端调用，需人工核对动态路由或命名差异")

    reference_data = None
    if reference:
        ref_pascal, ref_dir = normalize_module_name(reference)
        ref_path = function_root / ref_dir
        reference_data = {"name": ref_pascal, "directory": relative(ref_path, project_root), "exists": ref_path.is_dir()}
        if ref_path.is_dir():
            report.add("pass", "REFERENCE_MODULE_FOUND", "已定位相邻参考模块", relative(ref_path, project_root))
        else:
            report.add("warning", "REFERENCE_MODULE_MISSING", "指定的相邻参考模块不存在", relative(ref_path, project_root))

    report.add("unverified", "WORKTREE_STATUS", "脚本不调用 Git，写入前仍需单独检查用户未提交改动")
    report.data = {
        "backend": relative(backend, project_root) or ".",
        "module_name": pascal,
        "module_directory": relative(module_root, project_root),
        "canonical_package": f"system.store.functionModule.{directory_name}",
        "exists": True,
        "files": [relative(path, project_root) for path in files],
        "missing_standard_layers": missing_standard,
        "package_mismatches": package_mismatches,
        "endpoints": endpoints,
        "authorities": sorted(authorities),
        "tables": sorted(tables),
        "sql_files": [relative(path, project_root) for path in sql_files],
        "mapper_xml_files": mapper_files,
        "frontend_hits": client_hits,
        "frontend_contract": frontend_contract,
        "reference_module": reference_data,
    }
    return report


def main() -> int:
    args = parse_args()
    return print_report(inspect(absolute(args.project_root), args.module_name, args.reference), args.format)


if __name__ == "__main__":
    raise SystemExit(main())
