"""
HTML 渲染模块。
使用 Jinja2 模板生成三个视图的 HTML 汇报文件及汇总索引页。
"""

import os
from datetime import datetime
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from .config import TEMPLATES_DIR, OUTPUT_DIR


_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=True,
)


def render_lesson(
    data: dict,
    student_config: dict,
    lesson_date: str,
    corrected_text: str = "",
) -> dict:
    """渲染一节课的三份 HTML 汇报。

    Args:
        data: Pipeline 输出的结构化数据
        student_config: 学生配置
        lesson_date: 课程日期 (YYYY-MM-DD)
        corrected_text: 修正后的对话文本（用于教师版）

    Returns:
        dict: {"teacher": Path, "parent": Path, "student": Path}
    """
    student_name = student_config["name"]
    subject = data.get("subject", "未分类")

    # 确保日期字段存在
    data["date"] = lesson_date
    data["corrected_text"] = corrected_text

    # 模板上下文
    ctx = {
        "data": data,
        "student": student_config,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }

    # 输出目录：lessons/<日期>/ 子文件夹，index.html 留在学生根目录
    out_base = OUTPUT_DIR / student_name / "lessons" / lesson_date
    out_base.mkdir(parents=True, exist_ok=True)

    # 渲染三份 HTML
    views = {
        "teacher": ("teacher.html", "教师.html"),
        "parent": ("parent.html", "家长.html"),
        "student": ("student.html", "学生.html"),
    }

    result = {}
    for view_key, (template_name, filename) in views.items():
        template = _env.get_template(template_name)
        html = template.render(**ctx)
        filepath = out_base / filename
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html)
        result[view_key] = filepath

    return result


def render_index(student_config: dict) -> Path:
    """为某个学生重新生成汇总索引页。

    扫描 output 目录下各科目的 HTML 文件，生成 index.html。
    """
    student_name = student_config["name"]
    out_base = OUTPUT_DIR / student_name
    out_base.mkdir(parents=True, exist_ok=True)

    # 扫描 lessons/<日期>/ 下的教师版 HTML，按日期排序
    lessons = []
    teacher_files = sorted(out_base.glob("lessons/*/教师.html"), reverse=True)

    for tf in teacher_files:
        # 日期即子文件夹名，如 "2026-07-14"、"2026-07-05_0916"
        date_str = tf.parent.name

        # 解析 HTML 提取标题、摘要和科目
        title, summary, subject = _extract_meta_from_html(tf)

        # 科目标签（从 HTML 中解析的 badge accent 文本）
        if not subject:
            subject = "未分类"

        # 相对路径（index.html 在学生根目录，报告在 lessons/<日期>/ 下）
        prefix = f"lessons/{date_str}"
        lessons.append({
            "date": date_str,
            "title": title or f"{subject} 课程",
            "summary": summary or "",
            "subject": subject,
            "teacher_path": f"{prefix}/教师.html",
            "parent_path": f"{prefix}/家长.html",
            "student_path": f"{prefix}/学生.html",
        })

    ctx = {
        "student": student_config,
        "lessons": lessons,
        "total_lessons": len(lessons),
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }

    template = _env.get_template("index.html")
    html = template.render(**ctx)
    filepath = out_base / "index.html"
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)

    return filepath


def _extract_meta_from_html(filepath: Path) -> tuple[str, str, str]:
    """从 HTML 文件中简单提取标题、摘要和科目。

    Returns:
        (title, summary, subject) 元组
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except (IOError, UnicodeDecodeError):
        return ("", "", "")

    title = ""
    summary = ""
    subject = ""

    # 提取 <h1> 标题
    import re
    h1_match = re.search(r"<h1>(.+?)</h1>", content)
    if h1_match:
        title = h1_match.group(1).strip()

    # 提取 summary
    summary_match = re.search(r'class="summary">(.+?)</p>', content)
    if summary_match:
        summary = summary_match.group(1).strip()
        # 限制长度
        if len(summary) > 120:
            summary = summary[:120] + "..."

    # 提取科目标签（第一个 badge accent）
    subject_match = re.search(
        r'<span class="badge accent">(.+?)</span>', content
    )
    if subject_match:
        subject = subject_match.group(1).strip()

    return (title, summary, subject)
