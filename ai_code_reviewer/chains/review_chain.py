"""LangChain 评审链"""

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

        # 精简 diff
        if config.diff_process.enabled:
            diff_to_send = process_diff(git_info.staged_diff, config.diff_process)
        else:
            diff_to_send = git_info.staged_diff

        return {
            "diff": diff_to_send,
            "commit_message": git_info.commit_message,
            "commit_type": commit_type,
        }

    def get_prompt_for_type(inputs: dict[str, Any]) -> dict[str, Any]:
        """获取对应类型的 prompt"""
        commit_type = inputs.get("commit_type", "feat")
        prompt = PromptFactory.get_prompt(commit_type)
        return {"prompt": prompt, "inputs": inputs}

    def invoke_llm(data: dict[str, Any]) -> str:
        """调用 LLM"""
        prompt = data["prompt"]
        inputs = data["inputs"]
        chain = prompt | llm | StrOutputParser()
        return chain.invoke(inputs)

    # 完整的评审链
    review_chain = (
        RunnableLambda(prepare_input)
        | RunnableLambda(get_prompt_for_type)
        | RunnableLambda(invoke_llm)
        | review_parser
    )

    return review_chain
