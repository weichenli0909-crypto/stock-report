@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

REM ============================================
REM 📊 股票报告 - Windows 一键启动
REM 双击：更新数据 + 启动服务器 + 打开浏览器
REM ============================================

REM 切换到脚本所在目录（自动识别当前位置）
cd /d "%~dp0"

cls
echo =====================================================
echo.
echo     📊  股票报告 - 一键启动（Windows 版）
echo.
echo =====================================================
echo.
echo 📁 项目位置：%cd%
echo.

REM 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 未检测到 Python
    echo.
    echo 💡 请先双击「一键安装-Windows.bat」完成环境配置
    echo.
    pause
    exit /b 1
)

REM 检查关键依赖
python -c "import akshare, pandas, matplotlib" >nul 2>&1
if errorlevel 1 (
    echo ❌ Python 依赖库未安装完整
    echo.
    echo 💡 请先双击「一键安装-Windows.bat」完成环境配置
    echo.
    pause
    exit /b 1
)

REM 询问是否更新数据
echo 是否要先更新最新股票数据？
echo    1) ✅ 是（采集最新数据+生成报告，约 1-2 分钟）
echo    2) ⏭️  否（直接打开上次的报告）
echo.
set /p CHOICE=请输入 1 或 2（默认 1）:
if "!CHOICE!"=="" set CHOICE=1

if "!CHOICE!"=="1" (
    echo.
    echo -----------------------------------------------------
    echo ⏳ 正在更新数据并生成报告...
    echo -----------------------------------------------------
    echo.
    python run_workflow.py
    echo.
)

REM 关闭占用 8899 端口的旧进程
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8899 ^| findstr LISTENING') do (
    echo 🔁 检测到 8899 端口被占用，关闭旧进程 %%a ...
    taskkill /PID %%a /F >nul 2>&1
)

REM 启动 Web 服务器
echo.
echo 🚀 正在启动 Web 服务器...

if exist "web_server.py" (
    start "股票报告服务器" /min cmd /c "python web_server.py"
    timeout /t 3 /nobreak >nul
    echo    ✅ 服务器已启动
    echo.
    echo 📱 报告访问地址：
    echo    🖥️  本机访问：http://localhost:8899
    echo.
    echo 💡 功能说明：
    echo    • 浏览器里可以点「⚡ 快速刷新」获取最新行情
    echo    • 点「🔄 完整刷新」重新采集全部数据
    echo    • 右上角可切换「☀️ 亮色 / 🌙 暗色」主题
    echo.
    REM 自动打开浏览器
    start http://localhost:8899
) else (
    REM 没有 web_server.py 就直接打开 report.html
    if exist "output\report.html" (
        start "" "output\report.html"
    ) else (
        start "" "report.html"
    )
)

echo -----------------------------------------------------
echo.
echo ✅ 全部完成！浏览器应该已自动打开报告
echo.
echo ⚠️  关闭此窗口会停止服务器，请在使用完后再关闭
echo.
echo -----------------------------------------------------
echo.
pause
