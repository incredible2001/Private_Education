"""
TXT 转录文件解析器。
解析前置注释区（元数据）和转录正文。
"""

import re
from dataclasses import dataclass, field


@dataclass
class ParsedTranscript:
    """解析后的转录文件内容。"""

    # 元数据（来自前置注释区）
    subject: str = ""          # 科目
    notes: str = ""           # 备注
    homework: str = ""        # 课后作业
    lesson_type: str = ""     # 课程类型（新课/复习/考试讲评/摸底）

    # 转录正文（原始对话，含发言人标记）
    raw_body: str = ""

    # 从文件名提取的日期
    date: str = ""


def parse_transcript(filepath) -> ParsedTranscript:
    """解析一个 TXT 转录文件。

    文件格式：
        科目：数学
        备注：学生对称轴概念薄弱
        课后作业：《五三》P42-44
        课程类型：新课
        ---
        发言人1
        今天我们来讲...

    前置注释区中所有字段均为可选。
    """
    from pathlib import Path
    filepath = Path(filepath)

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    result = ParsedTranscript()

    # 从文件名提取日期（格式：YYYY-MM-DD.txt）
    stem = filepath.stem
    date_match = re.match(r"(\d{4}-\d{2}-\d{2})", stem)
    if date_match:
        result.date = date_match.group(1)

    # 查找分隔线
    separator_match = re.search(r"^---\s*$", content, re.MULTILINE)

    if separator_match:
        front_matter = content[:separator_match.start()].strip()
        result.raw_body = content[separator_match.end():].strip()
    else:
        # 无分隔线时，尝试自动识别前置注释
        # 如果前几行有「字段名：值」格式，视为前置注释
        front_matter = ""
        result.raw_body = content.strip()

    if front_matter:
        # 解析前置注释字段
        for line in front_matter.split("\n"):
            line = line.strip()
            if not line:
                continue

            # 匹配「字段名：值」
            kv_match = re.match(r"^(.+?)[：:](.*)$", line)
            if kv_match:
                key = kv_match.group(1).strip()
                value = kv_match.group(2).strip()

                if key in ("科目", "subject"):
                    result.subject = value
                elif key in ("备注", "notes"):
                    result.notes = value
                elif key in ("课后作业", "homework"):
                    result.homework = value
                elif key in ("课程类型", "lesson_type"):
                    result.lesson_type = value

    return result


def extract_speakers(raw_body: str) -> list[str]:
    """从转录正文中提取所有发言人标签。

    发言人标签格式：「发言人1」「发言人2」等。

    Returns:
        去重后的发言人标签列表，按首次出现顺序排序
    """
    speakers = []
    seen = set()
    for match in re.finditer(r"发言人\d+", raw_body):
        s = match.group(0)
        if s not in seen:
            seen.add(s)
            speakers.append(s)
    return speakers
