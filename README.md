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

### 使用 pip 安装（推荐）

```bash
pip install pre-commit-ai-reviewer
```

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
2. **`.git/hooks/commit-msg`** - Git commit-msg hook（自动安装）

**重要提示**：
- ⚠️ 必须在 Git 仓库根目录下运行此命令
- ✅ 自动验证 Git 仓库有效性
- ✅ 检测并智能处理已存在的 hooks
- ✅ 多重安全检查防止误操作

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

### 3. 安装 Git Hooks

运行初始化命令会智能安装 `commit-msg` hook：

```bash
# init 命令会自动创建 .git/hooks/commit-msg
# 无需额外操作
```

**智能安装特性**：

- ✅ **自动检测**：如果 hook 已存在，会检查是否包含 AI 代码评审功能
- ✅ **交互式追加**：如果 hook 存在但未包含 AI 功能，会询问是否追加
- ✅ **安全验证**：自动检查符号链接、路径遍历等安全问题
- ✅ **幂等性**：多次运行不会重复安装

**处理已存在的 hook**：

如果你已经有其他 Git hooks（如 pre-commit、Husky 等），`init` 命令会：

1. 显示现有 hook 内容
2. 询问是否在现有内容后追加 AI 代码评审调用
3. 保留原有功能，不会破坏现有 hook

示例输出：

```
[警告] commit-msg hook 已存在: .git/hooks/commit-msg
现有内容：
#!/bin/sh
# Your existing hook content

是否在现有 hook 中追加 AI 代码评审功能？ [Y/n]:
```

### 4. 提交代码

现在正常提交代码即可触发 AI 评审：

```bash
git add .
git commit -m "feat: 添加用户认证功能"
```

**重要说明**：AI 评审会在你输入 commit message **之后**执行，可以正确读取你当前的提交消息。

## 命令说明

### `init` - 初始化配置

```bash
ai-code-reviewer init [选项]
```

**选项**：
- `-p, --path <路径>` - 指定配置文件保存路径
- `-f, --force` - 强制覆盖已存在的 commit-msg hook

**功能**：
创建以下文件：
- `.ai-reviewer.toml` - AI 评审配置文件
- `.git/hooks/commit-msg` - Git commit-msg hook（自动安装）

**示例**：

```bash
# 普通初始化（智能追加模式）
ai-code-reviewer init

# 强制覆盖已存在的 hook
ai-code-reviewer init --force

# 指定配置文件路径
ai-code-reviewer init --path /path/to/config.toml
```

**行为说明**：

1. **默认模式（无 --force）**：
   - 如果 hook 不存在，创建新文件
   - 如果 hook 已存在且包含 AI 功能，显示成功消息
   - 如果 hook 已存在但不包含 AI 功能，询问是否追加

2. **强制模式（--force）**：
   - 显示现有 hook 内容
   - 直接覆盖为 AI 代码评审 hook
   - ⚠️ 警告：会丢失原有 hook 内容

### `commit-msg-review` - 用于 commit-msg hook

```bash
ai-code-reviewer commit-msg-review <commit-msg-file>
```

此命令由 Git commit-msg hook 自动调用，**不需要手动执行**。它会在输入 commit message 后执行 AI 评审。

### `review` - 手动执行评审（可选）

```bash
ai-code-reviewer review
```

手动执行代码评审，用于测试或调试。注意：此命令可能无法获取到正确的 commit message。

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

## Git Hook 说明

本工具使用 **Git commit-msg hook** 而不是 pre-commit hook，这样可以：

1. ✅ **正确获取 commit message**：在用户输入 commit message 后执行
2. ✅ **更准确的评审**：可以结合 commit message 和代码变更进行评审
3. ✅ **支持强制提交**：通过 `-f` 标志跳过评审

### 自动安装

运行 `ai-code-reviewer init` 会自动创建 `.git/hooks/commit-msg` 文件。

### 手动安装（如果需要）

如果需要手动安装 hook，创建 `.git/hooks/commit-msg` 文件：

```bash
#!/bin/sh
# AI Code Reviewer - commit-msg hook

COMMIT_MSG_FILE="$1"
ai-code-reviewer commit-msg-review "$COMMIT_MSG_FILE"
```

然后设置可执行权限：

```bash
chmod +x .git/hooks/commit-msg
```

## 跳过评审

### 方式一：使用 -f 强制提交标志（推荐）

在提交消息的最后添加 `-f` 标志，可以跳过 AI 审查直接提交：

```bash
git commit -m "feat: 紧急修复生产问题 -f"
```

这种方式适合紧急情况或不需要 AI 审查的提交。

### 方式二：使用 --no-verify

如果需要跳过所有 pre-commit hooks（不推荐），可以使用：

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
