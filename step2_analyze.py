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

    # 加载个股资金流向
    path = os.path.join(DATA_DIR, f"fundflow_{today}.csv")
    if os.path.exists(path):
        data["fundflow"] = pd.read_csv(path, dtype={"代码": str})
        data["fundflow"]["代码"] = data["fundflow"]["代码"].astype(str).str.zfill(6)
        print(f"  📂 加载资金流向: {len(data['fundflow'])} 条")
    else:
        print(f"  ⚠️ 未找到资金流向文件: {path}")
        data["fundflow"] = pd.DataFrame()

    # 加载财务快照数据
    path = os.path.join(DATA_DIR, f"finance_{today}.csv")
    if os.path.exists(path):
        data["finance"] = pd.read_csv(path, dtype={"代码": str})
        data["finance"]["代码"] = data["finance"]["代码"].astype(str).str.zfill(6)
        print(f"  📂 加载财务数据: {len(data['finance'])} 条")
    else:
        print(f"  ⚠️ 未找到财务数据文件: {path}")
        data["finance"] = pd.DataFrame()

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


def analyze_sector_trend(df):
    """
    分析各板块近30天累计涨跌幅走势
    返回: {板块名: {dates: [...], values: [...]}}
    """
    if df.empty or len(df) < 2:
        return {}

    if "日期" not in df.columns:
        return {}
    df["日期"] = pd.to_datetime(df["日期"])
    df = df.sort_values("日期")

    close_col = "收盘" if "收盘" in df.columns else "最新价"
    if close_col not in df.columns:
        return {}

    df[close_col] = pd.to_numeric(df[close_col], errors="coerce")

    sector_trends = {}
    for sector_name, stocks in STOCK_GROUPS.items():
        sector_codes = list(stocks.keys())
        sector_df = df[df["代码"].isin(sector_codes)].copy()
        if sector_df.empty:
            continue

        # Pivot: dates as index, stocks as columns
        pivot = sector_df.pivot_table(index="日期", columns="代码", values=close_col)
        if pivot.empty or len(pivot) < 2:
            continue

        # Normalize each stock to 100 on its first trading day, then equal-weight average
        normalized = pivot.apply(
            lambda col: (col / col.dropna().iloc[0]) * 100 if col.dropna().size > 0 else col
        )
        sector_index = normalized.mean(axis=1).dropna()
        if len(sector_index) < 2:
            continue

        cumulative = (sector_index - 100).round(2)

        sector_trends[sector_name] = {
            "dates": [d.strftime("%m-%d") for d in sector_index.index],
            "values": cumulative.tolist(),
        }

    return sector_trends


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

        # ====== 技术指标计算 ======
        # MACD
        ema12 = closes.ewm(span=12, adjust=False).mean()
        ema26 = closes.ewm(span=26, adjust=False).mean()
        dif = ema12 - ema26
        dea = dif.ewm(span=9, adjust=False).mean()
        macd = 2 * (dif - dea)
        macd_val = round(float(macd.iloc[-1]), 2) if len(macd) > 0 else None
        dif_val = round(float(dif.iloc[-1]), 2) if len(dif) > 0 else None
        dea_val = round(float(dea.iloc[-1]), 2) if len(dea) > 0 else None

        # KDJ (N=9)
        low9 = closes.rolling(window=9).min()
        high9 = closes.rolling(window=9).max()
        rsv = (closes - low9) / (high9 - low9) * 100
        rsv = rsv.fillna(50)
        k = pd.Series(index=closes.index, dtype=float)
        d = pd.Series(index=closes.index, dtype=float)
        k.iloc[0] = 50
        d.iloc[0] = 50
        for i in range(1, len(closes)):
            k.iloc[i] = 2/3 * k.iloc[i-1] + 1/3 * rsv.iloc[i]
            d.iloc[i] = 2/3 * d.iloc[i-1] + 1/3 * k.iloc[i]
        j = 3 * k - 2 * d
        k_val = round(float(k.iloc[-1]), 1) if len(k) > 0 else None
        d_val = round(float(d.iloc[-1]), 1) if len(d) > 0 else None
        j_val = round(float(j.iloc[-1]), 1) if len(j) > 0 else None

        # RSI (6日)
        delta = closes.diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.rolling(window=6).mean()
        avg_loss = loss.rolling(window=6).mean()
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        rsi_val = round(float(rsi.iloc[-1]), 1) if len(rsi) > 0 and pd.notna(rsi.iloc[-1]) else None

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
                "MACD": macd_val,
                "DIF": dif_val,
                "DEA": dea_val,
                "K": k_val,
                "D": d_val,
                "J": j_val,
                "RSI6": rsi_val,
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


def analyze_fundflow(df):
    """
    分析资金流向数据
    返回：主力资金净流入排行、板块资金汇总等
    """
    if df.empty:
        return {}

    results = {}

    # 确保数值类型
    df["净流入"] = pd.to_numeric(df["净流入"], errors="coerce")
    df["流入资金"] = pd.to_numeric(df["流入资金"], errors="coerce")
    df["流出资金"] = pd.to_numeric(df["流出资金"], errors="coerce")
    df["成交额"] = pd.to_numeric(df["成交额"], errors="coerce")

    # 1. 主力资金净流入 Top 5
    top_inflow = df.nlargest(5, "净流入")[
        ["代码", "名称", "最新价", "涨跌幅", "净流入", "成交额"]
    ].copy()
    top_inflow["净流入(亿)"] = (top_inflow["净流入"] / 1e8).round(2)
    top_inflow["成交额(亿)"] = (top_inflow["成交额"] / 1e8).round(2)
    results["主力流入Top5"] = top_inflow[["代码", "名称", "最新价", "涨跌幅", "净流入(亿)", "成交额(亿)"]].to_dict("records")

    # 2. 主力资金净流出 Top 5
    top_outflow = df.nsmallest(5, "净流入")[
        ["代码", "名称", "最新价", "涨跌幅", "净流入", "成交额"]
    ].copy()
    top_outflow["净流入(亿)"] = (top_outflow["净流入"] / 1e8).round(2)
    top_outflow["成交额(亿)"] = (top_outflow["成交额"] / 1e8).round(2)
    results["主力流出Top5"] = top_outflow[["代码", "名称", "最新价", "涨跌幅", "净流入(亿)", "成交额(亿)"]].to_dict("records")

    # 3. 按板块统计资金流向
    sector_fund = []
    for sector_name, stocks in STOCK_GROUPS.items():
        sector_codes = list(stocks.keys())
        sector_df = df[df["代码"].isin(sector_codes)]
        if sector_df.empty:
            continue
        net = sector_df["净流入"].sum()
        inflow = sector_df["流入资金"].sum()
        outflow = sector_df["流出资金"].sum()
        sector_fund.append({
            "板块": sector_name,
            "主力净流入(亿)": round(float(net / 1e8), 2),
            "流入(亿)": round(float(inflow / 1e8), 2),
            "流出(亿)": round(float(outflow / 1e8), 2),
            "个股数": len(sector_df),
        })
    sector_fund.sort(key=lambda x: x["主力净流入(亿)"], reverse=True)
    results["板块资金"] = sector_fund

    # 4. 个股资金流向映射（供报告使用）
    fund_map = {}
    for _, row in df.iterrows():
        code = str(row["代码"]).zfill(6)
        fund_map[code] = {
            "净流入(亿)": round(float(row["净流入"] / 1e8), 2) if pd.notna(row["净流入"]) else 0,
            "流入(亿)": round(float(row["流入资金"] / 1e8), 2) if pd.notna(row["流入资金"]) else 0,
            "流出(亿)": round(float(row["流出资金"] / 1e8), 2) if pd.notna(row["流出资金"]) else 0,
        }
    results["个股资金映射"] = fund_map

    return results


def analyze_sector_finance(df):
    """
    分析各板块财务指标对比
    返回: {板块名: [个股财务指标列表]}
    """
    if df.empty:
        return {}

    results = {}
    # 确保数值类型
    numeric_cols = ["最新价", "涨跌幅", "换手率", "市盈率-动态", "市净率", "总市值", "流通市值", "成交额"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    for sector_name, stocks in STOCK_GROUPS.items():
        sector_codes = list(stocks.keys())
        sector_df = df[df["代码"].isin(sector_codes)].copy()
        if sector_df.empty:
            continue

        # 计算板块平均指标
        avg_pe = sector_df["市盈率-动态"].replace([np.inf, -np.inf], np.nan).mean()
        avg_pb = sector_df["市净率"].replace([np.inf, -np.inf], np.nan).mean()
        total_mv = sector_df["总市值"].sum()

        stock_list = []
        for _, row in sector_df.iterrows():
            pe = row.get("市盈率-动态")
            pb = row.get("市净率")
            mv = row.get("总市值", 0)
            stock_list.append({
                "代码": str(row["代码"]).zfill(6),
                "名称": row.get("名称", ""),
                "最新价": round(float(row.get("最新价", 0)), 2) if pd.notna(row.get("最新价")) else "-",
                "涨跌幅": round(float(row.get("涨跌幅", 0)), 2) if pd.notna(row.get("涨跌幅")) else "-",
                "市盈率": round(float(pe), 1) if pd.notna(pe) and pe > 0 and pe < 5000 else "-",
                "市净率": round(float(pb), 1) if pd.notna(pb) and pb > 0 and pb < 5000 else "-",
                "总市值(亿)": round(float(mv / 1e8), 1) if pd.notna(mv) and mv > 0 else "-",
                "换手率": round(float(row.get("换手率", 0)), 2) if pd.notna(row.get("换手率")) else "-",
            })

        # 按总市值排序
        stock_list.sort(key=lambda x: x["总市值(亿)"] if isinstance(x["总市值(亿)"], (int, float)) else 0, reverse=True)

        results[sector_name] = {
            "平均市盈率": round(float(avg_pe), 1) if pd.notna(avg_pe) and avg_pe > 0 and avg_pe < 5000 else "-",
            "平均市净率": round(float(avg_pb), 1) if pd.notna(avg_pb) and avg_pb > 0 and avg_pb < 5000 else "-",
            "总市值(亿)": round(float(total_mv / 1e8), 1) if pd.notna(total_mv) else "-",
            "个股数": len(stock_list),
            "个股列表": stock_list,
        }

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

    # 分析板块走势
    print("🔍 分析板块走势...")
    sector_trend = analyze_sector_trend(data["history"])

    # 分析资金流向
    print("🔍 分析资金流向...")
    fundflow_results = analyze_fundflow(data["fundflow"])

    # 分析板块财务对比
    print("🔍 分析板块财务对比...")
    sector_finance = analyze_sector_finance(data["finance"])

    # 汇总分析结果
    analysis = {
        "分析日期": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "实时分析": realtime_results,
        "趋势分析": history_results,
        "板块走势": sector_trend,
        "资金流向": fundflow_results,
        "板块财务": sector_finance,
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
