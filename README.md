# AI Code Reviewer

基于 LangChain 的 Git 代码评审工具。使用 AI 对代码提交进行智能评审，支持根据不同 commit 类型进行针对性分析。

## 功能特性

- **智能 commit 类型识别**: 自动解析 commit message 前缀（feat/fix/refactor/doc/config）
- **针对性评审**: 根据不同 commit 类型使用专门的评审策略
- **灵活配置**: 支持多种 LLM 提供商（OpenAI、Ollama 等）
- **致命错误拦截**: 发现严重问题时阻止提交
- **基于 LangChain**: 使用最新的 LCEL 风格构建

## 安装

```bash
pip install ai-code-reviewer
```

## 配置

### 1. 初始化配置

```bash
ai-code-reviewer init
```

这将在当前目录创建 `.ai-reviewer.toml` 配置文件：

```toml
[llm]
model = "gpt-4o"
api_key = "your-api-key-here"
base_url = null  # 例如: "http://localhost:11434/v1" for ollama

[reviewer]
enabled_types = ["feat", "fix", "refactor", "doc", "config"]
max_file_size = 100000
excluded_patterns = ["*.lock", "package-lock.json", "*.min.js"]
output_file = null  # 可选: ".ai-review-log.json"
```

### 2. 编辑配置

设置你的 API Key 和其他选项。支持兼容 OpenAI API 格式的服务，如：

- OpenAI
- Azure OpenAI
- Ollama (`base_url = "http://localhost:11434/v1"`)

## 使用

### 作为 pre-commit hook

1. 在项目根目录创建 `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: local
    hooks:
      - id: ai-code-reviewer
        name: AI Code Reviewer
        entry: ai-code-reviewer review
        language: python
        pass_filenames: false
        always_run: true
```

2. 安装 hook:

```bash
pre-commit install
```

3. 正常提交代码即可触发评审:

```bash
git commit -m "feat: 添加新功能"
```

### 手动运行

```bash
ai-code-reviewer review
```

### 检查配置

```bash
ai-code-reviewer check
```

## Commit 类型说明

只有以下类型的 commit 会触发评审：

| 类型 | 说明 | 评审重点 |
|------|------|----------|
| `feat` | 新功能 | 功能完整性、逻辑正确性、边界条件处理 |
| `fix` | 修复 bug | 修复是否正确、是否引入新问题 |
| `refactor` | 重构 | 是否保持原有功能、是否有意外变更 |
| `doc` | 文档变更 | 文档准确性、逻辑正确性 |
| `config` | 配置变更 | 配置有效性、合理性 |

其他类型（如 `style`、`test`、`chore` 等）会跳过评审。

## 评审级别

- **critical (致命)**: 发现严重错误，会拦截提交
  - 安全漏洞
  - 严重逻辑错误
  - 破坏性变更
  - 明显的 bug

- **warning (警告)**: 仅显示，不拦截
  - 潜在性能问题
  - 代码异味
  - 不完整的实现

- **info (信息)**: 提示性建议

## 强制提交

如果需要跳过评审（不推荐），可以使用：

```bash
git commit --no-verify -m "your message"
```

## 项目结构

```
ai_code_reviewer/
├── cli.py              # CLI 入口
├── config.py           # 配置加载
├── git_helper.py       # Git 操作封装
├── commit_parser.py    # Commit 类型解析
├── models/             # 数据模型
├── prompts/            # 提示词模板
├── parsers/            # 输出解析器
└── chains/             # LangChain 评审链
```

## 依赖

- Python >= 3.10
- langchain >= 0.3.0
- langchain-openai >= 0.2.0
- pydantic >= 2.0.0
- pre-commit >= 3.0.0
