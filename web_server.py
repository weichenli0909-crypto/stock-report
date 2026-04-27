"""
🌐 Web 服务器 - 让报告可以通过网络分享给其他人
支持：局域网访问 + 一键刷新数据 + ngrok 公网分享
"""

import os
import sys
import json
import socket
import subprocess
import threading
import time
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler
from functools import partial
from urllib.parse import urlparse, parse_qs

# 报告输出目录
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output")

sys.path.insert(0, SCRIPT_DIR)

# 默认端口
DEFAULT_PORT = 8899

# 全局刷新状态
refresh_status = {
    "running": False,
    "last_refresh": None,
    "last_result": None,
    "progress": "",
    "step": 0,
    "total_steps": 3,
}


class ReportHandler(SimpleHTTPRequestHandler):
    """自定义请求处理器 — 支持静态文件 + API"""

    def __init__(self, *args, directory=None, **kwargs):
        super().__init__(*args, directory=directory, **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        # API 路由
        if path == "/api/refresh":
            self.handle_refresh()
        elif path == "/api/status":
            self.handle_status()
        elif path == "/api/quick-refresh":
            self.handle_quick_refresh()
        elif path == "/api/quotes":
            self.handle_quotes()
        else:
            # 根路径自动重定向到 report.html
            if path == "/" or path == "":
                self.path = "/report.html"
            return super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/refresh":
            self.handle_refresh()
        elif parsed.path == "/api/quick-refresh":
            self.handle_quick_refresh()
        else:
            self.send_error(404)

    def handle_refresh(self):
        """完整刷新：行情采集 + 舆情 + 美股 + 分析 + 预测 + 报告"""
        global refresh_status
        if refresh_status["running"]:
            self.send_json({"status": "busy", "message": "正在刷新中，请稍候..."})
            return

        # 启动后台线程执行刷新
        thread = threading.Thread(target=self._run_full_refresh, daemon=True)
        thread.start()
        self.send_json({"status": "started", "message": "开始完整刷新（约60秒）..."})

    def handle_quick_refresh(self):
        """快速刷新：行情采集 + 分析 + 报告（跳过舆情/美股/预测）"""
        global refresh_status
        if refresh_status["running"]:
            self.send_json({"status": "busy", "message": "正在刷新中，请稍候..."})
            return

        thread = threading.Thread(target=self._run_quick_refresh, daemon=True)
        thread.start()
        self.send_json({"status": "started", "message": "开始快速刷新（约20秒）..."})

    def handle_status(self):
        """返回刷新状态"""
        self.send_json(refresh_status)

    def handle_quotes(self):
        """直接拉取新浪实时行情，返回JSON（供前端轮询）"""
        try:
            from config import get_all_stocks

            all_stocks = get_all_stocks()
            sina_codes = ",".join(
                f"sh{c}" if c.startswith(("6", "9")) else f"sz{c}"
                for c in all_stocks.keys()
            )
            url = f"https://hq.sinajs.cn/list={sina_codes}"

            result = subprocess.run(
                [
                    "curl", "-s", "-m", "15",
                    "-H", "Referer: https://finance.sina.com.cn",
                    "-H", "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
                    url,
                ],
                capture_output=True, timeout=20
            )
            if result.returncode != 0 or not result.stdout:
                self.send_json({"error": "无法获取行情数据"})
                return

            text = result.stdout.decode("gbk", errors="replace")

            quotes = {}
            for line in text.strip().split("\n"):
                line = line.strip()
                if not line or '="' not in line:
                    continue
                try:
                    var_part = line.split("=")[0]
                    code_part = var_part.replace("var hq_str_", "").strip()
                    code6 = code_part[2:]

                    data_str = line.split('"')[1]
                    if not data_str:
                        continue
                    fields = data_str.split(",")
                    if len(fields) < 32:
                        continue

                    name = fields[0]
                    if not name or any(ord(c) > 0xFFFF for c in name):
                        name = all_stocks.get(code6, code6)

                    price = float(fields[3]) if fields[3] else 0
                    prev_close = float(fields[2]) if fields[2] else 0
                    change_pct = round((price - prev_close) / prev_close * 100, 2) if prev_close > 0 else 0

                    quotes[code6] = {
                        "name": name,
                        "price": price,
                        "open": float(fields[1]) if fields[1] else 0,
                        "prev_close": prev_close,
                        "high": float(fields[4]) if fields[4] else 0,
                        "low": float(fields[5]) if fields[5] else 0,
                        "volume": int(fields[8]) if fields[8] else 0,
                        "amount": float(fields[9]) if fields[9] else 0,
                        "change_pct": change_pct,
                    }
                except Exception:
                    continue

            self.send_json({
                "time": datetime.now().strftime("%H:%M:%S"),
                "count": len(quotes),
                "quotes": quotes,
            })
        except Exception as e:
            self.send_json({"error": str(e)})

    def _run_full_refresh(self):
        """后台执行完整刷新"""
        global refresh_status
        refresh_status["running"] = True
        refresh_status["step"] = 0
        refresh_status["total_steps"] = 6
        refresh_status["last_result"] = None
        start = time.time()

        try:
            # Step 1
            refresh_status["progress"] = "📥 采集行情数据..."
            refresh_status["step"] = 1
            print(f"\n  🔄 [API] Step 1/6 行情采集...")
            from step1_collect import run_collection
            run_collection()

            # Step 2
            refresh_status["progress"] = "📰 采集舆情新闻..."
            refresh_status["step"] = 2
            print(f"  🔄 [API] Step 2/6 舆情采集...")
            try:
                from step1b_news import run_news_collection
                run_news_collection()
            except Exception:
                pass

            # Step 3
            refresh_status["progress"] = "🇺🇸 采集美股数据..."
            refresh_status["step"] = 3
            print(f"  🔄 [API] Step 3/6 美股采集...")
            try:
                from step1c_us_stocks import run_us_stock_collection
                run_us_stock_collection()
            except Exception:
                pass

            # Step 4
            refresh_status["progress"] = "🔍 数据分析..."
            refresh_status["step"] = 4
            print(f"  🔄 [API] Step 4/6 数据分析...")
            from step2_analyze import run_analysis
            run_analysis()

            # Step 5
            refresh_status["progress"] = "🤖 ML预测..."
            refresh_status["step"] = 5
            print(f"  🔄 [API] Step 5/6 ML预测...")
            try:
                from step2b_predict import run_prediction
                run_prediction()
            except Exception:
                pass

            # Step 6
            refresh_status["progress"] = "📊 生成报告..."
            refresh_status["step"] = 6
            print(f"  🔄 [API] Step 6/6 生成报告...")
            from step3_report import run_report
            run_report()

            elapsed = time.time() - start
            refresh_status["last_result"] = "success"
            refresh_status["last_refresh"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            refresh_status["progress"] = f"✅ 完整刷新完成！耗时 {elapsed:.0f}秒"
            print(f"  ✅ [API] 完整刷新完成，耗时 {elapsed:.1f}秒")

        except Exception as e:
            refresh_status["last_result"] = f"error: {str(e)}"
            refresh_status["progress"] = f"❌ 刷新出错: {str(e)}"
            print(f"  ❌ [API] 刷新出错: {e}")

        finally:
            refresh_status["running"] = False

    def _run_quick_refresh(self):
        """后台执行快速刷新"""
        global refresh_status
        refresh_status["running"] = True
        refresh_status["step"] = 0
        refresh_status["total_steps"] = 3
        refresh_status["last_result"] = None
        start = time.time()

        try:
            # Step 1
            refresh_status["progress"] = "📥 采集行情数据..."
            refresh_status["step"] = 1
            print(f"\n  ⚡ [API] Step 1/3 行情采集...")
            from step1_collect import run_collection
            run_collection()

            # Step 2
            refresh_status["progress"] = "🔍 数据分析..."
            refresh_status["step"] = 2
            print(f"  ⚡ [API] Step 2/3 数据分析...")
            from step2_analyze import run_analysis
            run_analysis()

            # Step 3
            refresh_status["progress"] = "📊 生成报告..."
            refresh_status["step"] = 3
            print(f"  ⚡ [API] Step 3/3 生成报告...")
            from step3_report import run_report
            run_report()

            elapsed = time.time() - start
            refresh_status["last_result"] = "success"
            refresh_status["last_refresh"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            refresh_status["progress"] = f"✅ 快速刷新完成！耗时 {elapsed:.0f}秒"
            print(f"  ✅ [API] 快速刷新完成，耗时 {elapsed:.1f}秒")

        except Exception as e:
            refresh_status["last_result"] = f"error: {str(e)}"
            refresh_status["progress"] = f"❌ 刷新出错: {str(e)}"
            print(f"  ❌ [API] 刷新出错: {e}")

        finally:
            refresh_status["running"] = False

    def send_json(self, data):
        """发送 JSON 响应"""
        response = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def log_message(self, format, *args):
        msg = format % args
        if "200" in msg and "/api/" not in self.path:
            print(f"  ✅ {self.address_string()} 访问了报告")
        elif "404" in msg:
            print(f"  ⚠️ {self.address_string()} 请求了不存在的文件: {self.path}")

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        super().end_headers()


def get_local_ip():
    """获取本机局域网 IP"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def run_server(port=DEFAULT_PORT):
    """启动 Web 服务器"""

    report_path = os.path.join(OUTPUT_DIR, "report.html")
    if not os.path.exists(report_path):
        print("❌ 未找到报告文件！请先运行工作流生成报告：")
        print("   python3 run_workflow.py")
        return

    local_ip = get_local_ip()

    print()
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║                                                              ║")
    print("║   🌐  AI/光通信板块日报 - Web 分享服务器 v2.0                 ║")
    print("║                                                              ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()

    handler = partial(ReportHandler, directory=OUTPUT_DIR)
    server = HTTPServer(("0.0.0.0", port), handler)

    print(f"  ✅ 服务器已启动！端口: {port}")
    print()
    print("  📱 分享链接：")
    print("  ─────────────────────────────────────────")
    print(f"  🏠 本机访问:   http://localhost:{port}")
    print(f"  📶 局域网访问: http://{local_ip}:{port}")
    print()
    print("  🔄 刷新 API：")
    print("  ─────────────────────────────────────────")
    print(f"  ⚡ 快速刷新: http://localhost:{port}/api/quick-refresh")
    print(f"  🔄 完整刷新: http://localhost:{port}/api/refresh")
    print(f"  📊 查看状态: http://localhost:{port}/api/status")
    print()
    print("  💡 报告页面右上角有「刷新数据」按钮，点击即可更新！")
    print("  ⌨️  按 Ctrl+C 停止服务器")
    print()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\n  🛑 服务器已停止")
        server.shutdown()


if __name__ == "__main__":
    port = DEFAULT_PORT

    for arg in sys.argv[1:]:
        if arg.isdigit():
            port = int(arg)
        elif arg == "--help" or arg == "-h":
            print("用法: python3 web_server.py [端口号]")
            print()
            print("选项:")
            print("  端口号     服务器端口，默认 8899")
            print()
            print("API 接口:")
            print("  /api/quick-refresh   快速刷新（行情+分析+报告，约20秒）")
            print("  /api/refresh         完整刷新（全部6步，约60秒）")
            print("  /api/status          查看刷新状态")
            print()
            print("示例:")
            print("  python3 web_server.py              # 启动服务器")
            print("  python3 web_server.py 9000          # 自定义端口")
            sys.exit(0)

    run_server(port=port)
