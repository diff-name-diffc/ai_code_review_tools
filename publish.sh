#!/bin/bash
# PyPI 包自动化发布脚本
# 使用 pipx 在隔离环境中构建和上传包

set -e  # 遇到错误立即退出

# 颜色定义 - 使用 tput 以获得更好的兼容性
if [[ -t 1 ]] && command -v tput &> /dev/null; then
    # 终端支持颜色
    RED=$(tput setaf 1)
    GREEN=$(tput setaf 2)
    YELLOW=$(tput setaf 3)
    BLUE=$(tput setaf 4)
    BOLD=$(tput bold)
    NC=$(tput sgr0)
else
    # 降级到无颜色模式
    RED=""
    GREEN=""
    YELLOW=""
    BLUE=""
    BOLD=""
    NC=""
fi

# 打印带颜色的消息
print_info() {
    printf "${BLUE}ℹ${NC} %s\n" "$1"
}

print_success() {
    printf "${GREEN}✓${NC} %s\n" "$1"
}

print_warning() {
    printf "${YELLOW}⚠${NC} %s\n" "$1"
}

print_error() {
    printf "${RED}✗${NC} %s\n" "$1"
}

# 检查 pipx 是否安装
check_pipx() {
    print_info "检查 pipx 安装状态..."
    if ! command -v pipx &> /dev/null; then
        print_error "pipx 未安装"
        print_info "请先安装 pipx: brew install pipx"
        exit 1
    fi
    print_success "pipx 已安装"
}

# 确保 build 和 twine 已通过 pipx 安装
ensure_tools() {
    print_info "确保构建工具已安装..."

    # 检查并安装 build
    if ! pipx list | grep -q "build"; then
        print_info "正在安装 build..."
        pipx install build
    else
        print_success "build 已安装"
    fi

    # 检查并安装 twine
    if ! pipx list | grep -q "twine"; then
        print_info "正在安装 twine..."
        pipx install twine
    else
        print_success "twine 已安装"
    fi
}

# 清理旧的构建文件
clean_dist() {
    print_info "清理旧的构建文件..."
    if [ -d "dist" ]; then
        rm -rf dist
        print_success "已清理 dist 目录"
    fi
}

# 构建包
build_package() {
    print_info "开始构建包..."
    pipx run build --outdir dist
    print_success "包构建完成"

    # 显示构建的文件
    print_info "构建的文件:"
    ls -lh dist/
}

# 检查包
check_package() {
    print_info "检查包的完整性..."
    pipx run twine check dist/*
    print_success "包检查通过"
}

# 检查 ~/.pypirc 配置
check_pypirc() {
    print_info "检查 PyPI 配置..."

    if [ ! -f ~/.pypirc ]; then
        print_error "~/.pypirc 文件不存在"
        printf "\n"
        echo "请创建 ~/.pypirc 文件，内容如下："
        echo "-----------------------------------"
        cat << 'EOF'
[pypi]
username = __token__
password = <你的PyPI_API_Token>

[testpypi]
username = __token__
password = <你的TestPyPI_API_Token>
EOF
        echo "-----------------------------------"
        printf "\n"
        echo "创建命令："
        echo "  cat > ~/.pypirc << 'EOF'"
        echo "  [pypi]"
        echo "  username = __token__"
        echo "  password = <你的PyPI_API_Token>"
        echo "  "
        echo "  [testpypi]"
        echo "  username = __token__"
        echo "  password = <你的TestPyPI_API_Token>"
        echo "  EOF"
        printf "\n"
        echo "设置安全权限："
        echo "  chmod 600 ~/.pypirc"
        printf "\n"
        exit 1
    fi

    # 检查文件权限
    if [ $(stat -f %Lp ~/.pypirc) != "600" ]; then
        print_warning "~/.pypirc 权限不安全，正在修复..."
        chmod 600 ~/.pypirc
    fi

    print_success "~/.pypirc 配置存在"
}

# 上传到 TestPyPI
upload_test() {
    print_info "上传到 TestPyPI..."
    pipx run twine upload --repository testpypi dist/*
    print_success "上传到 TestPyPI 完成"
    print_info "测试安装命令:"
    echo "  pip install --index-url https://test.pypi.org/simple/ pre-commit-ai-reviewer"
}

# 上传到 PyPI
upload_pypi() {
    print_info "上传到 PyPI..."
    pipx run twine upload dist/*
    print_success "上传到 PyPI 完成"
    print_info "安装命令:"
    echo "  pip install pre-commit-ai-reviewer"
}

# 显示帮助信息
show_help() {
    printf "${BLUE}========================================${NC}\n"
    printf "${BLUE}    PyPI 包发布工具${NC}\n"
    printf "${BLUE}========================================${NC}\n"
    printf "\n"
    printf "用法: $0 [选项]\n"
    printf "\n"
    printf "选项:\n"
    printf "    ${GREEN}test${NC}       构建并上传到 TestPyPI（测试环境）\n"
    printf "    ${GREEN}prod${NC}       构建并上传到 PyPI（生产环境）\n"
    printf "    ${GREEN}build${NC}      仅构建包，不上传\n"
    printf "    ${GREEN}check${NC}      仅检查构建的包\n"
    printf "    ${GREEN}clean${NC}      清理构建文件\n"
    printf "    ${GREEN}help${NC}       显示此帮助信息\n"
    printf "\n"
    printf "示例:\n"
    printf "    $0 test        # 测试发布\n"
    printf "    $0 prod        # 正式发布\n"
    printf "    $0 build       # 仅构建\n"
    printf "\n"
    printf "环境要求:\n"
    printf "    - pipx (通过 brew install pipx 安装)\n"
    printf "    - ~/.pypirc 配置文件\n"
    printf "\n"
}

# 主函数
main() {
    printf "${BLUE}========================================${NC}\n"
    printf "${BLUE}    PyPI 包自动化发布工具${NC}\n"
    printf "${BLUE}========================================${NC}\n"
    printf "\n"

    # 检查环境
    check_pipx
    ensure_tools

    # 根据参数执行操作
    case "${1:-help}" in
        test)
            check_pypirc
            clean_dist
            build_package
            check_package
            printf "\n"
            print_warning "准备上传到 TestPyPI..."
            read -p "确认继续？  " -n 1 -r
            printf "\n"
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                upload_test
            else
                print_info "已取消上传"
            fi
            ;;
        prod)
            check_pypirc
            clean_dist
            build_package
            check_package
            printf "\n"
            print_warning "准备上传到 PyPI（生产环境）..."
            print_warning "版本号: $(grep 'version =' pyproject.toml | head -1 | sed 's/.*= "\(.*\)".*/\1/')"
            read -p "确认继续？  " -n 1 -r
            printf "\n"
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                upload_pypi
            else
                print_info "已取消上传"
            fi
            ;;
        build)
            clean_dist
            build_package
            ;;
        check)
            check_package
            ;;
        clean)
            clean_dist
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            print_error "未知选项: $1"
            printf "\n"
            show_help
            exit 1
            ;;
    esac

    printf "\n"
    print_success "完成！"
}

# 执行主函数
main "$@"
