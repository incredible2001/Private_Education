"""
作业追踪模块。
持久化管理跨课作业记录（布置 → 检查 → 完成状态）。
"""

import json
from datetime import datetime
from pathlib import Path
from .config import get_homework_path


def load_homework(student_name: str) -> dict:
    """加载某个学生的作业追踪记录。

    Returns:
        dict: { "assignments": [...], "last_updated": "..." }
    """
    path = get_homework_path(student_name)
    if not path.exists():
        return {"assignments": [], "last_updated": ""}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {"assignments": [], "last_updated": ""}


def save_homework(student_name: str, data: dict) -> None:
    """保存作业追踪记录。"""
    data["last_updated"] = datetime.now().isoformat()
    path = get_homework_path(student_name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def add_homework(student_name: str, lesson_date: str, subject: str,
                 assignments: list[dict]) -> None:
    """记录新布置的作业。

    Args:
        student_name: 学生姓名
        lesson_date: 布置日期
        subject: 科目
        assignments: 作业列表 [{"content": "...", "source": "...", "due_date": "..."}]
    """
    data = load_homework(student_name)
    for a in assignments:
        data["assignments"].append({
            "content": a.get("content", ""),
            "source": a.get("source", ""),
            "due_date": a.get("due_date", ""),
            "subject": subject,
            "assigned_date": lesson_date,
            "status": "待检查",  # 待检查 / 已完成 / 部分完成 / 未完成
            "check_date": None,
            "check_comment": "",
        })
    save_homework(student_name, data)


def mark_homework_checked(student_name: str, checked_items: list[dict]) -> None:
    """标记作业检查结果。

    根据 AI 提取的检查结果，更新匹配的作业状态。
    匹配逻辑：按 subject + content 关键词模糊匹配最近一条"待检查"的作业。

    Args:
        checked_items: [{"content": "...", "status": "...", "comment": "..."}]
    """
    if not checked_items:
        return

    data = load_homework(student_name)
    today = datetime.now().strftime("%Y-%m-%d")

    for checked in checked_items:
        # 找到最匹配的待检查作业
        best_match = None
        best_score = 0

        for hw in data["assignments"]:
            if hw["status"] != "待检查":
                continue
            # 简单的内容关键词匹配
            score = _content_similarity(checked.get("content", ""), hw.get("content", ""))
            if score > best_score:
                best_score = score
                best_match = hw

        if best_match and best_score > 0.3:
            best_match["status"] = checked.get("status", "已完成")
            best_match["check_date"] = today
            best_match["check_comment"] = checked.get("comment", "")

    save_homework(student_name, data)


def _content_similarity(a: str, b: str) -> float:
    """简单的内容相似度计算（基于共同字符）。"""
    if not a or not b:
        return 0.0
    a_set = set(a)
    b_set = set(b)
    if not a_set or not b_set:
        return 0.0
    intersection = a_set & b_set
    return len(intersection) / min(len(a_set), len(b_set))


def get_pending_homework(student_name: str) -> list[dict]:
    """获取所有待检查的作业。"""
    data = load_homework(student_name)
    return [h for h in data["assignments"] if h["status"] == "待检查"]


def get_homework_summary(student_name: str) -> str:
    """生成作业概况文本，用于传入 AI prompt。"""
    data = load_homework(student_name)
    if not data["assignments"]:
        return "暂无历史作业记录。"

    lines = ["## 历史作业记录"]
    for hw in data["assignments"]:
        lines.append(
            f"- [{hw['subject']}] {hw['assigned_date']} 布置：{hw['content']} "
            f"（来源：{hw['source']}）→ 状态：{hw['status']}"
        )
        if hw.get("check_comment"):
            lines.append(f"  检查备注：{hw['check_comment']}")

    return "\n".join(lines)
