"""LangChain 评审链"""

from typing import Any

from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableLambda, RunnablePassthrough

from ..commit_parser import parse_commit_type
from ..config import load_config
from ..git_helper import get_git_info
from ..models.config import ReviewerConfig
from ..models.review_result import ReviewResult
from ..parsers.review_parser import review_parser
from ..prompts.templates import PromptFactory


def create_review_chain(config: ReviewerConfig | None = None):
    """创建评审链

    使用 LCEL 构建：
    1. 获取 Git 信息
    2. 解析 commit 类型
    3. 获取对应的 prompt
    4. 调用 LLM
    5. 解析结果

    Args:
        config: 配置对象，如果为 None 则自动加载

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
        git_info = get_git_info(max_file_size=config.max_file_size)
        commit_type = parse_commit_type(git_info.commit_message)

        return {
            "diff": git_info.staged_diff,
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
