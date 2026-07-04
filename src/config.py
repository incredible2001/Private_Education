"""
配置加载模块。
加载 .env 环境变量和学生 config.json。
"""

import os
import json
from pathlib import Path
from dotenv import load_dotenv

# 项目根目录
ROOT_DIR = Path(__file__).resolve().parent.parent
INPUT_DIR = ROOT_DIR / "input"
OUTPUT_DIR = ROOT_DIR / "output"
TEMPLATES_DIR = ROOT_DIR / "templates"
PROMPTS_DIR = ROOT_DIR / "src" / "prompts"

# 加载 .env
load_dotenv(ROOT_DIR / ".env")


def get_api_config() -> dict:
    """获取 DeepSeek API 配置。"""
    api_key = os.getenv("DEEPSEEK_API_KEY", "")
    base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    if not api_key:
        raise RuntimeError("请在 .env 文件中设置 DEEPSEEK_API_KEY")
    return {"api_key": api_key, "base_url": base_url}


def load_student_config(student_name: str) -> dict:
    """加载学生配置。

    Args:
        student_name: 学生姓名（对应 input/ 下的文件夹名）

    Returns:
        dict: 包含 name, subjects, grade 等字段
    """
    config_path = INPUT_DIR / student_name / "config.json"
    if not config_path.exists():
        raise FileNotFoundError(f"找不到学生配置文件: {config_path}")
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def list_students() -> list[str]:
    """列出所有已配置的学生姓名。"""
    students = []
    if not INPUT_DIR.exists():
        return students
    for d in INPUT_DIR.iterdir():
        # 跳过以下划线开头的文件夹（模板等）
        if d.name.startswith("_"):
            continue
        if d.is_dir() and (d / "config.json").exists():
            students.append(d.name)
    return sorted(students)


def list_txt_files(student_name: str) -> list[Path]:
    """列出某个学生目录下的所有 TXT 文件（按文件名排序）。"""
    student_dir = INPUT_DIR / student_name
    if not student_dir.exists():
        return []
    return sorted(student_dir.glob("*.txt"))


def get_output_dir(student_name: str, subject: str = None) -> Path:
    """获取输出目录路径。"""
    base = OUTPUT_DIR / student_name
    if subject:
        base = base / subject
    base.mkdir(parents=True, exist_ok=True)
    return base


def get_homework_path(student_name: str) -> Path:
    """获取作业追踪文件路径。"""
    out_dir = OUTPUT_DIR / student_name
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir / "homework.json"
