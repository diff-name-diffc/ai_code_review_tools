"""Git 操作封装模块"""

import fnmatch
import os
import subprocess
from pathlib import Path

from pydantic import BaseModel


class GitInfo(BaseModel):
    """Git 信息"""

    commit_message: str
    staged_diff: str
    commit_type: str | None = None


def run_git_command(args: list[str], cwd: Path | None = None) -> str:
    """运行 git 命令

    Args:
        args: git 命令参数
        cwd: 工作目录

    Returns:
        命令输出

    Raises:
        subprocess.CalledProcessError: 命令执行失败
    """
    result = subprocess.run(
        ["git"] + args,
        capture_output=True,
        text=True,
        check=True,
        cwd=cwd or Path.cwd(),
    )
    return result.stdout.strip()


def get_git_root() -> Path:
    """获取 Git 仓库根目录"""
    root = run_git_command(["rev-parse", "--show-toplevel"])
    return Path(root)


def filter_files_by_pattern(
    file_list: list[str],
    included_extensions: list[str] | None = None,
    excluded_patterns: list[str] | None = None,
) -> list[str]:
    """按白名单和黑名单过滤文件

    Args:
        file_list: 文件路径列表
        included_extensions: 白名单后缀（如 [".py", ".js"]），为空则不过滤
        excluded_patterns: 黑名单 glob 模式（如 ["*.lock"]）

    Returns:
        过滤后的文件列表
    """
    filtered = []
    for file_path in file_list:
        path = Path(file_path)

        # 白名单检查
        if included_extensions:
            ext = path.suffix.lower()
            allowed_exts = [e.lower() for e in included_extensions]
            if ext not in allowed_exts:
                continue

        # 黑名单检查
        if excluded_patterns:
            if any(fnmatch.fnmatch(file_path, p) for p in excluded_patterns):
                continue

        filtered.append(file_path)
    return filtered


def get_staged_diff(
    max_file_size: int = 100_000,
    included_extensions: list[str] | None = None,
    excluded_patterns: list[str] | None = None,
) -> str:
    """获取暂存区的变更内容

    Args:
        max_file_size: 超过此大小的文件将被跳过
        included_extensions: 白名单后缀，为空则不过滤
        excluded_patterns: 黑名单 glob 模式

    Returns:
        diff 内容
    """
    try:
        # 获取所有暂存的文件
        files = run_git_command(["diff", "--cached", "--name-only", "-z"])
    except subprocess.CalledProcessError:
        return ""

    if not files:
        return ""

    file_list = [f for f in files.split("\0") if f]
    git_root = get_git_root()

    # 第一步：按后缀和模式过滤
    if included_extensions or excluded_patterns:
        file_list = filter_files_by_pattern(
            file_list,
            included_extensions=included_extensions,
            excluded_patterns=excluded_patterns,
        )

    if not file_list:
        return ""

    # 第二步：过滤大文件（只检查存在的文件）
    filtered_files = []
    for file_path in file_list:
        full_path = git_root / file_path
        if full_path.exists() and full_path.stat().st_size > max_file_size:
            print(f"[跳过] 文件过大: {file_path}")
        else:
            filtered_files.append(file_path)

    if not filtered_files:
        return ""

    # 获取 diff
    try:
        diff = run_git_command(["diff", "--cached", "--unified=5"] + filtered_files)
        return diff
    except subprocess.CalledProcessError:
        # 文件可能被删除或其他问题，返回所有文件的 diff
        try:
            return run_git_command(["diff", "--cached", "--unified=5"])
        except subprocess.CalledProcessError:
            return ""


def get_commit_message(commit_msg_file_path: Path | None = None) -> str:
    """获取 commit message

    Args:
        commit_msg_file_path: commit message 文件路径（用于 commit-msg hook）

    Returns:
        commit message 内容

    Raises:
        ValueError: 无法获取 commit message 时抛出异常

    读取优先级：
    1. 传入的 commit_msg_file_path 参数（commit-msg hook）- 最高优先级
    2. 环境变量 COMMIT_MSG
    3. .git/COMMIT_EDITMSG 文件（仅用于兼容性，不推荐）
    """
    # 优先从传入的文件路径读取（commit-msg hook）
    if commit_msg_file_path:
        if not commit_msg_file_path.exists():
            raise ValueError(f"Commit message 文件不存在: {commit_msg_file_path}")

        content = commit_msg_file_path.read_text(encoding="utf-8").strip()
        if not content:
            raise ValueError(f"Commit message 文件为空: {commit_msg_file_path}")

        return content

    # 从环境变量读取
    commit_msg = os.getenv("COMMIT_MSG")
    if commit_msg and commit_msg.strip():
        return commit_msg.strip()

    # 从 .git/COMMIT_EDITMSG 读取（仅用于兼容性）
    # 注意：这个文件可能包含旧的内容，不推荐依赖
    git_root = get_git_root()
    commit_msg_file = git_root / ".git" / "COMMIT_EDITMSG"

    if commit_msg_file.exists():
        content = commit_msg_file.read_text(encoding="utf-8").strip()
        if content:
            # 添加警告：这可能不是当前的 commit message
            import sys
            print(
                "[警告] 未从 commit-msg hook 获取消息，使用 COMMIT_EDITMSG 文件（可能不准确）",
                file=sys.stderr,
            )
            return content

    # 如果所有方式都失败，抛出错误而不是返回错误的内容
    raise ValueError(
        "无法获取 commit message。请确保：\n"
        "1. 使用 commit-msg hook 调用此工具\n"
        "2. 或设置 COMMIT_MSG 环境变量\n"
        "3. 或确保在 Git 仓库中且有提交历史"
    )


def get_git_info(
    max_file_size: int = 100_000,
    included_extensions: list[str] | None = None,
    excluded_patterns: list[str] | None = None,
    commit_msg_file_path: Path | None = None,
) -> GitInfo:
    """获取 Git 信息

    Args:
        max_file_size: 最大文件大小
        included_extensions: 白名单后缀
        excluded_patterns: 黑名单 glob 模式
        commit_msg_file_path: commit message 文件路径（用于 commit-msg hook）

    Returns:
        GitInfo: Git 信息
    """
    commit_message = get_commit_message(commit_msg_file_path)
    staged_diff = get_staged_diff(
        max_file_size=max_file_size,
        included_extensions=included_extensions,
        excluded_patterns=excluded_patterns,
    )

    return GitInfo(
        commit_message=commit_message,
        staged_diff=staged_diff,
    )
