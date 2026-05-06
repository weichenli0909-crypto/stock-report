"""
🚀 股票数据工作流 - 主入口
一键运行完整的 数据采集 → 舆情采集 → 美股采集 → 数据分析 → 报告生成 流程

聚焦板块：AI算力 · CPO · 光模块 · 光通信 · OCS · PCB + 美股关联
"""

import sys
import os
import time
import subprocess
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def print_banner():
    banner = """
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║   📊  AI / 光通信板块 - 股票数据工作流 v3.0                   ║
║                                                              ║
║   聚焦：AI算力 · CPO · 光模块 · 光通信 · OCS · PCB           ║
║                                                              ║
║   Step 1: 📥 行情采集（实时行情 + 历史数据 + 板块表现）       ║
║   Step 2: 📰 舆情采集（新闻动态 + 情绪分析 + 事件追踪）      ║
║   Step 3: 🇺🇸 美股采集（关联美股行情 + A股关联映射）          ║
║   Step 4: 🔍 数据分析（涨跌排行 + 板块对比 + 趋势分析）      ║
║   Step 5: 🤖 ML预测（随机森林 + 梯度提升 → 涨跌预测）       ║
║   Step 6: 📊 报告生成（图表 + 产业链 + 个股档案 + 预测）     ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)


def run_full_workflow():
    print_banner()
    start_time = time.time()
    total_steps = 8
    print(f"🕐 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Step 1: 行情采集
    print("━" * 60)
    print(f"  🔶 STEP 1 / {total_steps} : 行情数据采集")
    print("━" * 60)
    try:
        from step1_collect import run_collection

        run_collection()
    except Exception as e:
        print(f"\n❌ 行情采集出错: {e}")
        import traceback

        traceback.print_exc()
        return

    # Step 2: 舆情采集
    print("\n" + "━" * 60)
    print(f"  🔶 STEP 2 / {total_steps} : 舆情新闻采集")
    print("━" * 60)
    try:
        from step1b_news import run_news_collection

        run_news_collection()
    except Exception as e:
        print(f"\n⚠️ 舆情采集出错（非致命，继续）: {e}")

    # Step 2.5: 🧠 LLM 语义化舆情（若有 API key 则升级，否则保持关键词法）
    print("\n" + "━" * 60)
    print(f"  🔶 STEP 2.5 / {total_steps} : 🧠 LLM 语义化舆情（可选）")
    print("━" * 60)
    try:
        from step1b_llm_sentiment import run_llm_sentiment

        run_llm_sentiment()
    except Exception as e:
        print(f"\n⚠️ LLM 舆情出错（非致命，继续使用关键词法）: {e}")

    # Step 3: 美股采集

    print("\n" + "━" * 60)
    print(f"  🔶 STEP 3 / {total_steps} : 美股关联标的采集")
    print("━" * 60)
    try:
        from step1c_us_stocks import run_us_stock_collection

        run_us_stock_collection()
    except Exception as e:
        print(f"\n⚠️ 美股采集出错（非致命，继续）: {e}")

    # Step 4: 资金流向采集
    print("\n" + "━" * 60)
    print(f"  🔶 STEP 4 / {total_steps} : 资金流向采集")
    print("━" * 60)
    try:
        from step1d_fundflow import run_fundflow_collection

        run_fundflow_collection()
    except Exception as e:
        print(f"\n⚠️ 资金流向采集出错（非致命，继续）: {e}")

    # Step 5: 数据分析
    print("\n" + "━" * 60)
    print(f"  🔶 STEP 5 / {total_steps} : 数据分析")
    print("━" * 60)
    try:
        from step2_analyze import run_analysis

        run_analysis()
    except Exception as e:
        print(f"\n❌ 数据分析出错: {e}")
        import traceback

        traceback.print_exc()
        return

    # Step 5.5: 🎯 因子 IC 诊断（每天动态更新因子方向+权重，让 v5.0 模型始终用最新数据）
    print("\n" + "━" * 60)
    print(f"  🔶 STEP 5.5 / {total_steps} : 因子 IC 诊断（v5.0 数据驱动）")
    print("━" * 60)
    try:
        from step2b_factor_diag import run_diagnosis

        run_diagnosis()
    except Exception as e:

        print(f"\n⚠️ 因子诊断出错（非致命，继续，将 fallback 到上次结果）: {e}")

    # Step 6: ML预测
    print("\n" + "━" * 60)
    print(f"  🔶 STEP 6 / {total_steps} : 机器学习预测（v5.0）")
    print("━" * 60)
    try:
        from step2b_predict import run_prediction

        run_prediction()
    except Exception as e:
        print(f"\n⚠️ ML预测出错（非致命，继续）: {e}")


    # Step 7: 回测
    print("\n" + "━" * 60)
    print(f"  🔶 STEP 7 / {total_steps} : 预测回测")
    print("━" * 60)
    try:
        from step2c_backtest import run_backtest

        run_backtest()
    except Exception as e:
        print(f"\n⚠️ 回测出错（非致命，继续）: {e}")

    # Step 8: 报告生成
    print("\n" + "━" * 60)
    print(f"  🔶 STEP 8 / {total_steps} : 报告生成")
    print("━" * 60)
    try:
        from step3_report import run_report

        report_path = run_report()
    except Exception as e:
        print(f"\n❌ 报告生成出错: {e}")
        import traceback

        traceback.print_exc()
        return

    # Step 9: 3D 星空图
    print("\n" + "━" * 60)
    print(f"  🔶 STEP 9 / {total_steps} : 3D 股票星空图")
    print("━" * 60)
    try:
        from step4_starmap import run as run_starmap

        run_starmap()
    except Exception as e:
        print(f"\n⚠️ 星空图生成出错（非致命，继续）: {e}")

    # 完成
    elapsed = time.time() - start_time
    print("\n" + "=" * 60)
    print(f"🎉 工作流执行完成！")
    print(f"⏱️  总耗时: {elapsed:.1f} 秒")
    print(f"🕐 完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if report_path:
        print(f"\n📄 查看报告: open {report_path}")
    print("=" * 60)

    if report_path and os.path.exists(report_path):
        try:
            import webbrowser

            webbrowser.open(f"file://{report_path}")
            print("\n🌐 已在浏览器中打开报告！")
        except Exception:
            pass

    return report_path


def auto_deploy():
    """自动部署到 GitHub Pages"""
    print("\n🚀 开始自动部署到 GitHub Pages...")
    try:
        from deploy_pages import deploy

        deploy()
        send_notification("📊 股票日报已更新", "报告已成功部署到 GitHub Pages")
        return True
    except Exception as e:
        print(f"  ❌ 自动部署失败: {e}")
        return False


def send_notification(title, message):
    """发送系统通知（macOS）"""
    try:
        subprocess.run(
            [
                "osascript",
                "-e",
                f'display notification "{message}" with title "{title}"',
            ],
            check=True,
            timeout=10,
        )
    except Exception:
        pass


def run_single_step(step):
    if step == 1:
        from step1_collect import run_collection

        run_collection()
    elif step == 2:
        from step1b_news import run_news_collection

        run_news_collection()
    elif step == 3:
        from step1c_us_stocks import run_us_stock_collection

        run_us_stock_collection()
    elif step == 4:
        from step1d_fundflow import run_fundflow_collection

        run_fundflow_collection()
    elif step == 5:
        from step2_analyze import run_analysis

        run_analysis()
    elif step == 6:
        from step2b_predict import run_prediction

        run_prediction()
    elif step == 7:
        from step2c_backtest import run_backtest

        run_backtest()
    elif step == 8:
        from step3_report import run_report

        run_report()
    else:
        print(f"❌ 无效步骤号: {step}（可选 1-8）")


if __name__ == "__main__":
    deploy_flag = "--deploy" in sys.argv
    if deploy_flag:
        sys.argv.remove("--deploy")

    if len(sys.argv) > 1:
        try:
            step = int(sys.argv[1])
            print(f"🔶 运行单个步骤: Step {step}")
            run_single_step(step)
        except ValueError:
            if sys.argv[1] == "--help":
                print("用法:")
                print("  python run_workflow.py           # 运行完整工作流")
                print(
                    "  python run_workflow.py --deploy  # 运行完整工作流并自动部署到 GitHub Pages"
                )
                print("  python run_workflow.py 1         # 只运行行情采集")
                print("  python run_workflow.py 2         # 只运行舆情采集")
                print("  python run_workflow.py 3         # 只运行美股采集")
                print("  python run_workflow.py 4         # 只运行资金流向采集")
                print("  python run_workflow.py 5         # 只运行数据分析")
                print("  python run_workflow.py 6         # 只运行ML预测")
                print("  python run_workflow.py 7         # 只运行预测回测")
                print("  python run_workflow.py 8         # 只运行报告生成")
            else:
                print(f"❌ 未知参数: {sys.argv[1]}")
    else:
        report_path = run_full_workflow()
        if deploy_flag and report_path:
            auto_deploy()
