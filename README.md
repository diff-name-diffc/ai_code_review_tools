# AI Code Reviewer

基于 LangChain 的 Git 代码评审工具。使用 AI 对代码提交进行智能评审，支持根据不同 commit 类型进行针对性分析。

## 功能特性

- **智能 commit 类型识别**: 自动解析 commit message 前缀（feat/fix/refactor/doc/config）
- **针对性评审**: 根据不同 commit 类型使用专门的评审策略和提示词
- **灵活配置**: 支持多种 LLM 提供商（OpenAI、Ollama、Azure OpenAI 等）
- **致命错误拦截**: 发现严重问题时阻止提交
- **基于 LangChain**: 使用最新的 LCEL 风格构建
- **自动初始化**: `init` 命令自动创建配置文件和 pre-commit hook 配置

## 安装

### 从源码安装

```bash
# 克隆项目
git clone https://github.com/your-username/ai-code-reviewer.git
cd ai-code-reviewer

# 安装依赖（推荐使用虚拟环境）
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate  # Windows

pip install -e .
```

### 依赖要求

- Python >= 3.10
- langchain >= 0.3.0
- langchain-openai >= 0.2.0
- pydantic >= 2.0.0
- click >= 8.0.0
- gitpython >= 3.0.0

## 快速开始

### 1. 初始化配置

```bash
ai-code-reviewer init
```

此命令会创建两个文件：

1. **`.ai-reviewer.toml`** - AI 评审器配置文件
2. **`.pre-commit-config.yaml`** - Pre-commit hook 配置文件（如果不存在）

### 2. 编辑配置文件

编辑 `.ai-reviewer.toml` 设置你的 LLM 配置：

```toml
[llm]
model = "qwen3-coder:30b"          # 模型名称
api_key = ""                       # API Key（Ollama 可留空）
base_url = "http://localhost:11434/v1"  # API Base URL

[reviewer]
enabled_types = ["feat", "fix", "refactor", "doc", "config"]
max_file_size = 100000             # 跳过超过此大小的文件（字节）
excluded_patterns = ["*.lock", "package-lock.json", "*.min.js"]
output_file = ".ai-review-log.json"  # 评审日志文件
```

**支持的 LLM 提供商**：

| 提供商 | base_url 示例 |
|--------|--------------|
| OpenAI | `null`（默认） |
| Ollama | `"http://localhost:11434/v1"` |
| Azure OpenAI | Azure 端点 URL |
| 其他兼容服务 | 相应的 API 端点 |

### 3. 安装 Pre-commit Hooks

```bash
# 安装 pre-commit（如果还没安装）
pip install pre-commit

# 安装 hooks
pre-commit install
```

### 4. 提交代码

现在正常提交代码即可触发 AI 评审：

```bash
git add .
git commit -m "feat: 添加用户认证功能"
```

## 命令说明

### `init` - 初始化配置

```bash
ai-code-reviewer init
```

创建配置文件和 pre-commit hook 配置。

### `review` - 执行评审

```bash
ai-code-reviewer review
```

手动执行代码评审，无需提交。

### `check` - 检查配置

```bash
ai-code-reviewer check
```

验证配置文件是否正确。

## Commit 类型说明

只有以下类型的 commit 会触发评审：

| 类型 | 说明 | 评审重点 |
|------|------|----------|
| `feat` | 新功能 | 功能完整性、逻辑正确性、边界条件、错误处理 |
| `fix` | 修复 bug | 修复是否正确、是否引入新问题、副作用 |
| `refactor` | 重构 | 是否保持原有功能、是否有意外变更、合理性 |
| `doc` | 文档变更 | 文档准确性、逻辑正确性、与代码一致性 |
| `config` | 配置变更 | 配置有效性、合理性、结合 commit 信息分析 |

其他类型（如 `style`、`test`、`chore`、`perf` 等）会**自动跳过评审**。

## 评审级别

- **critical (致命)**: 发现严重错误，**会拦截提交**
  - 安全漏洞
  - 严重逻辑错误
  - 破坏性变更
  - 明显的 bug

- **warning (警告)**: 仅显示，不拦截
  - 潜在性能问题
  - 代码异味
  - 不完整的实现

- **info (信息)**: 提示性建议

## Pre-commit Hook 配置

项目使用 `language: system` 方式配置 hook，确保使用正确的虚拟环境：

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: ai-code-reviewer
        name: AI Code Reviewer
        entry: .venv/bin/python -m ai_code_reviewer.cli review
        language: system
        pass_filenames: false
        always_run: true
```

**注意**：如果你的虚拟环境路径不是 `.venv`，请相应修改 `entry` 中的路径。

## 跳过评审

如果需要跳过 AI 评审（不推荐），可以使用：

```bash
git commit --no-verify -m "your message"
```

## 项目结构

```
ai_code_reviewer/
├── __init__.py              # 主包入口
├── cli.py                   # CLI 命令处理
├── config.py                # 配置文件加载
├── git_helper.py            # Git 操作封装（diff、commit message）
├── commit_parser.py         # Commit 类型解析器
├── models/                  # Pydantic 数据模型
│   ├── config.py            # LLM 和 Reviewer 配置模型
│   └── review_result.py     # 评审结果模型
├── prompts/                 # LangChain 提示词模板
│   └── templates.py         # 各类型的专门提示词
├── parsers/                 # LLM 输出解析器
│   └── review_parser.py     # JSON 结果解析
└── chains/                  # LangChain 评审链
    └── review_chain.py      # LCEL 风格的评审链
```

## 输出示例

```
============================================================
  AI 代码评审报告
============================================================
Commit 类型: feat
总体评估: APPROVE
============================================================
摘要: 本次提交实现了用户认证功能，包含登录、注册和密码重置...
============================================================
发现问题: 3 个
============================================================
1. [警告] 代码异味
   文件: auth/login.py
   行号: 45
   描述: 在 check_password 函数中，使用了字符串比较而不是恒定时间比较...
   建议: 使用 hmac.compare_digest 进行恒定时间比较

2. [信息] 代码结构
   文件: auth/models.py
   描述: User 类缺少 email 字段的唯一性约束
   建议: 添加 unique=True 到 email 字段

3. [警告] 潜在问题
   文件: auth/views.py
   行号: 78
   描述: 错误处理不完整，未记录登录失败日志
   建议: 添加日志记录以便审计

============================================================
[通过] 评审完成
```

## 常见问题

### Q: 如何使用 Ollama 本地模型？

A: 在 `.ai-reviewer.toml` 中配置：

```toml
[llm]
model = "qwen2.5-coder:latest"
api_key = ""  # 可留空
base_url = "http://localhost:11434/v1"
```

### Q: 为什么我的 commit 没有触发评审？

A: 检查以下几点：
1. Commit message 是否以支持的类型前缀开头（feat/fix/refactor/doc/config）
2. 是否有暂存的代码变更
3. 配置文件中 `enabled_types` 是否包含该类型

### Q: 如何禁用某个 commit 类型的评审？

A: 在 `.ai-reviewer.toml` 中修改 `enabled_types`：

```toml
[reviewer]
enabled_types = ["feat", "fix"]  # 只评审 feat 和 fix
```

### Q: 评审日志保存在哪里？

A: 日志保存在配置文件指定的 `output_file` 路径，默认为 `.ai-review-log.json`。

## 开发

### 运行测试

```bash
pytest
```

### 代码格式化

```bash
black ai_code_reviewer/
ruff check ai_code_reviewer/
```

## License

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！
