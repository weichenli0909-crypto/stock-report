"""
⏰ 定时调度器 - 交易时间内自动刷新数据
盘中每隔 N 分钟自动重新采集 + 分析 + 生成报告

用法:
  python scheduler.py              # 默认每5分钟刷新
  python scheduler.py 10           # 每10分钟刷新
  python scheduler.py 3 --full     # 每3分钟刷新，含舆情+美股
"""

import sys
import os
import time
import signal
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def is_trading_time():
    """判断是否在A股交易时间"""
    now = datetime.now()
    weekday = now.weekday()  # 0=周一, 6=周日
    if weekday >= 5:  # 周末
        return False
    hour, minute = now.hour, now.minute
    t = hour * 100 + minute
    # 9:15 ~ 11:30, 13:00 ~ 15:05 (留5分钟缓冲)
    return (915 <= t <= 1135) or (1300 <= t <= 1505)


def is_extended_time():
    """扩展时段（盘前盘后也可以跑）"""
    now = datetime.now()
    weekday = now.weekday()
    if weekday >= 5:
        return False
    hour = now.hour
    return 8 <= hour <= 18


def run_quick_refresh():
    """快速刷新：只跑行情采集 + 分析 + 报告（跳过舆情和美股，更快）"""
    print(f"\n⚡ 快速刷新 - {datetime.now().strftime('%H:%M:%S')}")
    try:
        from step1_collect import run_collection

        run_collection()
    except Exception as e:
        print(f"  ❌ 行情采集出错: {e}")
        return False

    try:
        from step2_analyze import run_analysis

        run_analysis()
    except Exception as e:
        print(f"  ❌ 数据分析出错: {e}")
        return False

    try:
        from step3_report import run_report

        run_report()
    except Exception as e:
        print(f"  ❌ 报告生成出错: {e}")
        return False

    return True


def run_full_refresh():
    """完整刷新：全部5步"""
    print(f"\n🔄 完整刷新 - {datetime.now().strftime('%H:%M:%S')}")
    try:
        from step1_collect import run_collection

        run_collection()
    except Exception as e:
        print(f"  ❌ 行情采集出错: {e}")
        return False

    try:
        from step1b_news import run_news_collection

        run_news_collection()
    except Exception:
        pass

    try:
        from step1c_us_stocks import run_us_stock_collection

        run_us_stock_collection()
    except Exception:
        pass

    try:
        from step2_analyze import run_analysis

        run_analysis()
    except Exception as e:
        print(f"  ❌ 数据分析出错: {e}")
        return False

    try:
        from step3_report import run_report

        run_report()
    except Exception as e:
        print(f"  ❌ 报告生成出错: {e}")
        return False

    return True


def main():
    interval = 5  # 默认5分钟
    full_mode = False

    for arg in sys.argv[1:]:
        if arg == "--full":
            full_mode = True
        elif arg.isdigit():
            interval = int(arg)

    mode_label = "完整模式" if full_mode else "快速模式（行情+分析+报告）"

    print("=" * 60)
    print(f"⏰ AI/光通信板块 - 实时监控调度器")
    print(f"=" * 60)
    print(f"  📊 刷新间隔: 每 {interval} 分钟")
    print(f"  🔧 运行模式: {mode_label}")
    print(f"  🕐 交易时间: 9:15-11:30, 13:00-15:05 (工作日)")
    print(f"  📄 报告地址: output/report.html (浏览器自动刷新)")
    print(f"  ⌨️  按 Ctrl+C 停止")
    print(f"=" * 60)

    # 立即先跑一次完整的
    print("\n🚀 首次完整运行...")
    run_full_refresh()
    count = 1

    # 优雅退出
    running = True

    def signal_handler(sig, frame):
        nonlocal running
        running = False
        print(f"\n\n🛑 收到退出信号，停止调度器...")
        print(f"📊 共运行 {count} 次刷新")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    while running:
        # 等待下一次刷新
        next_run = datetime.now().strftime("%H:%M")
        mins_left = interval
        print(f"\n💤 等待 {interval} 分钟后刷新... (当前 {next_run})")

        for _ in range(interval * 60):
            if not running:
                break
            time.sleep(1)

        if not running:
            break

        now = datetime.now()

        # 判断是否在交易时间
        if not is_extended_time():
            print(f"  ⏸️  {now.strftime('%H:%M')} 非交易时段，跳过")
            continue

        # 执行刷新
        if full_mode or not is_trading_time():
            # 非交易时间或full模式，跑完整流程
            success = run_full_refresh()
        else:
            # 盘中快速刷新（只更新行情+分析+报告）
            success = run_quick_refresh()

        count += 1
        status = "✅" if success else "❌"
        print(f"\n{status} 第 {count} 次刷新完成 - {now.strftime('%H:%M:%S')}")


def run_daily_push():
    """每日收盘后自动推送：运行完整工作流 + 部署 + 通知"""
    target_hour, target_min = 15, 30

    print("=" * 60)
    print(f"📅 AI/光通信板块 - 每日自动推送")
    print("=" * 60)
    print(f"  🕐 目标时间: {target_hour:02d}:{target_min:02d}（收盘后）")
    print(f"  🚀 执行内容: 完整工作流 + GitHub Pages 部署 + 系统通知")
    print(f"  ⌨️  按 Ctrl+C 取消")
    print("=" * 60)

    running = True

    def signal_handler(sig, frame):
        nonlocal running
        running = False
        print(f"\n\n🛑 取消每日推送")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    # 等待到目标时间
    while running:
        now = datetime.now()
        if now.hour > target_hour or (now.hour == target_hour and now.minute >= target_min):
            print(f"\n🚀 开始执行每日推送... ({now.strftime('%H:%M:%S')})")
            break
        else:
            wait_sec = (target_hour * 3600 + target_min * 60) - (now.hour * 3600 + now.minute * 60 + now.second)
            if wait_sec > 60:
                print(f"  ⏳ 等待中... 还剩 {wait_sec // 60} 分钟")
                time.sleep(60)
            else:
                time.sleep(1)

    if not running:
        return

    # 执行完整工作流
    try:
        from run_workflow import run_full_workflow, auto_deploy

        report_path = run_full_workflow()
        if report_path:
            auto_deploy()
        else:
            print("  ❌ 报告生成失败，跳过部署")
    except Exception as e:
        print(f"  ❌ 每日推送失败: {e}")


if __name__ == "__main__":
    if "--daily" in sys.argv:
        run_daily_push()
    else:
        main()
