"""配置数据模型"""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class LLMConfig(BaseModel):
    """LLM 配置"""

    model: str = Field(default="gpt-4o", description="模型名称")
    api_key: str = Field(description="API Key")
    base_url: Optional[str] = Field(None, description="Base URL，支持 ollama 等兼容接口")
    temperature: float = Field(default=0.1, description="温度参数")
    max_tokens: int = Field(default=2000, description="最大 token 数")
    timeout: int = Field(default=30, description="超时时间（秒）")


class ReviewerConfig(BaseModel):
    """评审器配置"""

    model_config = ConfigDict(extra="ignore")

    llm: LLMConfig = Field(description="LLM 配置")
    enabled_types: list[str] = Field(
        default=["feat", "fix", "refactor", "doc", "config"],
        description="启用的 commit 类型",
    )
    max_file_size: int = Field(
        default=100_000, description="跳过超过此大小的文件（字节）"
    )
    excluded_patterns: list[str] = Field(
        default=["*.lock", "package-lock.json"], description="排除的文件 glob 模式"
    )
    output_file: Optional[str] = Field(None, description="可选的日志文件路径")
