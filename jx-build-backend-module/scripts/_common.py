#!/usr/bin/env python3
"""Shared read-only helpers for jx-build-backend-module tools."""

from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Iterator


LEVELS = ("pass", "warning", "blocker", "unverified")
LEVEL_LABELS = {
    "pass": "通过",
    "warning": "警告",
    "blocker": "阻断",
    "unverified": "未验证",
}
SKIP_DIRS = {
    ".git",
    ".idea",
    ".m2",
    ".gradle",
    "node_modules",
    "target",
    "dist",
    "build",
    "coverage",
    "__pycache__",
}


@dataclass(frozen=True)
class Finding:
    level: str
    code: str
    message: str
    evidence: str = ""

    def __post_init__(self) -> None:
        if self.level not in LEVELS:
            raise ValueError(f"unsupported level: {self.level}")


class Report:
    def __init__(self, tool: str, subject: str, read_only: bool = True) -> None:
        self.tool = tool
        self.subject = subject
        self.read_only = read_only
        self.findings: list[Finding] = []
        self.data: dict[str, Any] = {}

    def add(self, level: str, code: str, message: str, evidence: str = "") -> None:
        self.findings.append(Finding(level, code, message, evidence))

    def counts(self) -> dict[str, int]:
        return {level: sum(item.level == level for item in self.findings) for level in LEVELS}

    def payload(self) -> dict[str, Any]:
        return {
            "tool": self.tool,
            "subject": self.subject,
            "read_only": self.read_only,
            "summary": self.counts(),
            "findings": [asdict(item) for item in self.findings],
            "data": self.data,
        }

    def render(self, output_format: str) -> str:
        if output_format == "json":
            return json.dumps(self.payload(), ensure_ascii=False, indent=2)
        lines = [f"{self.tool}: {self.subject}", f"只读检查: {'是' if self.read_only else '否'}"]
        counts = self.counts()
        lines.append(
            "结果: " + "，".join(f"{LEVEL_LABELS[level]} {counts[level]}" for level in LEVELS)
        )
        for level in LEVELS:
            items = [item for item in self.findings if item.level == level]
            if not items:
                continue
            lines.append(f"\n[{LEVEL_LABELS[level]}]")
            for item in items:
                suffix = f" | 依据: {item.evidence}" if item.evidence else ""
                lines.append(f"- {item.code}: {item.message}{suffix}")
        if self.data:
            lines.append("\n[结构化摘要]")
            lines.append(json.dumps(self.data, ensure_ascii=False, indent=2))
        return "\n".join(lines)

    def exit_code(self) -> int:
        return 2 if any(item.level == "blocker" for item in self.findings) else 0


def absolute(path: str | Path) -> Path:
    return Path(path).expanduser().resolve()


def relative(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def read_text(path: Path) -> str:
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="replace")


def iter_files(
    root: Path,
    suffixes: Iterable[str] | None = None,
    max_files: int = 50_000,
) -> Iterator[Path]:
    allowed = {suffix.lower() for suffix in suffixes} if suffixes else None
    seen = 0
    if not root.is_dir():
        return
    for current, dirs, files in os.walk(root):
        dirs[:] = [name for name in dirs if name not in SKIP_DIRS]
        for name in files:
            path = Path(current) / name
            if allowed is not None and path.suffix.lower() not in allowed:
                continue
            yield path
            seen += 1
            if seen >= max_files:
                return


def backend_candidates(project_root: Path) -> list[Path]:
    candidates: list[Path] = []
    direct = project_root / "src" / "main" / "java" / "system" / "store" / "functionModule"
    if direct.is_dir():
        candidates.append(project_root)
    for child in sorted(project_root.iterdir()) if project_root.is_dir() else []:
        if not child.is_dir() or child.name in SKIP_DIRS:
            continue
        function_root = child / "src" / "main" / "java" / "system" / "store" / "functionModule"
        if function_root.is_dir():
            candidates.append(child)
    return candidates


def resolve_backend(project_root: Path) -> tuple[Path | None, Path | None]:
    candidates = backend_candidates(project_root)
    if not candidates:
        return None, None
    backend = candidates[0]
    function_root = backend / "src" / "main" / "java" / "system" / "store" / "functionModule"
    return backend, function_root


def normalize_module_name(value: str) -> tuple[str, str]:
    raw = value.strip()
    if raw.endswith("Module"):
        raw = raw[:-6]
    if not raw:
        return "", ""
    pascal = raw[0].upper() + raw[1:]
    return pascal, pascal + "Module"


def print_report(report: Report, output_format: str) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass
    print(report.render(output_format))
    return report.exit_code()
