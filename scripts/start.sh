#!/bin/bash
set -e

# Newhorse 一键启动脚本
# 用法: curl -fsSL https://raw.githubusercontent.com/winghv/newhorse/master/scripts/start.sh | bash
# 或本地运行: bash scripts/start.sh

# 检测是否远程执行：piped curl|bash 时 stdin 不是终端
if [ ! -t 0 ]; then
    ROOT_DIR="$(mktemp -d)"
    echo "📦 克隆仓库到临时目录..."
    git clone --depth 1 https://github.com/winghv/newhorse "$ROOT_DIR" 2>/dev/null || {
        echo "❌ git clone 失败，请检查网络"
        exit 1
    }
    (
        cd "$ROOT_DIR"
        echo "📦 安装依赖..."
        npm install
        npm run dev
    )
    rm -rf "$ROOT_DIR"
else
    cd "$(dirname "$0")/.."
    npm run dev
fi
