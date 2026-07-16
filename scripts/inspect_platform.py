#!/usr/bin/env python3
"""Inspect the low-code platform layout without modifying the project."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from _common import Report, absolute, backend_candidates, relative, print_report, read_text


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="只读扫描低代码平台目录与公共能力")
    parser.add_argument("project_root", help="项目根目录，或直接传入后台模块根目录")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser.parse_args()


def inspect(project_root: Path) -> Report:
    report = Report("inspect-platform", str(project_root))
    if not project_root.is_dir():
        report.add("blocker", "PROJECT_ROOT_MISSING", "项目根目录不存在", str(project_root))
        return report

    backends = backend_candidates(project_root)
    if not backends:
        report.add(
            "blocker",
            "FUNCTION_ROOT_MISSING",
            "未找到 system.store.functionModule 实际源码根",
            "检查项目根目录或后台模块目录",
        )
        return report
    if len(backends) > 1:
        report.add(
            "warning",
            "MULTIPLE_BACKENDS",
            "发现多个符合平台结构的后台目录，后续写入前必须明确目标",
            ", ".join(relative(path, project_root) for path in backends),
        )

    backend = backends[0]
    java_root = backend / "src" / "main" / "java"
    function_root = java_root / "system" / "store" / "functionModule"
    resources_root = backend / "src" / "main" / "resources"
    key_module = backend / "src" / "test" / "resources" / "KeyModule"
    module_maker = backend / "src" / "test" / "java" / "ModuleMaker.java"
    mapper_root = resources_root / "mapper" / "function"
    common_page = java_root / "system" / "store" / "common" / "myPage" / "CommonPage.java"

    report.add("pass", "FUNCTION_ROOT_FOUND", "已定位业务模块源码根", relative(function_root, project_root))
    if key_module.is_dir():
        template_files = sorted(relative(path, project_root) for path in key_module.rglob("*") if path.is_file())
        report.add("pass", "KEY_MODULE_FOUND", "已定位 KeyModule 模板", relative(key_module, project_root))
    else:
        template_files = []
        report.add("warning", "KEY_MODULE_MISSING", "未找到 KeyModule 模板，不能按当前平台骨架预演")
    if module_maker.is_file():
        report.add("pass", "MODULE_MAKER_FOUND", "已定位 ModuleMaker", relative(module_maker, project_root))
    else:
        report.add("warning", "MODULE_MAKER_MISSING", "未找到 ModuleMaker，不能验证模板生成契约")
    if mapper_root.is_dir():
        report.add("pass", "MAPPER_ROOT_FOUND", "已定位自定义 Mapper XML 目录", relative(mapper_root, project_root))
    else:
        report.add("unverified", "MAPPER_ROOT_ABSENT", "尚未发现自定义 Mapper XML 目录")

    common_page_properties = []
    if common_page.is_file():
        common_page_text = read_text(common_page)
        common_page_properties = re.findall(r"private\s+[A-Za-z0-9_<>?,. ]+\s+([A-Za-z][A-Za-z0-9_]*)\s*;", common_page_text)
        report.add(
            "pass",
            "PAGINATION_CONTRACT_FOUND",
            "已定位 CommonPage 当前可用业务查询属性",
            ", ".join(common_page_properties) or "仅继承分页属性",
        )
    else:
        report.add("warning", "COMMON_PAGE_MISSING", "未找到 CommonPage，生成查询前必须重新确认分页输入")

    frontends = []
    frontend_details = []
    search_roots = [project_root] if backend == project_root else [child for child in project_root.iterdir() if child.is_dir()]
    for child in search_roots:
        if (child / "package.json").is_file():
            frontends.append(relative(child, project_root))
            source = child / "src"
            contract_files = {
                "module_root": source / "views" / "main" / "modules",
                "use_fetch_list": source / "hooks" / "useFetchList.ts",
                "use_modal_handler": source / "hooks" / "useModalHandler.ts",
                "page_modal": source / "components" / "PageModal" / "index.vue",
                "page_content": source / "components" / "PageContent" / "index.vue",
                "button_permissions": source / "utils" / "map-menus.ts",
                "current_user_store": source / "store" / "main" / "main.ts",
            }
            existing = {
                key: relative(path, project_root)
                for key, path in contract_files.items()
                if path.exists()
            }
            fetch_text = read_text(contract_files["use_fetch_list"]) if contract_files["use_fetch_list"].is_file() else ""
            modal_text = read_text(contract_files["page_modal"]) if contract_files["page_modal"].is_file() else ""
            permission_text = read_text(contract_files["button_permissions"]) if contract_files["button_permissions"].is_file() else ""
            frontend_details.append(
                {
                    "name": child.name,
                    "root": relative(child, project_root),
                    "contract_files": existing,
                    "contract_signals": {
                        "page_list_and_total": "data.list" in fetch_text and "data.total" in fetch_text,
                        "list_transform": "transform" in fetch_text,
                        "label_code_value": "labelCode" in modal_text and "labelValue" in modal_text,
                        "form_field_update": "updateFormField" in modal_text,
                        "button_permission_helper": "hasButtonPermission" in permission_text,
                        "button_permission_substring_match": ".includes(btnType)" in permission_text,
                    },
                }
            )
    if frontends:
        report.add("pass", "FRONTENDS_FOUND", "已定位前端项目", ", ".join(frontends))
        contract_count = sum(bool(item["contract_files"]) for item in frontend_details)
        if contract_count:
            report.add("pass", "FRONTEND_CONTRACT_FOUND", "已定位低代码页面与后台契约依据", str(contract_count))
    else:
        report.add("unverified", "FRONTENDS_NOT_FOUND", "未在项目根的直接子目录发现前端项目")

    base_root = java_root / "system" / "store" / "baseModule"
    common_capabilities = []
    if base_root.is_dir():
        common_capabilities = sorted(path.name for path in base_root.iterdir() if path.is_dir())
        report.add("pass", "BASE_MODULES_FOUND", "已定位平台公共能力目录", relative(base_root, project_root))
    else:
        report.add("warning", "BASE_MODULES_MISSING", "未找到 system.store.baseModule 公共能力目录")

    modules = sorted(path.name for path in function_root.iterdir() if path.is_dir())
    pom = backend / "pom.xml"
    versions: dict[str, str] = {}
    if pom.is_file():
        text = pom.read_text(encoding="utf-8", errors="replace")
        patterns = {
            "spring_boot": r"spring-boot-starter-parent</artifactId>\s*<version>([^<]+)",
            "java": r"<(?:java\.version|java\.complier)>([^<]+)",
            "mybatis_plus": r"mybatis-plus-boot-starter</artifactId>\s*<version>([^<]+)",
            "mysql_connector": r"mysql-connector-j</artifactId>\s*<version>([^<]+)",
        }
        for key, pattern in patterns.items():
            match = re.search(pattern, text)
            if match:
                versions[key] = match.group(1).strip()

    report.data = {
        "project_root": str(project_root),
        "backend_candidates": [relative(path, project_root) for path in backends],
        "selected_backend": relative(backend, project_root) or ".",
        "java_root": relative(java_root, project_root),
        "function_module_root": relative(function_root, project_root),
        "canonical_package_root": "system.store.functionModule",
        "key_module": relative(key_module, project_root) if key_module.is_dir() else None,
        "key_module_files": template_files,
        "module_maker": relative(module_maker, project_root) if module_maker.is_file() else None,
        "mapper_root": relative(mapper_root, project_root) if mapper_root.is_dir() else None,
        "pagination_contract": {
            "common_page_file": relative(common_page, project_root) if common_page.is_file() else None,
            "declared_business_properties": common_page_properties,
            "dedicated_page_required_for_other_filters": True,
        },
        "frontends": frontends,
        "frontend_details": frontend_details,
        "base_capabilities": common_capabilities,
        "business_modules": modules,
        "versions": versions,
    }
    return report


def main() -> int:
    args = parse_args()
    return print_report(inspect(absolute(args.project_root)), args.format)


if __name__ == "__main__":
    raise SystemExit(main())
