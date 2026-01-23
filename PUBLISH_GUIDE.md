# 📦 PyPI 发布指南

本项目的自动化发布脚本使用 **pipx** 在隔离环境中构建和上传包，确保 macOS 系统的安全性。

## 前置要求

### 1. 安装 pipx

```bash
# macOS
brew install pipx

# 确保 pipx PATH 已配置
pipx ensurepath
```

### 2. 配置 PyPI Token

#### 获取 API Token

- **PyPI 生产环境**: https://pypi.org/manage/account/token/
- **TestPyPI 测试环境**: https://test.pypi.org/manage/account/token/

#### 创建配置文件

```bash
# 方式1: 手动创建
cat > ~/.pypirc << 'EOF'
[pypi]
username = __token__
password = <你的PyPI_API_Token>

[testpypi]
username = __token__
password = <你的TestPyPI_API_Token>
EOF

# 方式2: 复制示例文件
cp .pypirc.example ~/.pypirc
# 然后编辑 ~/.pypirc 替换 Token

# 设置安全权限
chmod 600 ~/.pypirc
```

## 使用自动化脚本

### 基本命令

```bash
# 查看帮助
./publish.sh help

# 仅构建包（不上传）
./publish.sh build

# 仅检查包
./publish.sh check

# 清理构建文件
./publish.sh clean
```

### 发布到 TestPyPI（测试）

```bash
./publish.sh test
```

**测试安装**:
```bash
pip install --index-url https://test.pypi.org/simple/ ai-code-reviewer
```

### 发布到 PyPI（生产）

```bash
./publish.sh prod
```

**正式安装**:
```bash
pip install ai-code-reviewer
```

## 发布流程

脚本会自动执行以下步骤：

1. ✅ 检查 pipx 安装状态
2. ✅ 确保 build 和 twine 工具已安装（通过 pipx）
3. ✅ 清理旧的构建文件（`dist/` 目录）
4. ✅ 构建包（创建 `.tar.gz` 和 `.whl` 文件）
5. ✅ 检查包的完整性和元数据
6. ✅ 上传到指定的 PyPI 仓库

## 版本发布检查清单

在发布新版本前，请确保：

- [ ] 更新 `pyproject.toml` 中的版本号
- [ ] 更新 `README.md` 中的变更日志
- [ ] 在本地测试所有功能正常
- [ ] 先发布到 TestPyPI 测试
- [ ] 确认测试通过后再发布到 PyPI

## 工作原理

### pipx 隔离环境

```bash
# pipx 会为每个工具创建独立的虚拟环境
pipx install build    # 在 ~/.local/pipx/venvs/build 中安装
pipx install twine    # 在 ~/.local/pipx/venvs/twine 中安装

# pipx run 在隔离环境中执行命令
pipx run build        # 构建包
pipx run twine upload # 上传包
```

### 为什么使用 pipx？

- ✅ **安全性**: 不污染系统 Python 环境
- ✅ **隔离性**: 每个工具独立环境，避免依赖冲突
- ✅ **兼容性**: 符合 macOS 安全策略
- ✅ **可管理**: 易于安装、更新和卸载

## 常见问题

### Q: 如何更新构建工具？

```bash
pipx upgrade build
pipx upgrade twine
```

### Q: 如何卸载构建工具？

```bash
pipx uninstall build
pipx uninstall twine
```

### Q: 上传失败怎么办？

1. 检查网络连接
2. 验证 `~/.pypirc` 配置正确
3. 确认版本号没有被占用
4. 查看 PyPI 账户状态

### Q: 如何验证包已上传成功？

访问以下地址：
- PyPI: https://pypi.org/project/ai-code-reviewer/
- TestPyPI: https://test.pypi.org/project/ai-code-reviewer/

### Q: Token 失效了怎么办？

1. 访问 PyPI 管理页面重新生成 Token
2. 更新 `~/.pypirc` 文件中的 password 字段
3. 确保文件权限为 600: `chmod 600 ~/.pypirc`

## 安全建议

- 🔒 **永远不要**将 `~/.pypirc` 提交到 Git
- 🔒 **永远不要**在公开场合分享 API Token
- 🔒 Token 泄露后立即在 PyPI 撤销并重新生成
- 🔒 建议为项目创建独立范围的 Token

## 相关链接

- [PyPI 官方文档](https://packaging.python.org/tutorials/packaging-projects/)
- [pipx GitHub](https://github.com/pypa/pipx)
- [TestPyPI](https://test.pypi.org/)
