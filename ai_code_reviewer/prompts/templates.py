"""LangChain 提示词模板"""

from langchain_core.prompts import ChatPromptTemplate

# 通用评审系统提示
SYSTEM_PROMPT = """你是一个专业的代码评审助手。你将根据 commit 类型和代码变更进行分析评审。

评审要求：
1. 仔细分析代码逻辑，发现潜在的错误、漏洞和不合理之处
2. 根据问题严重程度分类：critical（致命错误）、warning（警告）、info（信息）
3. critical 级别的例子：安全漏洞、严重的逻辑错误、破坏性变更、明显的 bug
4. warning 级别的例子：潜在的性能问题、代码异味、不完整的实现
5. 返回 JSON 格式的结构化结果

输出格式要求（严格遵守）：
{{
  "has_critical": true/false,
  "issues": [
    {{
      "file_path": "路径",
      "line_number": 行号或null,
      "severity": "critical/warning/info",
      "category": "问题类别",
      "description": "详细描述",
      "suggestion": "修复建议"
    }}
  ],
  "summary": "评审摘要",
  "overall_assessment": "approve/warning/reject"
}}"""


# 各类型的专门提示
FEAT_PROMPT = """
Commit 类型：feat（新功能）

评审重点：
- 功能实现的完整性和逻辑正确性
- 边界条件处理
- 错误处理是否完善
- 是否有潜在的运行时错误

变更内容：
```diff
{diff}
```

Commit 信息：{commit_message}
"""

FIX_PROMPT = """
Commit 类型：fix（修复 bug）

评审重点：
- 修复是否真正解决了问题
- 是否引入了新的 bug 或影响了原有正确逻辑
- 修复方式是否合理，有无副作用

变更内容：
```diff
{diff}
```

Commit 信息：{commit_message}
"""

REFACTOR_PROMPT = """
Commit 类型：refactor（重构）

评审重点：
- 重构是否保持了原有功能逻辑
- 是否有意外的行为变更
- 重构是否合理，有无引入新问题

变更内容：
```diff
{diff}
```

Commit 信息：{commit_message}
"""

DOC_PROMPT = """
Commit 类型：doc（文档变更）

评审重点：
- 文档内容是否有错误或遗漏
- 技术描述的逻辑是否正确
- 是否与代码实现一致

变更内容：
```diff
{diff}
```

Commit 信息：{commit_message}
"""

CONFIG_PROMPT = """
Commit 类型：config（配置变更）

评审重点：
- 配置变更的有效性和合理性
- 是否有配置冲突或错误
- 结合 commit 信息分析变更目的

变更内容：
```diff
{diff}
```

Commit 信息：{commit_message}
"""


class PromptFactory:
    """根据 commit 类型获取对应的 prompt 模板"""

    _prompts = {
        "feat": FEAT_PROMPT,
        "fix": FIX_PROMPT,
        "refactor": REFACTOR_PROMPT,
        "doc": DOC_PROMPT,
        "config": CONFIG_PROMPT,
    }

    @classmethod
    def get_prompt(cls, commit_type: str) -> ChatPromptTemplate:
        """获取指定类型的 prompt 模板

        Args:
            commit_type: commit 类型

        Returns:
            ChatPromptTemplate: 提示词模板
        """
        template = cls._prompts.get(commit_type, FEAT_PROMPT)
        return ChatPromptTemplate.from_messages(
            [("system", SYSTEM_PROMPT), ("human", template)]
        )
