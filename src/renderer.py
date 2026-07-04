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

    # 输出目录
    out_base = OUTPUT_DIR / student_name / subject
    out_base.mkdir(parents=True, exist_ok=True)

    # 渲染三份 HTML
    views = {
        "teacher": ("teacher.html", f"{lesson_date}_教师.html"),
        "parent": ("parent.html", f"{lesson_date}_家长.html"),
        "student": ("student.html", f"{lesson_date}_学生.html"),
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

    # 扫描各科目的 HTML 文件
    subjects_data = []
    total_lessons = 0

    for subject_dir in sorted(out_base.iterdir()):
        if not subject_dir.is_dir():
            continue
        if subject_dir.name == "homework.json":
            continue

        subject_name = subject_dir.name
        lessons = []

        # 收集该科目下的教师版 HTML（按日期排序）
        teacher_files = sorted(subject_dir.glob("*_教师.html"), reverse=True)
        for tf in teacher_files:
            # 提取日期
            stem = tf.stem  # e.g., "2026-07-03_教师"
            date_str = stem.replace("_教师", "")

            # 简单解析 HTML 提取标题和摘要（不使用完整 HTML 解析器）
            title, summary = _extract_meta_from_html(tf)

            # 相对路径（相对于 index.html）
            parent_path = f"{subject_name}/{stem.replace('_教师', '_家长')}.html"
            student_path = f"{subject_name}/{stem.replace('_教师', '_学生')}.html"
            teacher_path = f"{subject_name}/{tf.name}"

            lessons.append({
                "date": date_str,
                "title": title or f"{subject_name} 课程",
                "summary": summary or "",
                "teacher_path": teacher_path,
                "parent_path": parent_path,
                "student_path": student_path,
            })

        if lessons:
            subjects_data.append({
                "name": subject_name,
                "lesson_count": len(lessons),
                "lessons": lessons,
            })
            total_lessons += len(lessons)

    ctx = {
        "student": student_config,
        "subjects": subjects_data,
        "total_lessons": total_lessons,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }

    template = _env.get_template("index.html")
    html = template.render(**ctx)
    filepath = out_base / "index.html"
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)

    return filepath


def _extract_meta_from_html(filepath: Path) -> tuple[str, str]:
    """从 HTML 文件中简单提取标题和摘要。

    Returns:
        (title, summary) 元组
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except (IOError, UnicodeDecodeError):
        return ("", "")

    title = ""
    summary = ""

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

    return (title, summary)
