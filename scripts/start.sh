#!/bin/bash
set -e

# Newhorse 一键启动脚本
# 用法: curl -fsSL https://raw.githubusercontent.com/winghv/newhorse/master/scripts/start.sh | bash
# 或本地运行: bash scripts/start.sh

INSTALL_URL="https://raw.githubusercontent.com/winghv/newhorse/master"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
IS_REMOTE=false

# 检测是否远程执行
if [ "$SCRIPT_DIR" = "/tmp" ] || [ ! -d "$ROOT_DIR/.git" ]; then
    IS_REMOTE=true
    ROOT_DIR="$(mktemp -d)"
    echo "📦 克隆仓库到临时目录..."
    git clone --depth 1 https://github.com/winghv/newhorse "$ROOT_DIR" 2>/dev/null || {
        echo "❌ git clone 失败，请检查网络"
        exit 1
    }
fi

cd "$ROOT_DIR"

echo "🚀 Newhorse 启动中"
echo "================="

# 检查 Node.js
if ! command -v node &> /dev/null; then
    echo "❌ Node.js 未安装，请从 https://nodejs.org 下载安装"
    [ "$IS_REMOTE" = true ] && rm -rf "$ROOT_DIR"
    exit 1
fi

echo "✓ Node.js $(node -v) 和 npm $(npm -v) 已就绪"

# 安装依赖
if [ ! -d "node_modules" ]; then
    echo ""
    echo "📦 安装依赖..."
    npm install
fi

# 安装 API 依赖
if [ ! -d "apps/api/venv" ]; then
    echo ""
    echo "📦 设置 Python 虚拟环境..."
    node scripts/setup-venv.js
fi

# 设置环境变量
node scripts/setup-env.js

echo ""
echo "✅ 准备完成，启动中..."
echo ""

if [ "$IS_REMOTE" = true ]; then
    npm run dev
    rm -rf "$ROOT_DIR"
else
    npm run dev
fi
