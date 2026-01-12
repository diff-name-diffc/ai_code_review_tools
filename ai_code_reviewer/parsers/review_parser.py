"""评审结果解析器"""

import json
import re
from typing import Any

from langchain_core.exceptions import OutputParserException
from langchain_core.output_parsers import BaseOutputParser
from langchain_core.outputs import Generation

from ..models.review_result import CodeIssue, ReviewResult, SeverityLevel


class ReviewOutputParser(BaseOutputParser[ReviewResult]):
    """评审结果解析器"""

    def parse(self, text: str) -> ReviewResult:
        """解析 LLM 输出

        Args:
            text: LLM 返回的文本

        Returns:
            ReviewResult: 评审结果

        Raises:
            OutputParserException: 解析失败
        """
        # 尝试提取 JSON
        json_str = self._extract_json(text)
        if not json_str:
            raise OutputParserException(f"无法从输出中提取 JSON: {text[:200]}...")

        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise OutputParserException(f"JSON 解析失败: {e}")

        # 验证并构建结果
        try:
            issues = [
                CodeIssue(
                    file_path=issue.get("file_path", "unknown"),
                    line_number=issue.get("line_number"),
                    severity=SeverityLevel(issue.get("severity", "info")),
                    category=issue.get("category", "general"),
                    description=issue.get("description", ""),
                    suggestion=issue.get("suggestion"),
                )
                for issue in data.get("issues", [])
            ]

            return ReviewResult(
                commit_type=data.get("commit_type", "unknown"),
                has_critical=data.get("has_critical", False),
                issues=issues,
                summary=data.get("summary", ""),
                overall_assessment=data.get("overall_assessment", "warning"),
            )
        except Exception as e:
            raise OutputParserException(f"结果构建失败: {e}")

    def _extract_json(self, text: str) -> str | None:
        """从文本中提取 JSON

        尝试多种方式提取 JSON 内容
        """
        # 方式1: 直接解析
        text = text.strip()
        try:
            json.loads(text)
            return text
        except json.JSONDecodeError:
            pass

        # 方式2: 提取 ```json ... ``` 中的内容
        json_block = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
        if json_block:
            try:
                json.loads(json_block.group(1))
                return json_block.group(1)
            except json.JSONDecodeError:
                pass

        # 方式3: 提取 ``` ... ``` 中的内容
        code_block = re.search(r"```\s*(.*?)\s*```", text, re.DOTALL)
        if code_block:
            try:
                json.loads(code_block.group(1))
                return code_block.group(1)
            except json.JSONDecodeError:
                pass

        # 方式4: 查找 { ... }
        brace_match = re.search(r"\{.*\}", text, re.DOTALL)
        if brace_match:
            try:
                json.loads(brace_match.group(0))
                return brace_match.group(0)
            except json.JSONDecodeError:
                pass

        return None

    def parse_result(self, result: Any, *, partial: bool = False) -> ReviewResult:
        """解析 Generation 结果"""
        # 处理列表
        if isinstance(result, list):
            if result and isinstance(result[0], Generation):
                return self.parse(result[0].text)
        # 处理单个 Generation
        if isinstance(result, Generation):
            return self.parse(result.text)
        raise NotImplementedError(f"不支持的类型: {type(result)}")


# 单例实例
review_parser = ReviewOutputParser()
