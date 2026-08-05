"""
转录文本去重工具。
处理录音转录中每句话重复两次的问题。
"""

import re


def _dedup_text(text: str) -> str:
    """对一段文本去除连续重复的句子/短语。

    模式：每个句子/短语立即重复，如 "A。A。B。B。" → "A。B。"
    支持中英文标点（。！？.!?）作为分割边界。
    """
    # 按中英文句子标点分割（保留分隔符）
    parts = re.split(r'(?<=[。！？.!?])', text)

    result = []
    prev = ""
    for part in parts:
        stripped = part.strip()
        if not stripped:
            if part:  # 保留纯空白
                result.append(part)
            continue

        # 如果与上一段完全相同，跳过
        if stripped == prev:
            continue

        # 检查是否是上一段的子串或超串（处理部分重复和不完美重复）
        if len(stripped) > 5 and len(prev) > 5:
            if stripped in prev:
                # 当前是上一段的子串，保留较长的（prev 已在结果中）
                continue
            if prev in stripped:
                # 上一段是当前的子串，替换为较长的
                if result:
                    result.pop()
                result.append(part)
                prev = stripped
                continue
            else:
                result.append(part)
                prev = stripped
        else:
            result.append(part)
            prev = stripped

    return "".join(result)


def dedup_transcript(text: str) -> str:
    """对完整转录文本去重。

    1. 逐行去重
    2. 然后合并同一发言人的连续行，整体去重
    """
    lines = text.split("\n")
    result_lines = []

    for line in lines:
        stripped = line.strip()

        # 发言人标签行、空行、段头标记等保持原样
        if not stripped:
            result_lines.append(line)
            continue

        if re.match(r"^发言人\d+", stripped):
            result_lines.append(line)
            continue

        if re.match(r"^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}\s+记录_原文", stripped):
            result_lines.append(line)
            continue

        if re.match(r"^\d{4}年\d{2}月\d{2}日\s+\d{2}:\d{2}", stripped):
            result_lines.append(line)
            continue

        if stripped == "两人对话。":
            result_lines.append(line)
            continue

        # 内容行：先去重
        deduped = _dedup_text(stripped)
        result_lines.append(deduped)

    # ── 第二遍：合并同一发言人的连续行，整体去重 ──
    first_pass = "\n".join(result_lines)
    lines2 = first_pass.split("\n")
    final_lines = []
    i = 0
    while i < len(lines2):
        line = lines2[i]
        stripped = line.strip()

        # 非发言人标签：直接保留
        if not stripped or not re.match(r"^发言人\d+", stripped):
            # 检查是否是元数据行
            if stripped and not re.match(
                r"^\d{4}(-\d{2}){2}\s+\d{2}:\d{2}\s+记录_原文",
                stripped,
            ) and not re.match(r"^\d{4}年", stripped) and stripped != "两人对话。":
                final_lines.append(line)
            else:
                final_lines.append(line)
            i += 1
            continue

        # 收集同一发言人的连续内容行
        speaker = line
        content_lines = []
        i += 1
        while i < len(lines2):
            nl = lines2[i].strip()
            if not nl:
                # 空行：结束当前发言人段
                break
            if re.match(r"^发言人\d+", nl):
                # 新发言人：结束当前段
                break
            if re.match(r"^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}\s+记录_原文", nl):
                break
            if re.match(r"^\d{4}年\d{2}月\d{2}日\s+\d{2}:\d{2}", nl):
                break
            if nl == "两人对话。":
                break
            content_lines.append(lines2[i])
            i += 1

        # 对该发言人的所有内容行合并去重
        if content_lines:
            merged = "".join(content_lines)
            deduped_merged = _dedup_text(merged)
            final_lines.append(speaker)
            final_lines.append(deduped_merged)
        else:
            final_lines.append(speaker)

    return "\n".join(final_lines)
