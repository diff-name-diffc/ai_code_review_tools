"""Git 操作封装模块"""

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


def get_staged_diff(max_file_size: int = 100_000) -> str:
    """获取暂存区的变更内容

    Args:
        max_file_size: 超过此大小的文件将被跳过

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

    # 过滤大文件（只检查存在的文件）
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


def get_commit_message() -> str:
    """获取 commit message

    从以下位置按优先级读取：
    1. 环境变量 GIT_COMMITTER_NAME 或其他 Git hook 相关变量
    2. .git/COMMIT_EDITMSG 文件
    3. git log 最后一条（用于测试）
    """
    # pre-commit hook 阶段，尝试从环境变量读取
    # Git 在执行 hook 时会设置一些环境变量
    commit_msg = os.getenv("COMMIT_MSG")
    if commit_msg:
        return commit_msg.strip()

    # 从 .git/COMMIT_EDITMSG 读取
    git_root = get_git_root()
    commit_msg_file = git_root / ".git" / "COMMIT_EDITMSG"

    if commit_msg_file.exists():
        content = commit_msg_file.read_text(encoding="utf-8").strip()
        if content:
            return content

    # fallback: 从 git log 获取最后一条（用于测试）
    try:
        return run_git_command(["log", "-1", "--pretty=%B"])
    except subprocess.CalledProcessError:
        return ""


def get_git_info(max_file_size: int = 100_000) -> GitInfo:
    """获取 Git 信息

    Args:
        max_file_size: 最大文件大小

    Returns:
        GitInfo: Git 信息
    """
    commit_message = get_commit_message()
    staged_diff = get_staged_diff(max_file_size=max_file_size)

    return GitInfo(
        commit_message=commit_message,
        staged_diff=staged_diff,
    )
