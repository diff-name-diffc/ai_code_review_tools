"""配置加载模块"""

import os
from pathlib import Path

import toml
from pydantic import ValidationError

from .models.config import LLMConfig, ReviewerConfig


DEFAULT_CONFIG_PATH = ".ai-reviewer.toml"
DEFAULT_CONFIG_CONTENT = """# AI Code Reviewer 配置文件

[llm]
model = "qwen3-coder:30b"
api_key = ""
base_url = "http://localhost:11434/v1"  # 例如: "http://localhost:11434/v1" for ollama

[reviewer]
enabled_types = ["feat", "fix", "refactor", "doc", "config"]
max_file_size = 100000
excluded_patterns = ["*.lock", "package-lock.json", "*.min.js"]
output_file = ".ai-review-log.json"  # 日志文件目录默认: ".ai-review-log.json"
"""


def find_config_file(start_dir: Path | None = None) -> Path | None:
    """查找配置文件"""
    if start_dir is None:
        start_dir = Path.cwd()

    # 检查当前目录
    config_path = start_dir / DEFAULT_CONFIG_PATH
    if config_path.exists():
        return config_path

    # 检查父目录（直到 git root）
    current = start_dir
    while current != current.parent:
        config_path = current / DEFAULT_CONFIG_PATH
        if config_path.exists():
            return config_path
        current = current.parent

    return None


def load_config(config_path: Path | None = None) -> ReviewerConfig:
    """加载配置

    Args:
        config_path: 配置文件路径，如果为 None 则自动查找

    Returns:
        ReviewerConfig: 配置对象

    Raises:
        FileNotFoundError: 配置文件不存在
        ValidationError: 配置格式错误
    """
    if config_path is None:
        config_path = find_config_file()

    if config_path is None or not config_path.exists():
        raise FileNotFoundError(
            f"配置文件不存在: {DEFAULT_CONFIG_PATH}\n"
            f"请创建配置文件或运行: ai-code-reviewer init"
        )

    data = toml.load(config_path)

    # 构建 LLM 配置
    llm_data = data.get("llm", {})
    # 支持环境变量覆盖
    llm_data["api_key"] = os.getenv("AI_REVIEWER_API_KEY", llm_data.get("api_key", ""))
    llm_data["base_url"] = os.getenv("AI_REVIEWER_BASE_URL", llm_data.get("base_url"))

    # 构建评审器配置
    reviewer_data = data.get("reviewer", {})
    reviewer_data["llm"] = LLMConfig(**llm_data)

    return ReviewerConfig(**reviewer_data)


def create_default_config(path: Path | None = None) -> Path:
    """创建默认配置文件"""
    if path is None:
        path = Path.cwd() / DEFAULT_CONFIG_PATH

    if path.exists():
        raise FileExistsError(f"配置文件已存在: {path}")

    path.write_text(DEFAULT_CONFIG_CONTENT, encoding="utf-8")
    return path
