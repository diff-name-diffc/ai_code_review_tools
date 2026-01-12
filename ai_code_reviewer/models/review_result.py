"""评审结果数据模型"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class SeverityLevel(str, Enum):
    """问题严重级别"""

    CRITICAL = "critical"  # 致命错误，拦截提交
    WARNING = "warning"  # 警告，仅显示
    INFO = "info"  # 信息提示


class CodeIssue(BaseModel):
    """代码问题"""

    file_path: str = Field(description="文件路径")
    line_number: Optional[int] = Field(None, description="行号")
    severity: SeverityLevel = Field(description="严重级别")
    category: str = Field(description="问题类别")
    description: str = Field(description="问题描述")
    suggestion: Optional[str] = Field(None, description="修复建议")


class ReviewResult(BaseModel):
    """评审结果"""

    commit_type: str = Field(description="Commit 类型")
    has_critical: bool = Field(description="是否有致命错误")
    issues: list[CodeIssue] = Field(default_factory=list, description="问题列表")
    summary: str = Field(description="评审摘要")
    overall_assessment: str = Field(description="总体评估: approve/warning/reject")
