"""CLI 入口 - pre-commit hook"""

import sys
from pathlib import Path
from typing import Optional

import click

from .chains import create_review_chain
from .commit_parser import is_force_commit, parse_commit_type, should_review
from .config import create_default_config, find_config_file, load_config
from .git_helper import get_git_info
from .models.review_result import ReviewResult, SeverityLevel


def print_review_result(result: ReviewResult, commit_message: str = ""):
    """打印评审结果

    Args:
        result: 评审结果
        commit_message: 提交消息
    """
    # 分隔线
    separator = "=" * 60
    click.echo()
    click.echo(separator)
    click.echo(f"  AI 代码评审报告")
    click.echo(separator)

    # 显示提交消息
    if commit_message:
        # 只显示第一行（标题）
        first_line = commit_message.split("\n", 1)[0].strip()
        click.echo(f"提交消息: {first_line}")

    click.echo(f"Commit 类型: {result.commit_type}")
    click.echo(f"总体评估: {result.overall_assessment.upper()}")
    click.echo(separator)
    click.echo(f"摘要: {result.summary}")
    click.echo(separator)

    if result.issues:
        click.echo(f"发现问题: {len(result.issues)} 个")
        click.echo(separator)

        for i, issue in enumerate(result.issues, 1):
            # 根据严重级别显示不同颜色
            if issue.severity == SeverityLevel.CRITICAL:
                icon = "[致命]"
                color = "red"
            elif issue.severity == SeverityLevel.WARNING:
                icon = "[警告]"
                color = "yellow"
            else:
                icon = "[信息]"
                color = "blue"

            click.echo(f"{i}. {click.style(icon, fg=color)} {issue.category}")
            click.echo(f"   文件: {issue.file_path}")
            if issue.line_number:
                click.echo(f"   行号: {issue.line_number}")
            click.echo(f"   描述: {issue.description}")
            if issue.suggestion:
                click.echo(f"   建议: {issue.suggestion}")
            click.echo()

    else:
        click.echo(click.style("没有发现问题", fg="green"))

    click.echo(separator)
    click.echo()


def print_compact_summary(result: ReviewResult):
    """打印紧凑的问题摘要（用于 pre-commit 输出）"""
    if not result.issues:
        return

    # 统计各级别问题
    warning_count = sum(1 for i in result.issues if i.severity == SeverityLevel.WARNING)
    info_count = sum(1 for i in result.issues if i.severity == SeverityLevel.INFO)

    # 只显示警告和信息
    non_critical = [i for i in result.issues if i.severity != SeverityLevel.CRITICAL]
    if not non_critical:
        return

    click.echo()
    click.echo(click.style("AI 代码评审 - 问题摘要:", bold=True))

    for issue in non_critical:
        if issue.severity == SeverityLevel.WARNING:
            icon = click.style("[警告]", fg="yellow")
        else:
            icon = click.style("[信息]", fg="blue")

        click.echo(f"  {icon} {issue.file_path}:{issue.line_number or '?'} - {issue.description}")

    # 统计信息
    parts = []
    if warning_count > 0:
        parts.append(f"{warning_count} 个警告")
    if info_count > 0:
        parts.append(f"{info_count} 个信息")

    if parts:
        click.echo(f"  共: {', '.join(parts)}")
    click.echo()


def save_review_log(result: ReviewResult, log_file: Path):
    """保存评审日志"""
    log_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")


@click.group()
def cli():
    """AI Code Reviewer - 基于 LangChain 的代码评审工具"""
    pass


@cli.command()
@click.option("--config", "-c", type=click.Path(exists=True), help="配置文件路径")
@click.argument("commit_msg_file", type=click.Path(exists=True), required=False)
def commit_msg_review(config: Optional[str], commit_msg_file: Optional[str]):
    """用于 commit-msg hook 的代码评审

    这个命令专门用于 commit-msg hook，可以正确获取当前的 commit message。

    Args:
        commit_msg_file: commit message 文件路径（Git 会自动传入）
    """
    try:
        # 加载配置
        if config:
            cfg = load_config(Path(config))
        else:
            cfg = load_config()

        # 获取 commit message 文件路径
        commit_msg_path = Path(commit_msg_file) if commit_msg_file else None

        # 获取 Git 信息并检查是否需要评审
        git_info = get_git_info(
            max_file_size=cfg.max_file_size, commit_msg_file_path=commit_msg_path
        )
        commit_type = parse_commit_type(git_info.commit_message)

        # 检查是否为强制提交（跳过 AI 审查）
        if is_force_commit(git_info.commit_message):
            click.echo(
                click.style(
                    "[强制提交] 检测到 -f 标志，跳过 AI 审查", fg="cyan", bold=True
                )
            )
            sys.exit(0)

        # 检查是否需要评审
        if not should_review(commit_type, cfg.enabled_types):
            click.echo(
                click.style(
                    f"[跳过] Commit 类型 '{commit_type}' 不在评审列表中", fg="yellow"
                )
            )
            sys.exit(0)

        # 没有变更内容，跳过评审
        if not git_info.staged_diff:
            click.echo(click.style("[跳过] 没有需要评审的变更", fg="yellow"))
            sys.exit(0)

        # 创建评审链
        chain = create_review_chain(cfg)

        # 执行评审
        click.echo("[AI 代码评审] 正在分析...")
        result: ReviewResult = chain.invoke({})

        # 打印结果（传入提交消息）
        print_review_result(result, git_info.commit_message)

        # 保存日志
        if cfg.output_file:
            log_file = Path(cfg.output_file)
            save_review_log(result, log_file)
            click.echo(f"评审日志已保存到: {log_file}")

        # 判断是否需要拦截
        if result.has_critical:
            click.echo(
                click.style("[拦截] 发现致命错误，请修复后重新提交", fg="red", bold=True)
            )
            sys.exit(1)
        else:
            # 评审通过，但显示警告和信息的紧凑摘要
            print_compact_summary(result)
            click.echo(click.style("[通过] 评审完成", fg="green"))
            sys.exit(0)

    except FileNotFoundError as e:
        click.echo(click.style(f"[错误] {e}", fg="red"), err=True)
        sys.exit(1)
    except ValueError as e:
        # 处理 commit message 获取失败的情况
        click.echo(click.style(f"[错误] {e}", fg="red"), err=True)
        click.echo("\n提示：请确保在 Git commit-msg hook 中调用此命令。", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(click.style(f"[错误] 评审失败: {e}", fg="red"), err=True)
        import traceback

        traceback.print_exc()
        sys.exit(1)


@cli.command()
@click.option("--config", "-c", type=click.Path(exists=True), help="配置文件路径")
def review(config: Optional[str]):
    """执行代码评审"""
    try:
        # 加载配置
        if config:
            cfg = load_config(Path(config))
        else:
            cfg = load_config()

        # 获取 Git 信息并检查是否需要评审
        git_info = get_git_info(max_file_size=cfg.max_file_size)
        commit_type = parse_commit_type(git_info.commit_message)

        # 检查是否为强制提交（跳过 AI 审查）
        if is_force_commit(git_info.commit_message):
            click.echo(
                click.style(
                    "[强制提交] 检测到 -f 标志，跳过 AI 审查", fg="cyan", bold=True
                )
            )
            sys.exit(0)

        # 检查是否需要评审
        if not should_review(commit_type, cfg.enabled_types):
            click.echo(
                click.style(
                    f"[跳过] Commit 类型 '{commit_type}' 不在评审列表中", fg="yellow"
                )
            )
            sys.exit(0)

        # 没有变更内容，跳过评审
        if not git_info.staged_diff:
            click.echo(click.style("[跳过] 没有需要评审的变更", fg="yellow"))
            sys.exit(0)

        # 创建评审链
        chain = create_review_chain(cfg)

        # 执行评审
        click.echo("[AI 代码评审] 正在分析...")
        result: ReviewResult = chain.invoke({})

        # 打印结果（传入提交消息）
        print_review_result(result, git_info.commit_message)

        # 保存日志
        if cfg.output_file:
            log_file = Path(cfg.output_file)
            save_review_log(result, log_file)
            click.echo(f"评审日志已保存到: {log_file}")

        # 判断是否需要拦截
        if result.has_critical:
            click.echo(
                click.style("[拦截] 发现致命错误，请修复后重新提交", fg="red", bold=True)
            )
            sys.exit(1)
        else:
            # 评审通过，但显示警告和信息的紧凑摘要
            print_compact_summary(result)
            click.echo(click.style("[通过] 评审完成", fg="green"))
            sys.exit(0)

    except FileNotFoundError as e:
        click.echo(click.style(f"[错误] {e}", fg="red"), err=True)
        sys.exit(1)
    except ValueError as e:
        # 处理 commit message 获取失败的情况
        click.echo(click.style(f"[错误] {e}", fg="red"), err=True)
        click.echo("\n提示：review 命令可能无法准确获取 commit message。", err=True)
        click.echo("建议：使用 commit-msg-review 命令或通过 Git hook 自动调用。", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(click.style(f"[错误] 评审失败: {e}", fg="red"), err=True)
        import traceback

        traceback.print_exc()
        sys.exit(1)


# Git commit-msg hook 脚本
COMMIT_MSG_HOOK_SCRIPT = """#!/bin/sh
# AI Code Reviewer - commit-msg hook
# 此脚本会在输入 commit message 后执行

# 获取 commit message 文件路径（Git 自动传入第一个参数）
COMMIT_MSG_FILE="$1"

# 执行 AI 代码评审
ai-code-reviewer commit-msg-review "$COMMIT_MSG_FILE"
"""


def is_valid_git_repository(base_path: Path) -> tuple[bool, str]:
    """验证路径是否位于有效的 Git 仓库内

    Args:
        base_path: 要检查的基础路径（通常是当前工作目录）

    Returns:
        (是否有效, 错误消息)
    """
    git_dir = base_path / ".git"

    # 检查 .git 目录是否存在
    if not git_dir.exists():
        return False, f"未找到 .git 目录: {git_dir}"

    # 检查 .git 是否为目录（而非文件，如 git worktree 的情况）
    if not git_dir.is_dir():
        # .git 可能是文件（git worktree 场景），读取文件内容找到真实的 git 目录
        try:
            git_file_content = git_dir.read_text(encoding="utf-8").strip()
            if git_file_content.startswith("gitdir:"):
                # 这是一个 worktree，暂时不支持
                return False, ".git 是 worktree 引用文件，请在主仓库目录运行 init 命令"
        except Exception as e:
            return False, f".git 文件格式无效: {e}"
        return False, ".git 不是目录"

    # 验证关键的 Git 仓库文件
    git_head = git_dir / "HEAD"
    git_config = git_dir / "config"

    if not git_head.exists():
        return False, "无效的 Git 仓库：缺少 .git/HEAD 文件"

    if not git_config.exists():
        return False, "无效的 Git 仓库：缺少 .git/config 文件"

    # 验证 HEAD 文件格式
    try:
        head_content = git_head.read_text(encoding="utf-8").strip()
        # HEAD 应该是 "ref: refs/heads/xxx" 或一个 commit hash
        if not (head_content.startswith("ref:") or len(head_content) == 40):
            return False, "无效的 Git 仓库：.git/HEAD 内容格式错误"
    except Exception as e:
        return False, f"无法读取 .git/HEAD: {e}"

    return True, ""


def validate_hook_path_safety(hook_path: Path, hooks_dir: Path) -> tuple[bool, str]:
    """验证 hook 文件路径的安全性

    Args:
        hook_path: hook 文件路径
        hooks_dir: hooks 目录路径

    Returns:
        (是否安全, 错误消息)
    """
    try:
        # 1. 确保路径在 .git/hooks 目录下（防止路径遍历攻击）
        resolved_hook = hook_path.resolve()
        resolved_hooks_dir = hooks_dir.resolve()

        if not str(resolved_hook).startswith(str(resolved_hooks_dir)):
            return False, f"安全错误: hook 路径 {resolved_hook} 不在 hooks 目录 {resolved_hooks_dir} 下"

        # 2. 检查是否为符号链接
        if hook_path.is_symlink():
            link_target = hook_path.readlink()
            return False, f"安全错误: hook 文件是符号链接，指向 {link_target}。请手动处理符号链接。"

        # 3. 如果文件存在，检查是否为普通文件
        if hook_path.exists():
            # 使用 stat 检查文件类型
            stat_info = hook_path.stat()
            import stat
            if not stat.S_ISREG(stat_info.st_mode):
                return False, f"安全错误: hook 路径不是普通文件（可能是设备、管道等）"

        return True, ""

    except Exception as e:
        return False, f"路径验证失败: {e}"


def safe_write_hook_file(hook_path: Path, content: str) -> None:
    """安全地写入 hook 文件

    Args:
        hook_path: hook 文件路径
        content: 文件内容

    Raises:
        ValueError: 如果路径不安全
    """
    # 先写入临时文件，然后原子性重命名
    temp_path = hook_path.with_suffix('.tmp')
    try:
        temp_path.write_text(content, encoding="utf-8")
        temp_path.chmod(0o755)
        # 原子性重命名
        temp_path.replace(hook_path)
    except Exception as e:
        # 清理临时文件
        if temp_path.exists():
            temp_path.unlink()
        raise e


@cli.command()
@click.option("--path", "-p", type=click.Path(), help="配置文件保存路径")
@click.option("--force", "-f", is_flag=True, help="强制覆盖已存在的 commit-msg hook")
def init(path: Optional[str], force: bool):
    """初始化配置文件"""
    try:
        # 创建 AI Reviewer 配置文件
        config_path = create_default_config(Path(path) if path else None)
        click.echo(
            click.style(
                f"[成功] 配置文件已创建: {config_path}", fg="green", bold=True
            )
        )
        click.echo("\n请编辑配置文件，设置你的 API Key 等信息。")

        # 验证是否在有效的 Git 仓库内
        is_valid, error_msg = is_valid_git_repository(Path.cwd())
        if not is_valid:
            click.echo(
                click.style(
                    f"\n[错误] {error_msg}",
                    fg="red"
                ),
                err=True
            )
            click.echo(
                "\n提示：请确保在 Git 仓库根目录下运行此命令。",
                err=True
            )
            return

        # 安装 Git commit-msg hook
        git_hooks_dir = Path.cwd() / ".git" / "hooks"
        if git_hooks_dir.exists():
            commit_msg_hook_path = git_hooks_dir / "commit-msg"

            # 安全性验证
            is_safe, error_msg = validate_hook_path_safety(commit_msg_hook_path, git_hooks_dir)
            if not is_safe:
                click.echo(click.style(f"\n[错误] {error_msg}", fg="red"), err=True)
                click.echo("\n请手动处理该文件后重新运行 init 命令。")
                click.echo("需要添加的内容：")
                click.echo(click.style(COMMIT_MSG_HOOK_SCRIPT, fg="cyan"))
                return

            # 检查是否已存在 hook
            if commit_msg_hook_path.exists():
                # 如果使用 --force 选项，显示警告后直接覆盖
                if force:
                    try:
                        # 读取并显示现有内容（让用户知道被覆盖的内容）
                        existing_content = commit_msg_hook_path.read_text(encoding="utf-8")
                        click.echo(
                            click.style(
                                f"\n[警告] 使用 --force 选项，将覆盖现有 hook: {commit_msg_hook_path}",
                                fg="yellow",
                                bold=True
                            )
                        )
                        click.echo("原有内容：")
                        click.echo(click.style(existing_content, fg="cyan", dim=True))

                        # 直接覆盖
                        safe_write_hook_file(commit_msg_hook_path, COMMIT_MSG_HOOK_SCRIPT)
                        click.echo(
                            click.style(
                                f"\n[成功] Git commit-msg hook 已覆盖: {commit_msg_hook_path}",
                                fg="green",
                                bold=True,
                            )
                        )
                    except Exception as e:
                        click.echo(
                            click.style(f"\n[错误] 覆盖 hook 文件失败: {e}", fg="red"),
                            err=True
                        )
                        return
                else:
                    # 非 force 模式，使用原有的智能追加逻辑
                    try:
                        # 读取现有 hook 内容
                        existing_content = commit_msg_hook_path.read_text(encoding="utf-8")
                    except Exception as e:
                        click.echo(
                            click.style(f"\n[错误] 无法读取现有 hook 文件: {e}", fg="red"),
                            err=True
                        )
                        return

                    # 检查是否已包含 AI reviewer 调用
                    ai_reviewer_marker = "ai-code-reviewer commit-msg-review"
                    if ai_reviewer_marker in existing_content:
                        click.echo(
                            click.style(
                                f"\n[成功] commit-msg hook 已包含 AI 代码评审功能",
                                fg="green",
                            )
                        )
                    else:
                        # 询问用户是否追加
                        click.echo(
                            click.style(
                                f"\n[警告] commit-msg hook 已存在: {commit_msg_hook_path}",
                                fg="yellow",
                            )
                        )
                        click.echo("现有内容：")
                        click.echo(click.style(existing_content, fg="cyan", dim=True))

                        if click.confirm("\n是否在现有 hook 中追加 AI 代码评审功能？", default=True):
                            try:
                                # 在现有内容后追加 AI reviewer 调用
                                # 确保有换行符分隔
                                separator = "\n" if not existing_content.endswith("\n") else ""
                                new_content = existing_content + separator + "\n# AI Code Reviewer\n" + "ai-code-reviewer commit-msg-review \"$1\"\n"

                                # 使用安全写入方法
                                safe_write_hook_file(commit_msg_hook_path, new_content)

                                click.echo(
                                    click.style(
                                        f"\n[成功] 已将 AI 代码评审功能追加到 commit-msg hook",
                                        fg="green",
                                        bold=True,
                                    )
                                )
                            except Exception as e:
                                click.echo(
                                    click.style(f"\n[错误] 写入 hook 文件失败: {e}", fg="red"),
                                    err=True
                                )
                                return
                        else:
                            click.echo("\n跳过 hook 安装。如需手动添加，请在 hook 中添加以下内容：")
                            click.echo(click.style(COMMIT_MSG_HOOK_SCRIPT, fg="cyan"))
                            click.echo("\n提示：你也可以使用 --force 选项强制覆盖：")
                            click.echo(click.style("  ai-code-reviewer init --force", fg="cyan"))
                            return
            else:
                # 创建 commit-msg hook
                try:
                    safe_write_hook_file(commit_msg_hook_path, COMMIT_MSG_HOOK_SCRIPT)
                    click.echo(
                        click.style(
                            f"\n[成功] Git commit-msg hook 已创建: {commit_msg_hook_path}",
                            fg="green",
                            bold=True,
                        )
                    )
                except Exception as e:
                    click.echo(
                        click.style(f"\n[错误] 创建 hook 文件失败: {e}", fg="red"),
                        err=True
                    )
                    return

            # 统一的使用说明
            click.echo("\n现在你可以正常提交代码，AI 会自动评审：")
            click.echo(click.style('  git commit -m "feat: 你的提交消息"', fg="cyan"))
            click.echo("\n使用 -f 标志可以跳过 AI 审查：")
            click.echo(
                click.style('  git commit -m "feat: 紧急修复 -f"', fg="cyan")
            )
        else:
            click.echo(
                click.style(
                    "\n[警告] 未找到 .git 目录，请确保在 Git 仓库根目录执行此命令",
                    fg="yellow",
                )
            )

    except FileExistsError as e:
        click.echo(click.style(f"[错误] {e}", fg="red"), err=True)
        sys.exit(1)


@cli.command()
def check():
    """检查配置是否正确"""
    try:
        config_path = find_config_file()
        if not config_path:
            click.echo(click.style("[错误] 未找到配置文件", fg="red"), err=True)
            click.echo("请运行: ai-code-reviewer init")
            sys.exit(1)

        click.echo(f"配置文件: {config_path}")
        cfg = load_config(config_path)
        click.echo(f"模型: {cfg.llm.model}")
        click.echo(f"Base URL: {cfg.llm.base_url or '默认'}")
        click.echo(f"启用的类型: {', '.join(cfg.enabled_types)}")
        click.echo(click.style("[成功] 配置有效", fg="green"))

    except Exception as e:
        click.echo(click.style(f"[错误] 配置检查失败: {e}", fg="red"), err=True)
        sys.exit(1)


# pre-commit hook 入口点
def main():
    """主入口点"""
    cli()


if __name__ == "__main__":
    main()
