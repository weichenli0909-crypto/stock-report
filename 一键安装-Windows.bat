@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

REM ============================================
REM 📊 股票报告 - Windows 一键安装脚本
REM 双击此文件即可自动安装
REM ============================================

REM 切换到脚本所在目录（自动识别，不依赖固定路径）
cd /d "%~dp0"

cls
echo =====================================================
echo.
echo     📊  股票报告 - 一键安装（Windows 版）
echo.
echo =====================================================
echo.
echo ⏳ 本脚本将自动安装：
echo    • Python 3（如未安装，会打开下载页面）
echo    • Python 依赖库（akshare, pandas 等）
echo.
echo 💾 需要约 500MB 磁盘空间
echo.
echo 📁 项目位置：%cd%
echo.
pause
echo.

REM ========== 1. 检查 Python ==========
echo -----------------------------------------------------
echo 📦 [1/2] 检查 Python 3...
python --version >nul 2>&1
if errorlevel 1 (
    echo    ❌ 未检测到 Python
    echo.
    echo    将为您打开 Python 官网下载页面
    echo.
    echo    ⚠️⚠️⚠️ 重要：安装时务必勾选底部的
    echo         「Add Python to PATH」
    echo         ^(把 Python 添加到系统路径^)
    echo.
    echo    安装完成后，请重新双击本脚本
    echo.
    pause
    start https://www.python.org/downloads/
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PY_VER=%%i
echo    ✅ Python !PY_VER! 已安装
echo.

REM ========== 2. 安装 Python 依赖 ==========
echo -----------------------------------------------------
echo 📦 [2/2] 安装 Python 依赖库...
echo    （可能需要 2-3 分钟，请耐心等待）
echo.

set PIP_MIRROR=https://pypi.tuna.tsinghua.edu.cn/simple

if exist "requirements.txt" (
    python -m pip install --upgrade -r requirements.txt -i %PIP_MIRROR%
) else (
    python -m pip install --upgrade akshare pandas matplotlib numpy scikit-learn yfinance requests beautifulsoup4 lxml -i %PIP_MIRROR%
)

echo.
echo    ✅ 依赖库安装完成
echo.

REM ========== 验证安装 ==========
echo -----------------------------------------------------
echo 🔍 验证安装...
echo.

set ALL_OK=1
for %%P in (akshare pandas matplotlib numpy sklearn) do (
    python -c "import %%P" >nul 2>&1
    if errorlevel 1 (
        echo    ❌ %%P  ^(未安装^)
        set ALL_OK=0
    ) else (
        echo    ✅ %%P
    )
)

echo.
echo -----------------------------------------------------
if "!ALL_OK!"=="1" (
    echo.
    echo    🎉 安装完成！
    echo.
    echo 📖 下一步：
    echo    1️⃣  双击「启动股票报告-Windows.bat」运行
    echo    2️⃣  浏览器会自动打开：http://localhost:8899
    echo    3️⃣  以后每次使用只需双击启动脚本即可
    echo.
) else (
    echo.
    echo    ⚠️  部分依赖安装失败
    echo.
    echo 💡 尝试手动安装：
    echo    python -m pip install akshare pandas matplotlib numpy scikit-learn
    echo.
)

echo -----------------------------------------------------
echo.
pause
