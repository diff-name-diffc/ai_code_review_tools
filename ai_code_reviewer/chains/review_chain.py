"""LangChain 评审链"""

import logging
from pathlib import Path
from typing import Any

from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableLambda, RunnablePassthrough

from ..commit_parser import parse_commit_type
from ..config import load_config
from ..diff_processor import process_diff
from ..git_helper import GitInfo, get_git_info
from ..models.config import ReviewerConfig
from ..models.review_result import ReviewResult
from ..parsers.review_parser import review_parser
from ..prompts.templates import PromptFactory

# 配置日志
logger = logging.getLogger(__name__)


def setup_debug_logging(verbose: bool = False, log_file: str | None = None):
    """设置调试日志

    Args:
        verbose: 是否输出到控制台
        log_file: 日志文件路径（可选）
    """
    handlers = []

    if verbose:
        # 控制台输出
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(
            logging.Formatter('\n[DEBUG] %(message)s')
        )
        handlers.append(console_handler)

    if log_file:
        # 文件输出
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(message)s')
        )
        handlers.append(file_handler)

    if handlers:
        logger.setLevel(logging.DEBUG)
        for handler in handlers:
            logger.addHandler(handler)


def create_review_chain(
    config: ReviewerConfig | None = None,
    git_info: GitInfo | None = None,
    commit_msg_file_path: Path | None = None,
):
    """创建评审链

    使用 LCEL 构建：
    1. 获取 Git 信息
    2. 解析 commit 类型
    3. 获取对应的 prompt
    4. 调用 LLM
    5. 解析结果

    Args:
        config: 配置对象，如果为 None 则自动加载
        git_info: Git 信息，如果提供则复用，否则重新获取
        commit_msg_file_path: commit message 文件路径（用于 commit-msg hook）

    Returns:
        评审链
    """
    if config is None:
        config = load_config()

    # 初始化 LLM
    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(
        model=config.llm.model,
        api_key=config.llm.api_key,
        base_url=config.llm.base_url,
        temperature=config.llm.temperature,
        max_tokens=config.llm.max_tokens,
        timeout=config.llm.timeout,
    )

    # 构建链
    def prepare_input(_: Any) -> dict[str, Any]:
        """准备输入"""
        # 如果外部已提供 git_info，则复用；否则重新获取
        nonlocal git_info
        if git_info is None:
            git_info = get_git_info(
                max_file_size=config.max_file_size,
                included_extensions=config.included_extensions,
                excluded_patterns=config.excluded_patterns,
                commit_msg_file_path=commit_msg_file_path,
            )
        commit_type = parse_commit_type(git_info.commit_message)

        # === 调试日志：原始 diff ===
        logger.debug("=" * 80)
        logger.debug("【1. 原始 DIFF 内容】")
        logger.debug("=" * 80)
        logger.debug(f"原始 diff 长度: {len(git_info.staged_diff)} 字符")
        logger.debug("-" * 40)
        logger.debug(git_info.staged_diff)

        # 精简 diff
        if config.diff_process.enabled:
            diff_to_send = process_diff(git_info.staged_diff, config.diff_process)
        else:
            diff_to_send = git_info.staged_diff

        # === 调试日志：精简后的 diff ===
        logger.debug("=" * 80)
        logger.debug("【2. 精简后 DIFF 内容】")
        logger.debug("=" * 80)
        logger.debug(f"精简配置: max_files={config.diff_process.max_files}, "
                     f"max_hunks={config.diff_process.max_hunks_per_file}, "
                     f"context={config.diff_process.context_lines}, "
                     f"max_lines={config.diff_process.max_total_lines}")
        logger.debug(f"精简后 diff 长度: {len(diff_to_send)} 字符")
        logger.debug("-" * 40)
        logger.debug(diff_to_send)

        # === 调试日志：Commit 信息 ===
        logger.debug("=" * 80)
        logger.debug("【3. COMMIT 信息】")
        logger.debug("=" * 80)
        logger.debug(f"Commit 类型: {commit_type}")
        logger.debug(f"Commit 消息: {git_info.commit_message}")

        return {
            "diff": diff_to_send,
            "commit_message": git_info.commit_message,
            "commit_type": commit_type,
        }

    def get_prompt_for_type(inputs: dict[str, Any]) -> dict[str, Any]:
        """获取对应类型的 prompt"""
        commit_type = inputs.get("commit_type", "feat")
        prompt = PromptFactory.get_prompt(commit_type)

        # === 调试日志：Prompt 模板 ===
        logger.debug("=" * 80)
        logger.debug("【4. PROMPT 模板】")
        logger.debug("=" * 80)
        logger.debug(f"Commit 类型: {commit_type}")
        logger.debug("-" * 40)
        logger.debug("Prompt messages:")
        for msg in prompt.messages:
            # 获取消息类型名称
            msg_type = type(msg).__name__
            logger.debug(f"  Role: {msg_type}")
            # 获取模板内容
            if hasattr(msg, 'prompt') and hasattr(msg.prompt, 'template'):
                logger.debug(f"  Template: {msg.prompt.template}")
            else:
                logger.debug(f"  Content: {msg}")
            logger.debug("-" * 20)

        return {"prompt": prompt, "inputs": inputs}

    def invoke_llm(data: dict[str, Any]) -> str:
        """调用 LLM"""
        prompt = data["prompt"]
        inputs = data["inputs"]

        # === 调试日志：最终发送给 LLM 的完整内容 ===
        logger.debug("=" * 80)
        logger.debug("【5. 最终发送给 LLM 的完整内容】")
        logger.debug("=" * 80)

        # 构建最终消息
        final_messages = prompt.format_messages(
            diff=inputs["diff"],
            commit_message=inputs["commit_message"]
        )

        for i, msg in enumerate(final_messages, 1):
            logger.debug(f"--- Message {i} ---")
            logger.debug(f"Type: {type(msg).__name__}")
            logger.debug(f"Content:\n{msg.content}")
            logger.debug("")

        logger.debug("=" * 80)
        logger.debug("【6. 调用 LLM API】")
        logger.debug("=" * 80)
        logger.debug(f"Model: {config.llm.model}")
        logger.debug(f"Base URL: {config.llm.base_url}")
        logger.debug(f"Temperature: {config.llm.temperature}")
        logger.debug(f"Max Tokens: {config.llm.max_tokens}")

        chain = prompt | llm | StrOutputParser()
        result = chain.invoke(inputs)

        # === 调试日志：LLM 原始响应 ===
        logger.debug("=" * 80)
        logger.debug("【7. LLM 原始响应】")
        logger.debug("=" * 80)
        logger.debug(result)
        logger.debug("=" * 80)

        return {
            "raw_response": result,
            "commit_type": inputs["commit_type"],
        }

    # 完整的评审链
    review_chain = (
        RunnableLambda(prepare_input)
        | RunnableLambda(get_prompt_for_type)
        | RunnableLambda(invoke_llm)
        | RunnableLambda(lambda data: {
            "result": review_parser.parse(data["raw_response"]),
            "commit_type": data["commit_type"],
        })
        | RunnableLambda(lambda data: (
            setattr(data["result"], "commit_type", data["commit_type"]) or data["result"]
        ))
    )

    return review_chain
