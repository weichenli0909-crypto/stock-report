#!/bin/bash
# ============================================
# 📊 股票报告 - Mac 一键安装脚本
# 双击此文件即可自动安装所有依赖
# 不依赖特定电脑，任何 Mac 都可用
# ============================================

# 关键：切换到脚本所在目录（自动识别，任何位置都能运行）
cd "$(dirname "$0")"

clear
echo "╔══════════════════════════════════════════════════╗"
echo "║                                                  ║"
echo "║   📊  股票报告 - 一键安装（Mac 版）              ║"
echo "║                                                  ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""
echo "⏳ 本脚本将自动安装："
echo "   • Homebrew（Mac 包管理器）"
echo "   • Python 3（编程语言）"
echo "   • Python 依赖库（akshare, pandas 等）"
echo ""
echo "💾 需要约 500MB 磁盘空间，首次安装约 3-5 分钟"
echo ""
echo "📁 项目位置：$(pwd)"
echo ""
read -p "👉 按 Enter 开始安装（Ctrl+C 取消）..."
echo ""

# ========== 1. 检查/安装 Homebrew ==========
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📦 [1/3] 检查 Homebrew..."
if command -v brew &>/dev/null; then
    echo "   ✅ Homebrew 已安装"
else
    echo "   正在安装 Homebrew（macOS 包管理器）..."
    echo "   ⚠️  可能需要你输入 Mac 密码（输入时不会显示，直接输完回车）"
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

    # Apple Silicon 需要加到 PATH
    if [ -f /opt/homebrew/bin/brew ]; then
        eval "$(/opt/homebrew/bin/brew shellenv)"
        echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
    elif [ -f /usr/local/bin/brew ]; then
        eval "$(/usr/local/bin/brew shellenv)"
    fi

    if command -v brew &>/dev/null; then
        echo "   ✅ Homebrew 安装完成"
    else
        echo "   ❌ Homebrew 安装失败，请查看上方错误信息"
        echo ""
        read -p "按任意键退出..."
        exit 1
    fi
fi
echo ""

# ========== 2. 检查/安装 Python 3 ==========
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📦 [2/3] 检查 Python 3..."
if command -v python3 &>/dev/null; then
    PY_VER=$(python3 --version 2>&1 | awk '{print $2}')
    echo "   ✅ Python $PY_VER 已安装"
else
    echo "   正在安装 Python 3.11..."
    brew install python@3.11
    if command -v python3 &>/dev/null; then
        echo "   ✅ Python 安装完成"
    else
        echo "   ❌ Python 安装失败"
        read -p "按任意键退出..."
        exit 1
    fi
fi
echo ""

# ========== 3. 安装 Python 依赖库 ==========
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📦 [3/3] 安装 Python 依赖库..."
echo "   （可能需要 2-3 分钟，请耐心等待）"
echo ""

# 使用国内镜像加速
PIP_MIRROR="https://pypi.tuna.tsinghua.edu.cn/simple"

if [ -f "requirements.txt" ]; then
    python3 -m pip install --upgrade -r requirements.txt -i $PIP_MIRROR 2>&1 | tail -5
else
    python3 -m pip install --upgrade akshare pandas matplotlib numpy scikit-learn yfinance requests beautifulsoup4 lxml -i $PIP_MIRROR 2>&1 | tail -5
fi

echo ""
echo "   ✅ 依赖库安装完成"
echo ""

# ========== 验证安装 ==========
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔍 验证安装..."
echo ""

ALL_OK=true
for pkg in akshare pandas matplotlib numpy sklearn; do
    if python3 -c "import $pkg" 2>/dev/null; then
        echo "   ✅ $pkg"
    else
        echo "   ❌ $pkg （未安装）"
        ALL_OK=false
    fi
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ "$ALL_OK" = true ]; then
    echo ""
    echo "   🎉 安装完成！"
    echo ""
    echo "📖 下一步："
    echo "   1️⃣  双击「启动股票报告-Mac.command」运行"
    echo "   2️⃣  浏览器会自动打开：http://localhost:8899"
    echo "   3️⃣  以后每次使用只需双击启动脚本即可"
    echo ""
else
    echo ""
    echo "   ⚠️  部分依赖安装失败，请检查上方错误"
    echo ""
    echo "💡 尝试手动安装："
    echo "   python3 -m pip install akshare pandas matplotlib numpy scikit-learn"
    echo ""
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
read -p "按 Enter 关闭此窗口..."
