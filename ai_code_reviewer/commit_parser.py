"""Commit 类型解析器"""

import re
from typing import Optional

# 常见的 commit 类型前缀
COMMIT_TYPES = {
    "feat": "新功能",
    "fix": "修复 bug",
    "refactor": "重构",
    "doc": "文档变更",
    "config": "配置变更",
    "style": "代码格式调整",
    "test": "测试相关",
    "chore": "构建/工具变更",
}

# Commit 类型正则
COMMIT_TYPE_PATTERN = re.compile(
    r"^(?P<type>" + "|".join(COMMIT_TYPES.keys()) + r")(?P<scope>\(.+\))?\s*:\s*",
    re.IGNORECASE,
)


def parse_commit_type(commit_message: str) -> Optional[str]:
    """解析 commit 类型

    Args:
        commit_message: commit message

    Returns:
        commit 类型（小写），如果无法解析则返回 None
    """
    if not commit_message:
        return None

    # 去除首行
    first_line = commit_message.split("\n", 1)[0].strip()

    # 匹配类型
    match = COMMIT_TYPE_PATTERN.match(first_line)
    if match:
        return match.group("type").lower()

    return None


def should_review(commit_type: Optional[str], enabled_types: list[str]) -> bool:
    """判断是否应该进行评审

    Args:
        commit_type: commit 类型
        enabled_types: 启用的类型列表

    Returns:
        是否应该评审
    """
    if commit_type is None:
        return False
    return commit_type in enabled_types


def get_commit_type_description(commit_type: str) -> str:
    """获取 commit 类型描述"""
    return COMMIT_TYPES.get(commit_type, commit_type)


def is_force_commit(commit_message: str) -> bool:
    """检查是否为强制提交（跳过 AI 审查）

    Args:
        commit_message: commit message

    Returns:
        如果提交消息以 ' -f' 结尾，则返回 True
    """
    if not commit_message:
        return False

    # 检查提交消息是否以 -f 结尾（支持空格）
    first_line = commit_message.split("\n", 1)[0].strip()
    return first_line.endswith(" -f") or first_line.endswith("-f")
