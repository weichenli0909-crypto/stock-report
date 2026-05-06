#!/bin/bash
# ============================================
# 📊 股票报告 - Mac 一键启动脚本
# 双击此文件：自动更新数据 + 启动服务器 + 打开浏览器
# ============================================

# 关键：切换到脚本所在目录（自动识别当前位置）
cd "$(dirname "$0")"

clear
echo "╔══════════════════════════════════════════════════╗"
echo "║                                                  ║"
echo "║   📊  股票报告 - 一键启动（Mac 版）              ║"
echo "║                                                  ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""
echo "📁 项目位置：$(pwd)"
echo ""

# 检查 Python 是否安装
if ! command -v python3 &>/dev/null; then
    echo "❌ 未检测到 Python 3"
    echo ""
    echo "💡 请先双击「一键安装-Mac.command」完成环境配置"
    echo ""
    read -p "按 Enter 关闭..."
    exit 1
fi

# 检查关键依赖
if ! python3 -c "import akshare, pandas, matplotlib" 2>/dev/null; then
    echo "❌ Python 依赖库未安装完整"
    echo ""
    echo "💡 请先双击「一键安装-Mac.command」完成环境配置"
    echo ""
    read -p "按 Enter 关闭..."
    exit 1
fi

# 询问是否更新数据
echo "是否要先更新最新股票数据？"
echo "   1) ✅ 是（采集最新数据+生成报告，约 1-2 分钟）"
echo "   2) ⏭️  否（直接打开上次的报告）"
echo ""
read -p "请输入 1 或 2（默认 1）: " CHOICE
CHOICE=${CHOICE:-1}

if [ "$CHOICE" = "1" ]; then
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "⏳ 正在更新数据并生成报告..."
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    python3 run_workflow.py
    echo ""
fi

# 检查报告文件是否存在
if [ ! -f "output/report.html" ] && [ ! -f "report.html" ]; then
    echo "⚠️  暂无报告，请先选择 1 生成数据"
    read -p "按 Enter 关闭..."
    exit 1
fi

# 停掉已有的 web_server（避免端口冲突）
PID=$(lsof -ti :8899 2>/dev/null)
if [ -n "$PID" ]; then
    echo "🔁 检测到 8899 端口已被占用，关闭旧进程..."
    kill -9 $PID 2>/dev/null
    sleep 1
fi

# 启动 Web 服务器（后台）
echo ""
echo "🚀 正在启动 Web 服务器..."
if [ -f "web_server.py" ]; then
    nohup python3 web_server.py > /tmp/stock_web_server.log 2>&1 &
    SERVER_PID=$!
    sleep 2
    echo "   ✅ 服务器已启动（进程号 $SERVER_PID）"
    echo ""
    echo "📱 报告访问地址："
    echo "   🖥️  本机访问：http://localhost:8899"
    echo ""
    # 显示局域网IP，方便手机访问
    LAN_IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null)
    if [ -n "$LAN_IP" ]; then
        echo "   📱 手机访问：http://$LAN_IP:8899（需要同一WiFi）"
    fi
    echo ""
    echo "💡 功能说明："
    echo "   • 浏览器里可以点「⚡ 快速刷新」获取最新行情"
    echo "   • 点「🔄 完整刷新」重新采集全部数据"
    echo "   • 右上角可切换「☀️ 亮色 / 🌙 暗色」主题"
    echo ""
    # 自动打开浏览器
    sleep 1
    open "http://localhost:8899"
else
    # 没有 web_server.py 就直接打开 report.html
    if [ -f "output/report.html" ]; then
        open "output/report.html"
    else
        open "report.html"
    fi
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "✅ 全部完成！浏览器应该已自动打开报告"
echo ""
echo "⚠️  关闭此窗口会停止服务器，请在使用完后再关闭"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
read -p "按 Enter 停止服务器并关闭..."

# 清理：关闭服务器
if [ -n "$SERVER_PID" ]; then
    kill $SERVER_PID 2>/dev/null
    echo "🛑 服务器已关闭"
fi
