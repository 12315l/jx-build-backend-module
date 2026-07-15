#!/usr/bin/env python3
"""Check requirement document structure without changing requirements or project files."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from _common import Report, absolute, read_text, print_report


ROLE_WORDS = ("管理员", "教练", "学员", "用户", "学生", "员工", "商家", "医生", "患者", "教师", "家长")
ACTION_SIGNALS = {
    "view": ("查看", "浏览", "查询", "详情", "列表"),
    "maintain": ("维护", "管理", "新增", "修改", "删除", "发布"),
    "submit": ("提交", "申请", "报名", "预约", "下单"),
    "review": ("审核", "审批", "通过", "驳回"),
    "confirm": ("确认", "发放", "核销", "结算", "验收"),
    "reverse": ("归还", "取消", "撤回", "退款", "报损", "丢失"),
    "record": ("录入", "补录", "补签", "记录"),
    "statistics": ("统计", "趋势", "排行", "占比", "看板"),
    "recommend": ("推荐", "智能选人", "猜你喜欢", "协同过滤"),
    "interaction": ("评论", "点赞", "收藏", "评分"),
}
STATE_WORDS = ("待处理", "处理中", "已完成", "通过", "驳回", "取消", "发放", "使用中", "归还", "报损", "丢失")
QUANTITY_WORDS = ("库存", "数量", "名额", "容量", "剩余", "扣减", "增加", "恢复", "核减", "金额", "积分", "评分")
HIGH_RISK_WORDS = ("真实支付", "在线退款", "二维码", "扫码", "定位", "消息通知", "自动发送", "人脸识别")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="只读检查角色功能与核心流程需求文档")
    parser.add_argument("requirements_file")
    parser.add_argument("--platform-report", help="可选 inspect-platform JSON 报告；当前版本仅记录来源")
    parser.add_argument("--forbid", action="append", default=[], help="项目明确禁止的能力，可重复")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser.parse_args()


def clean_markup(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value)
    value = value.replace("**", "").replace("`", "")
    return re.sub(r"\s+", " ", value).strip(" -:*|\t")


def role_candidates(lines: list[str]) -> list[str]:
    roles: list[str] = []
    for line in lines:
        cleaned = clean_markup(line)
        if not any(word in cleaned for word in ROLE_WORDS):
            continue
        if line.lstrip().startswith("#") or (line.startswith("|") and "角色" not in cleaned[:6]):
            candidate = cleaned.split("|")[0].strip()
            if candidate and len(candidate) <= 40 and candidate not in roles:
                roles.append(candidate)
    return roles


def feature_candidates(lines: list[str]) -> list[dict[str, str]]:
    features: list[dict[str, str]] = []
    current_heading = ""
    for line in lines:
        if line.lstrip().startswith("#"):
            current_heading = clean_markup(line.lstrip("#"))
            continue
        stripped = line.strip()
        if not re.match(r"^(?:[-*+]\s+|\d+(?:\.\d+)*[.、]\s*)", stripped):
            continue
        cleaned = clean_markup(re.sub(r"^(?:[-*+]\s+|\d+(?:\.\d+)*[.、]\s*)", "", stripped))
        if len(cleaned) < 4:
            continue
        name = re.split(r"[：:]", cleaned, maxsplit=1)[0][:60]
        features.append({"heading": current_heading, "name": name, "text": cleaned})
    return features


def flow_candidates(lines: list[str]) -> list[dict[str, str]]:
    flows: list[dict[str, str]] = []
    for index, line in enumerate(lines):
        if not line.lstrip().startswith("#"):
            continue
        heading = clean_markup(line.lstrip("#"))
        if "流程" not in heading and "闭环" not in heading:
            continue
        body_lines = []
        for following in lines[index + 1 : index + 15]:
            if following.lstrip().startswith("#"):
                break
            if following.strip() and not following.strip().startswith("```"):
                body_lines.append(clean_markup(following))
        flows.append({"name": heading, "summary": " ".join(body_lines)[:800]})
    return flows


def validate(path: Path, forbidden: list[str], platform_report: str | None) -> Report:
    report = Report("validate-project-requirements", str(path))
    if not path.is_file():
        report.add("blocker", "REQUIREMENTS_MISSING", "需求文件不存在", str(path))
        return report
    text = read_text(path)
    lines = text.splitlines()
    roles = role_candidates(lines)
    features = feature_candidates(lines)
    flows = flow_candidates(lines)

    if roles:
        report.add("pass", "ROLES_FOUND", "发现角色描述", str(len(roles)))
    else:
        report.add("blocker", "ROLES_MISSING", "未识别到按角色划分的需求")
    if features:
        report.add("pass", "FEATURES_FOUND", "发现候选功能条目", str(len(features)))
    else:
        report.add("blocker", "FEATURES_MISSING", "未识别到可追踪的功能条目")
    if flows:
        report.add("pass", "FLOWS_FOUND", "发现核心流程或闭环描述", str(len(flows)))
    else:
        report.add("blocker", "FLOWS_MISSING", "未识别到核心流程说明")

    lowered = text.lower()
    signals = {name: [word for word in words if word.lower() in lowered] for name, words in ACTION_SIGNALS.items()}
    signals = {name: words for name, words in signals.items() if words}
    state_hits = sorted({word for word in STATE_WORDS if word in text})
    quantity_hits = sorted({word for word in QUANTITY_WORDS if word in text})
    if state_hits:
        report.add("warning", "STATE_RULES_REQUIRED", "需求包含状态信号，模块规格必须补齐状态与流转", "、".join(state_hits))
    if quantity_hits:
        report.add("warning", "QUANTITY_RULES_REQUIRED", "需求包含数量信号，必须明确变化时点、事务和守恒规则", "、".join(quantity_hits))

    explicit_forbidden = sorted({item.strip() for item in forbidden if item.strip()})
    conflicts = [item for item in explicit_forbidden if item in text]
    for item in conflicts:
        report.add("blocker", "FORBIDDEN_CAPABILITY_PRESENT", f"需求文档仍包含明确禁止能力：{item}")

    risk_hits = sorted({word for word in HIGH_RISK_WORDS if word in text and word not in explicit_forbidden})
    if risk_hits:
        report.add(
            "warning",
            "HIGH_RISK_CONFIRMATION",
            "发现需以真实代码或最新需求确认的高风险能力，不能按行业惯例直接生成",
            "、".join(risk_hits),
        )

    has_correction = any(word in text for word in ("最新修正", "禁止事项", "暂缓开发", "不包含", "不支持"))
    if has_correction:
        report.add("pass", "CORRECTION_SECTION_FOUND", "发现最新修正或禁止事项表达")
    else:
        report.add("warning", "CORRECTION_SECTION_MISSING", "未识别到最新修正与禁止事项，需防止旧文档覆盖最新口径")

    has_scope = any(word in text for word in ("仅能", "本人", "全部数据", "数据范围", "自己负责", "本队伍"))
    if has_scope:
        report.add("pass", "DATA_SCOPE_FOUND", "发现角色数据范围描述")
    else:
        report.add("warning", "DATA_SCOPE_MISSING", "未识别到角色数据范围说明")

    if platform_report:
        platform_path = absolute(platform_report)
        if platform_path.is_file():
            report.add("unverified", "PLATFORM_REPORT_ATTACHED", "已记录平台报告来源；需求覆盖仍需结合代码证据逐项判断", str(platform_path))
        else:
            report.add("warning", "PLATFORM_REPORT_MISSING", "指定的平台报告文件不存在", str(platform_path))

    coverage = []
    for index, feature in enumerate(features, start=1):
        matched = [name for name, words in ACTION_SIGNALS.items() if any(word in feature["text"] for word in words)]
        coverage.append(
            {
                "requirement_id": f"REQ-CANDIDATE-{index:03d}",
                "source_heading": feature["heading"],
                "original_feature": feature["text"],
                "action_signals": matched,
                "coverage_status": "to_confirm",
                "note": "候选编号；需按正式角色清单稳定编号并结合项目证据确认",
            }
        )
    flow_rows = [
        {
            "flow_id": f"FLOW-CANDIDATE-{index:03d}",
            "name": flow["name"],
            "summary": flow["summary"],
            "status": "to_confirm",
        }
        for index, flow in enumerate(flows, start=1)
    ]

    report.add("unverified", "SEMANTIC_COVERAGE", "脚本只做结构与信号检查，最终功能覆盖和流程真实性必须由 Skill 结合代码确认")
    report.data = {
        "requirements_file": str(path),
        "roles": roles,
        "feature_count": len(features),
        "flow_count": len(flows),
        "action_signals": signals,
        "state_signals": state_hits,
        "quantity_signals": quantity_hits,
        "explicit_forbidden": explicit_forbidden,
        "feature_coverage_candidates": coverage,
        "flow_candidates": flow_rows,
    }
    return report


def main() -> int:
    args = parse_args()
    return print_report(validate(absolute(args.requirements_file), args.forbid, args.platform_report), args.format)


if __name__ == "__main__":
    raise SystemExit(main())

