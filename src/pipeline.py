"""
AI 处理 Pipeline。
编排三步 AI 调用：说话人识别 → 文字纠错 → 内容归纳结构化。
"""

import json
import re
from openai import OpenAI
from .config import get_api_config, PROMPTS_DIR
from .homework import get_homework_summary, add_homework, mark_homework_checked


def _load_prompt(name: str) -> str:
    """加载 prompt 模板文件。"""
    path = PROMPTS_DIR / name
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _get_client() -> OpenAI:
    """获取 DeepSeek API 客户端。"""
    cfg = get_api_config()
    return OpenAI(api_key=cfg["api_key"], base_url=cfg["base_url"])


def _call_deepseek(prompt: str, system: str = "你是一个专业的助手。") -> str:
    """调用 DeepSeek API，返回文本响应。"""
    client = _get_client()
    response = client.chat.completions.create(
        model="deepseek-v4-pro",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
        max_tokens=8192,
    )
    content = response.choices[0].message.content
    # 某些模型版本可能返回 None
    return content if content else ""


def _parse_json_response(text: str) -> dict:
    """从 API 响应中提取 JSON 对象。

    处理各种可能的包裹格式（```json ... ```、裸 JSON 等）。
    """
    text = text.strip()

    # 尝试提取 markdown 代码块中的 JSON
    code_block_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if code_block_match:
        text = code_block_match.group(1).strip()

    # 尝试找到第一个 { 和最后一个 }
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        text = text[start:end + 1]

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # 尝试修复常见问题：尾部逗号、未转义引号等
        # 先尝试逐行清理
        cleaned = re.sub(r",\s*}", "}", text)
        cleaned = re.sub(r",\s*]", "]", cleaned)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            raise ValueError(f"无法解析 API 返回的 JSON: {text[:500]}...")


# ─── Pipeline Steps ────────────────────────────────────────────

def step_speaker_identify(transcript: str, extra_context: str = "") -> dict:
    """步骤1：说话人角色识别。

    Args:
        transcript: 原始转录正文
        extra_context: 额外上下文（如前置注释中的信息）

    Returns:
        dict: { "发言人1": "老师", "发言人2": "学生", ... }
    """
    template = _load_prompt("speaker_identify.txt")
    prompt = template.format(
        transcript=transcript,
        extra_context=extra_context or "（无额外信息）",
    )

    print("  [1/3] 识别说话人角色...")
    response = _call_deepseek(prompt, system="你是一个课堂对话分析助手。请只输出 JSON。")
    result = _parse_json_response(response)
    return result.get("speakers", {})


def step_text_correct(transcript: str, speakers: dict) -> str:
    """步骤2：文字纠错。

    Args:
        transcript: 原始转录正文
        speakers: 说话人角色映射

    Returns:
        str: 修正后的完整对话文本
    """
    speaker_lines = [f"- {tag}: {role}" for tag, role in speakers.items()]
    speaker_context = "对话角色：" + "；".join(speaker_lines)

    template = _load_prompt("text_correct.txt")
    prompt = template.format(
        transcript=transcript,
        speaker_context=speaker_context,
    )

    print("  [2/3] 文字纠错中...")
    return _call_deepseek(prompt, system="你是一个中文文本校对助手。")


def step_summarize(
    corrected_transcript: str,
    speakers: dict,
    student_config: dict,
    user_notes: str = "",
) -> dict:
    """步骤3：内容归纳与结构化。

    Args:
        corrected_transcript: 修正后的对话文本
        speakers: 说话人角色映射
        student_config: 学生配置 {name, subjects, grade}
        user_notes: 前置注释中用户的手动备注

    Returns:
        dict: 结构化的课程汇报数据
    """
    speaker_lines = [f"- {tag}: {role}" for tag, role in speakers.items()]
    speaker_context = "对话角色：" + "；".join(speaker_lines)

    homework_context = get_homework_summary(student_config["name"])

    template = _load_prompt("summarize.txt")
    prompt = template.format(
        transcript=corrected_transcript,
        speaker_context=speaker_context,
        student_name=student_config["name"],
        grade=student_config.get("grade", "未知"),
        subjects="、".join(student_config.get("subjects", [])),
        user_notes=user_notes or "（无额外备注）",
        homework_context=homework_context,
    )

    print("  [3/3] 内容归纳与结构化...")
    response = _call_deepseek(prompt, system="你是一个教育内容分析助手。请只输出 JSON。")
    return _parse_json_response(response)


# ─── Main Pipeline ─────────────────────────────────────────────

def run_pipeline(
    transcript: str,
    student_config: dict,
    extra_context: str = "",
    user_notes: str = "",
) -> dict:
    """运行完整的 AI 处理 Pipeline。

    Args:
        transcript: 原始转录正文
        student_config: 学生配置
        extra_context: 额外上下文（科目提示等）
        user_notes: 用户备注

    Returns:
        dict: 最终的结构化汇报数据
    """
    student_name = student_config["name"]

    # Step 1: 说话人识别
    speakers = step_speaker_identify(transcript, extra_context)
    print(f"    识别结果: {speakers}")

    # Step 2: 文字纠错
    corrected = step_text_correct(transcript, speakers)
    print(f"    纠错完成（{len(corrected)} 字符）")

    # Step 3: 内容归纳
    summary = step_summarize(corrected, speakers, student_config, user_notes)
    print(f"    归纳完成: {summary.get('title', '未知标题')}")

    # 保存正确的科目信息
    if "subject" not in summary or not summary.get("subject"):
        summary["subject"] = "未分类"

    # 将修正后的文本附加到结果中
    summary["corrected_text"] = corrected

    return summary


def run_and_track_homework(
    transcript: str,
    student_config: dict,
    lesson_date: str,
    extra_context: str = "",
    user_notes: str = "",
) -> dict:
    """运行 Pipeline 并自动追踪作业。

    在 run_pipeline 基础上，自动将提取的作业写入 homework.json。
    """
    result = run_pipeline(transcript, student_config, extra_context, user_notes)

    student_name = student_config["name"]
    subject = result.get("subject", "未分类")

    # 记录新布置的作业
    assigned = result.get("homework_assigned", [])
    if assigned:
        add_homework(student_name, lesson_date, subject, assigned)
        print(f"    新增作业 {len(assigned)} 项")

    # 标记已检查的作业
    checked = result.get("homework_checked", [])
    if checked:
        mark_homework_checked(student_name, checked)
        print(f"    更新作业状态 {len(checked)} 项")

    return result
