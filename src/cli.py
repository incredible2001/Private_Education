# -*- coding: utf-8 -*-
"""
CLI 入口。
命令示例：
    python -m src.cli 张三              # 增量处理
    python -m src.cli 张三 --rebuild    # 全量重建
    python -m src.cli --all             # 处理所有学生
"""

import sys
import io
import argparse
from pathlib import Path
from .config import (
    load_student_config,
    list_students,
    list_txt_files,
    OUTPUT_DIR,
)
from .parser import parse_transcript
from .pipeline import run_and_track_homework
from .renderer import render_lesson, render_index

# 强制 stdout 使用 UTF-8（Windows 兼容）
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def process_one_lesson(
    student_name: str,
    txt_path: Path,
    student_config: dict,
    rebuild: bool = False,
) -> bool:
    """处理单节课。

    Returns:
        True 表示成功，False 表示跳过或失败
    """
    lesson_date = txt_path.stem  # e.g., "2026-07-03"

    # 检查是否已经处理过（增量模式下跳过已处理）
    if not rebuild:
        out_base = OUTPUT_DIR / student_name
        # 在所有科目目录中查找
        existing = list(out_base.glob(f"**/{lesson_date}_教师.html"))
        if existing:
            print(f"  - 跳过（已有汇报）: {lesson_date}")
            return False

    print(f"\n>>> 处理: {student_name}/{txt_path.name}")

    # 1. 解析 TXT
    parsed = parse_transcript(txt_path)
    print(f"  日期: {parsed.date or lesson_date}")
    if parsed.subject:
        print(f"  科目（标注）: {parsed.subject}")
    if parsed.lesson_type:
        print(f"  课程类型: {parsed.lesson_type}")

    # 构建额外上下文
    extra_context_parts = []
    if parsed.subject:
        extra_context_parts.append(f"用户标注科目为：{parsed.subject}")
    if student_config.get("subjects"):
        extra_context_parts.append(
            f"该学生的科目列表：{'、'.join(student_config['subjects'])}"
        )
    extra_context = "\n".join(extra_context_parts) if extra_context_parts else ""

    # 2. 运行 AI Pipeline
    try:
        result = run_and_track_homework(
            transcript=parsed.raw_body,
            student_config=student_config,
            lesson_date=parsed.date or lesson_date,
            extra_context=extra_context,
            user_notes=parsed.notes,
        )
    except Exception as e:
        print(f"  X AI 处理失败: {e}")
        return False

    # 如果用户标注了科目但 AI 没识别出来，使用用户标注
    if parsed.subject and (not result.get("subject") or result["subject"] == "未分类"):
        result["subject"] = parsed.subject

    # 如果用户标注了课程类型
    if parsed.lesson_type and not result.get("lesson_type"):
        result["lesson_type"] = parsed.lesson_type

    # 3. 渲染 HTML
    try:
        paths = render_lesson(
            data=result,
            student_config=student_config,
            lesson_date=parsed.date or lesson_date,
            corrected_text=result.get("corrected_text", parsed.raw_body),
        )
        print(f"  -> 教师版: {paths['teacher'].name}")
        print(f"  -> 家长版: {paths['parent'].name}")
        print(f"  -> 学生版: {paths['student'].name}")
    except Exception as e:
        print(f"  X HTML 渲染失败: {e}")
        return False

    return True


def process_student(student_name: str, rebuild: bool = False) -> int:
    """处理某个学生的全部课程。

    Returns:
        成功处理的课程数量
    """
    print(f"\n{'='*60}")
    print(f"学生: {student_name}")
    print(f"{'='*60}")

    # 加载配置
    try:
        config = load_student_config(student_name)
        print(f"年级: {config.get('grade', '未知')}")
        print(f"科目: {'、'.join(config.get('subjects', []))}")
    except FileNotFoundError as e:
        print(f"X {e}")
        return 0

    # 列出 TXT 文件
    txt_files = list_txt_files(student_name)
    if not txt_files:
        print(f"X 没有找到 TXT 文件。请将转录稿放入 input/{student_name}/")
        return 0

    print(f"共 {len(txt_files)} 个 TXT 文件")

    # 逐课处理
    success_count = 0
    for txt_path in txt_files:
        ok = process_one_lesson(student_name, txt_path, config, rebuild)
        if ok:
            success_count += 1

    # 重新生成汇总索引
    if success_count > 0 or rebuild:
        index_path = render_index(config)
        print(f"\n>>> 汇总索引: {index_path}")

    return success_count


def main():
    parser = argparse.ArgumentParser(
        description="Private_Education - 家教学习记录系统",
    )
    parser.add_argument(
        "student",
        nargs="?",
        help="学生姓名（对应 input/ 下的文件夹名）。省略时配合 --all 处理所有学生。",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="处理所有学生",
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="全量重建（默认增量模式，跳过已有汇报的课程）",
    )

    args = parser.parse_args()

    # 无参数时显示帮助
    if not args.student and not args.all:
        parser.print_help()
        print("\n可用的学生:")
        for s in list_students():
            print(f"  - {s}")
        return

    # 处理所有学生
    if args.all:
        students = list_students()
        if not students:
            print("X 没有找到任何学生。请在 input/ 下创建学生文件夹并添加 config.json。")
            return
        total = 0
        for s in students:
            total += process_student(s, args.rebuild)
        print(f"\n{'='*60}")
        print(f"全部完成！共处理 {total} 节课。")
        return

    # 处理单个学生
    count = process_student(args.student, args.rebuild)
    print(f"\n完成！共处理 {count} 节课。")


if __name__ == "__main__":
    main()
