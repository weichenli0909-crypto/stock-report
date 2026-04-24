"""
🧹 第二步：数据分析
对采集的数据进行清洗、计算和统计分析
"""

import os
import json
import pandas as pd
import numpy as np
from datetime import datetime
from config import STOCK_GROUPS, DATA_DIR, get_all_stocks


def load_today_data():
    """加载今天采集的数据文件"""
    today = datetime.now().strftime("%Y%m%d")

    data = {}

    # 加载实时行情
    path = os.path.join(DATA_DIR, f"realtime_{today}.csv")
    if os.path.exists(path):
        data["realtime"] = pd.read_csv(path, dtype={"代码": str})
        data["realtime"]["代码"] = data["realtime"]["代码"].astype(str).str.zfill(6)
        print(f"  📂 加载实时行情: {len(data['realtime'])} 条")
    else:
        print(f"  ⚠️ 未找到实时行情文件: {path}")
        data["realtime"] = pd.DataFrame()

    # 加载历史数据
    path = os.path.join(DATA_DIR, f"history_{today}.csv")
    if os.path.exists(path):
        data["history"] = pd.read_csv(path, dtype={"代码": str})
        data["history"]["代码"] = data["history"]["代码"].astype(str).str.zfill(6)
        print(f"  📂 加载历史数据: {len(data['history'])} 条")
    else:
        print(f"  ⚠️ 未找到历史数据文件: {path}")
        data["history"] = pd.DataFrame()

    # 加载板块资金流向
    path = os.path.join(DATA_DIR, f"sector_funds_{today}.csv")
    if os.path.exists(path):
        data["sector"] = pd.read_csv(path)
        print(f"  📂 加载板块资金: {len(data['sector'])} 条")
    else:
        print(f"  ⚠️ 未找到板块资金文件: {path}")
        data["sector"] = pd.DataFrame()

    return data


def analyze_realtime(df):
    """
    分析实时行情数据
    返回：涨跌排行、板块表现等
    """
    if df.empty:
        return {}

    results = {}

    # 确保涨跌幅是数值类型
    df["涨跌幅"] = pd.to_numeric(df["涨跌幅"], errors="coerce")
    df["成交额"] = pd.to_numeric(df["成交额"], errors="coerce")
    if "换手率" not in df.columns:
        df["换手率"] = 0
    df["换手率"] = pd.to_numeric(df["换手率"], errors="coerce")

    # 1. 涨幅排行 Top 5
    top_gainers = df.nlargest(5, "涨跌幅")[
        ["代码", "名称", "最新价", "涨跌幅", "成交额"]
    ].to_dict("records")
    results["涨幅Top5"] = top_gainers

    # 2. 跌幅排行 Top 5
    top_losers = df.nsmallest(5, "涨跌幅")[
        ["代码", "名称", "最新价", "涨跌幅", "成交额"]
    ].to_dict("records")
    results["跌幅Top5"] = top_losers

    # 3. 成交额排行 Top 5
    top_volume = df.nlargest(5, "成交额")[
        ["代码", "名称", "最新价", "涨跌幅", "成交额"]
    ].to_dict("records")
    results["成交额Top5"] = top_volume

    # 4. 换手率排行 Top 5
    top_turnover = df.nlargest(5, "换手率")[
        ["代码", "名称", "涨跌幅", "换手率"]
    ].to_dict("records")
    results["换手率Top5"] = top_turnover

    # 5. 整体统计
    results["整体统计"] = {
        "上涨数": int((df["涨跌幅"] > 0).sum()),
        "下跌数": int((df["涨跌幅"] < 0).sum()),
        "平盘数": int((df["涨跌幅"] == 0).sum()),
        "平均涨跌幅": round(float(df["涨跌幅"].mean()), 2),
        "总成交额(亿)": round(float(df["成交额"].sum() / 1e8), 2),
    }

    # 6. 按板块统计平均涨跌幅
    sector_perf = []
    for sector_name, stocks in STOCK_GROUPS.items():
        sector_codes = list(stocks.keys())
        sector_df = df[df["代码"].isin(sector_codes)]
        if not sector_df.empty:
            avg_change = round(float(sector_df["涨跌幅"].mean()), 2)
            total_amount = round(float(sector_df["成交额"].sum() / 1e8), 2)
            sector_perf.append(
                {
                    "板块": sector_name,
                    "平均涨跌幅": avg_change,
                    "成交额(亿)": total_amount,
                    "个股数": len(sector_df),
                }
            )
    sector_perf.sort(key=lambda x: x["平均涨跌幅"], reverse=True)
    results["板块表现"] = sector_perf

    return results


def analyze_history(df):
    """
    分析历史数据
    返回：近期趋势、波动率等
    """
    if df.empty:
        return {}

    results = {}
    all_stocks = get_all_stocks()

    stock_trends = []
    for code, name in all_stocks.items():
        stock_df = df[df["代码"] == code].copy()
        if stock_df.empty or len(stock_df) < 2:
            continue

        # 确保日期排序
        if "日期" in stock_df.columns:
            stock_df["日期"] = pd.to_datetime(stock_df["日期"])
            stock_df = stock_df.sort_values("日期")

        # 计算指标
        close_col = "收盘" if "收盘" in stock_df.columns else "最新价"
        if close_col not in stock_df.columns:
            continue

        closes = pd.to_numeric(stock_df[close_col], errors="coerce").dropna()
        if len(closes) < 2:
            continue

        # 近5日涨跌幅
        if len(closes) >= 5:
            change_5d = round(float((closes.iloc[-1] / closes.iloc[-5] - 1) * 100), 2)
        else:
            change_5d = round(float((closes.iloc[-1] / closes.iloc[0] - 1) * 100), 2)

        # 近期最高/最低
        high_col = "最高" if "最高" in stock_df.columns else close_col
        low_col = "最低" if "最低" in stock_df.columns else close_col
        recent_high = float(pd.to_numeric(stock_df[high_col], errors="coerce").max())
        recent_low = float(pd.to_numeric(stock_df[low_col], errors="coerce").min())

        # 波动率（日收益率标准差 * sqrt(252)）
        returns = closes.pct_change().dropna()
        volatility = (
            round(float(returns.std() * np.sqrt(252) * 100), 2)
            if len(returns) > 1
            else 0
        )

        # 均线位置
        ma5 = round(float(closes.tail(5).mean()), 2) if len(closes) >= 5 else None
        ma10 = round(float(closes.tail(10).mean()), 2) if len(closes) >= 10 else None
        ma20 = round(float(closes.tail(20).mean()), 2) if len(closes) >= 20 else None

        stock_trends.append(
            {
                "代码": code,
                "名称": name,
                "最新价": round(float(closes.iloc[-1]), 2),
                "近5日涨跌幅": change_5d,
                "近期最高": round(recent_high, 2),
                "近期最低": round(recent_low, 2),
                "波动率(年化%)": volatility,
                "MA5": ma5,
                "MA10": ma10,
                "MA20": ma20,
            }
        )

    # 按近5日涨跌幅排序
    stock_trends.sort(key=lambda x: x["近5日涨跌幅"], reverse=True)
    results["个股趋势"] = stock_trends

    # 近5日强势股（涨幅 > 5%）
    results["强势股"] = [s for s in stock_trends if s["近5日涨跌幅"] > 5]

    # 近5日弱势股（跌幅 > 5%）
    results["弱势股"] = [s for s in stock_trends if s["近5日涨跌幅"] < -5]

    return results


def run_analysis():
    """
    执行完整的数据分析流程
    """
    print("\n" + "=" * 60)
    print(f"🔍 开始数据分析 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # 加载数据
    data = load_today_data()

    # 分析实时行情
    print("\n🔍 分析实时行情...")
    realtime_results = analyze_realtime(data["realtime"])

    # 分析历史数据
    print("🔍 分析历史趋势...")
    history_results = analyze_history(data["history"])

    # 汇总分析结果
    analysis = {
        "分析日期": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "实时分析": realtime_results,
        "趋势分析": history_results,
    }

    # 保存分析结果
    today = datetime.now().strftime("%Y%m%d")
    output_path = os.path.join(DATA_DIR, f"analysis_{today}.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(analysis, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n💾 分析结果已保存: {output_path}")

    # 打印摘要
    if realtime_results:
        stats = realtime_results.get("整体统计", {})
        print(f"\n📊 今日概览:")
        print(
            f"  上涨 {stats.get('上涨数', 0)} 只 | 下跌 {stats.get('下跌数', 0)} 只 | 平均涨跌幅 {stats.get('平均涨跌幅', 0)}%"
        )

        if realtime_results.get("板块表现"):
            print(f"\n📊 板块表现排名:")
            for s in realtime_results["板块表现"]:
                emoji = "🔴" if s["平均涨跌幅"] >= 0 else "🟢"
                print(
                    f"  {emoji} {s['板块']}: {s['平均涨跌幅']}% (成交额 {s['成交额(亿)']} 亿)"
                )

    print("\n✅ 数据分析完成！")
    return analysis


if __name__ == "__main__":
    run_analysis()
