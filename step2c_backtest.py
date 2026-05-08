"""
📈 AI评分回测模块 v4.1
 walk-forward 历史模拟 + 排序质量评估
"""

import os
import json
import glob
import base64
import warnings
import numpy as np
import pandas as pd
from io import BytesIO
from datetime import datetime, timedelta
from scipy import stats

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as _fm

# 跨平台中文字体（复用 step3 的思路，精简版）
_PREFERRED_FONTS = [
    "Arial Unicode MS", "PingFang SC", "Heiti SC",
    "Noto Sans CJK SC", "Noto Sans CJK JP", "Noto Serif CJK SC",
    "WenQuanYi Zen Hei", "WenQuanYi Micro Hei",
    "Microsoft YaHei", "SimHei", "SimSun",
]
plt.rcParams["font.sans-serif"] = _PREFERRED_FONTS + plt.rcParams["font.sans-serif"]
plt.rcParams["axes.unicode_minus"] = False
_available = {f.name for f in _fm.fontManager.ttflist}
if not any(n in _available for n in _PREFERRED_FONTS):
    for _p in [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    ]:
        import os as _os
        if _os.path.exists(_p):
            try:
                _fm.fontManager.addfont(_p)
                _name = _fm.FontProperties(fname=_p).get_name()
                plt.rcParams["font.sans-serif"] = [_name] + plt.rcParams["font.sans-serif"]
                break
            except Exception:
                pass


warnings.filterwarnings("ignore")

from config import DATA_DIR, STOCK_GROUPS


def load_history_prices():
    """加载最近的历史价格数据"""
    today = datetime.now().strftime("%Y%m%d")
    path = os.path.join(DATA_DIR, f"history_{today}.csv")
    if not os.path.exists(path):
        hist_files = sorted(glob.glob(os.path.join(DATA_DIR, "history_*.csv")))
        if not hist_files:
            return pd.DataFrame()
        path = hist_files[-1]
    df = pd.read_csv(path, dtype={"代码": str}, encoding="utf-8-sig")
    df["代码"] = df["代码"].astype(str).str.zfill(6)
    df["日期"] = pd.to_datetime(df["日期"])
    df["收盘"] = pd.to_numeric(df["收盘"], errors="coerce")
    return df


def compute_scores_for_date(history_df, target_date, stock_groups):
    """
    对指定日期计算所有股票的AI评分（无未来数据泄露）
    """
    from step2b_predict import calc_features_for_stock, add_market_sector_factors, compute_factor_scores

    all_stocks = {}
    for group in stock_groups.values():
        all_stocks.update(group)

    # 只用到 target_date 的历史数据（防止未来泄露）
    hist_up_to = history_df[history_df["日期"] <= target_date].copy()

    stock_list = []
    for code in all_stocks:
        stock_df = hist_up_to[hist_up_to["代码"] == code]
        if len(stock_df) < 20:
            continue
        try:
            feat = calc_features_for_stock(stock_df)
            feat["代码"] = code
            stock_list.append(feat)
        except Exception:
            continue

    if not stock_list:
        return None

    panel = pd.concat(stock_list, ignore_index=True)

    # 市场/板块因子也用截至 target_date 的数据
    try:
        panel = add_market_sector_factors(panel, hist_up_to, stock_groups)
    except Exception:
        return None

    # 取 target_date 当天的数据
    target_panel = panel[panel["日期"] == target_date].copy()
    if len(target_panel) < 5:
        return None

    # 丢弃预热期不够的行（个股因子计算需要至少20天历史）
    target_panel["row_num"] = target_panel.groupby("代码").cumcount()
    # 这里 cumcount 是针对排序后的数据，但由于我们只取了 target_date 的行，
    # 每只股票只有一行，cumcount 会返回0。所以这个过滤不适用于回溯场景。
    # 实际上 calc_features_for_stock 已经处理了 min_periods。

    scored = compute_factor_scores(target_panel)
    return scored


def run_historical_simulation(history_df, stock_groups, horizons=[1, 3, 5]):
    """
    walk-forward 历史模拟回测
    对历史每一天计算AI评分，并关联未来收益
    """
    print("\n🔬 启动历史 walk-forward 模拟回测...")
    history_df = history_df.copy().sort_values(["代码", "日期"]).reset_index(drop=True)
    history_df["日期"] = pd.to_datetime(history_df["日期"])
    history_df["代码"] = history_df["代码"].astype(str).str.zfill(6)
    history_df["收盘"] = pd.to_numeric(history_df["收盘"], errors="coerce")

    dates = sorted(history_df["日期"].unique())
    max_horizon = max(horizons)

    # 需要至少30天预热 + 未来收益
    start_idx = 30
    end_idx = len(dates) - max_horizon
    if start_idx >= end_idx:
        print("  ⚠️ 历史数据不足，无法模拟")
        return None

    all_records = {h: [] for h in horizons}

    total_days = end_idx - start_idx
    print(f"  📅 模拟区间: {dates[start_idx].strftime('%Y-%m-%d')} ~ {dates[end_idx-1].strftime('%Y-%m-%d')} ({total_days} 个交易日)")

    for i in range(start_idx, end_idx):
        target_date = dates[i]
        if i % 20 == 0:
            print(f"  ⏳ 模拟进度: {i-start_idx}/{total_days} ({target_date.strftime('%m-%d')})")

        scored = compute_scores_for_date(history_df, target_date, stock_groups)
        if scored is None or len(scored) < 5:
            continue

        for horizon in horizons:
            future_date = dates[i + horizon]
            future_df = history_df[history_df["日期"] == future_date][["代码", "收盘"]].copy()
            future_df["代码"] = future_df["代码"].astype(str).str.zfill(6)
            future_df["收盘"] = pd.to_numeric(future_df["收盘"], errors="coerce")
            future_map = future_df.set_index("代码")["收盘"].to_dict()

            for _, row in scored.iterrows():
                code = str(row["代码"]).zfill(6)
                if code not in future_map:
                    continue
                base_price = float(row["收盘"]) if pd.notna(row.get("收盘")) else None
                if base_price is None or base_price <= 0:
                    continue
                future_price = future_map[code]
                if pd.isna(future_price) or future_price <= 0:
                    continue
                future_ret = (future_price - base_price) / base_price

                all_records[horizon].append({
                    "date": target_date,
                    "code": code,
                    "ai_score": float(row.get("AI评分", 50)),
                    "signal_level": int(row.get("信号级别", 0)),
                    "future_ret": future_ret,
                    "momentum_score": float(row.get("momentum_score", 50)),
                    "relative_score": float(row.get("relative_score", 50)),
                    "vol_price_score": float(row.get("vol_price_score", 50)),
                    "location_score": float(row.get("location_score", 50)),
                    "external_score": float(row.get("external_score", 50)),
                })

    dfs = {}
    for h, records in all_records.items():
        if records:
            dfs[h] = pd.DataFrame(records)
            print(f"  ✅ {h}日收益样本: {len(records)} 条")
        else:
            print(f"  ⚠️ {h}日收益无样本")
    return dfs


def evaluate_simulation(df, horizon_days):
    """评估一组模拟结果的统计指标"""
    if df is None or len(df) < 50:
        return None

    # 1. 分位收益 spread
    df["quintile"] = df.groupby("date")["ai_score"].transform(
        lambda x: pd.qcut(x, 5, labels=[1, 2, 3, 4, 5], duplicates="drop")
    )
    # 如果某天股票太少分不了5组，会 drop 成更少，丢弃这些行
    df_valid = df.dropna(subset=["quintile"]).copy()
    if len(df_valid) < 50:
        return None

    quintile_rets = df_valid.groupby("quintile")["future_ret"].mean()
    top_q_ret = quintile_rets.get(5, np.nan)
    bottom_q_ret = quintile_rets.get(1, np.nan)
    spread = top_q_ret - bottom_q_ret if not pd.isna(top_q_ret) and not pd.isna(bottom_q_ret) else np.nan

    # 2. 每日 IC
    daily_ic = df.groupby("date").apply(
        lambda g: stats.spearmanr(g["ai_score"], g["future_ret"])[0]
        if len(g) >= 5 else np.nan
    ).dropna()
    ic_mean = daily_ic.mean()
    ic_std = daily_ic.std()
    ir = ic_mean / ic_std if ic_std > 0 else 0

    # 3. 方向准确率
    df["pred_dir"] = df["signal_level"].apply(lambda x: 1 if x >= 1 else (-1 if x <= -1 else 0))
    df["actual_dir"] = df["future_ret"].apply(lambda x: 1 if x > 0 else (-1 if x < 0 else 0))
    dir_mask = df["pred_dir"] != 0
    dir_acc = 50.0
    if dir_mask.sum() > 0:
        correct = (df.loc[dir_mask, "pred_dir"] == df.loc[dir_mask, "actual_dir"]).sum()
        dir_acc = correct / dir_mask.sum() * 100

    # 4. 强势/弱势命中率
    strong_mask = df["ai_score"] >= 65
    strong_hit = (df.loc[strong_mask, "future_ret"] > 0).sum() / strong_mask.sum() * 100 if strong_mask.sum() > 0 else 50.0

    weak_mask = df["ai_score"] <= 35
    weak_hit = (df.loc[weak_mask, "future_ret"] < 0).sum() / weak_mask.sum() * 100 if weak_mask.sum() > 0 else 50.0

    # 5. 多空组合日收益（Top20% - Bottom20%）
    long_short = df_valid.groupby("date").apply(
        lambda g: g[g["quintile"] == 5]["future_ret"].mean() - g[g["quintile"] == 1]["future_ret"].mean()
        if len(g[g["quintile"] == 5]) > 0 and len(g[g["quintile"] == 1]) > 0 else 0
    )
    ls_mean = long_short.mean()
    ls_std = long_short.std()
    ls_sharpe = ls_mean / ls_std * np.sqrt(252) if ls_std > 0 else 0

    return {
        "评估周期": f"{horizon_days}日",
        "总样本数": len(df),
        "交易天数": int(df["date"].nunique()),
        "平均分位收益差": round(float(spread) * 100, 2) if not pd.isna(spread) else None,
        "IC均值": round(float(ic_mean), 4),
        "IC标准差": round(float(ic_std), 4),
        "IR": round(float(ir), 3),
        "方向准确率": round(float(dir_acc), 1),
        "强势命中率": round(float(strong_hit), 1),
        "弱势命中率": round(float(weak_hit), 1),
        "多空日收益": round(float(ls_mean) * 100, 3),
        "多空年化夏普": round(float(ls_sharpe), 2),
    }


# ============ 图表生成 ============


def fig_to_base64(fig):
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=120, bbox_inches="tight")
    buf.seek(0)
    img = base64.b64encode(buf.read()).decode("utf-8")
    plt.close(fig)
    return img


def chart_quintile_cumulative(df, horizon_days):
    """分位组合累计收益曲线"""
    df = df.dropna(subset=["quintile"]).copy()
    if len(df) < 50:
        return None

    # 每日各分位平均收益
    daily_quintile = df.groupby(["date", "quintile"])["future_ret"].mean().unstack()
    if daily_quintile.empty or daily_quintile.shape[1] < 2:
        return None

    # 累计收益
    cum = (1 + daily_quintile.fillna(0)).cumprod() - 1

    fig, ax = plt.subplots(figsize=(12, 5))
    colors = ["#22c55e", "#86efac", "#94a3b8", "#fca5a5", "#ef4444"]
    for i, col in enumerate(cum.columns):
        label = {1: "Bottom20%", 2: "Q2", 3: "Q3", 4: "Q4", 5: "Top20%"}.get(int(col), f"Q{int(col)}")
        ax.plot(cum.index, cum[col] * 100, label=label, color=colors[i % len(colors)], linewidth=2)

    ax.axhline(y=0, color="gray", linewidth=0.5, linestyle="--")
    ax.set_xlabel("日期", color="#94a3b8")
    ax.set_ylabel("累计收益 (%)", color="#94a3b8")
    ax.set_title(f"分位组合累计收益 ({horizon_days}日持仓)", fontsize=14, fontweight="bold", color="#e2e8f0")
    ax.legend(loc="upper left", facecolor="#1e293b", edgecolor="#334155", labelcolor="#e2e8f0")
    ax.set_facecolor("#0f172a")
    fig.patch.set_facecolor("#0f172a")
    ax.tick_params(colors="#94a3b8")
    ax.grid(True, alpha=0.2, color="#334155")
    plt.xticks(rotation=45, ha="right")
    fig.tight_layout()
    return fig_to_base64(fig)


def chart_long_short_cumulative(df, horizon_days):
    """多空组合累计收益曲线"""
    df = df.dropna(subset=["quintile"]).copy()
    if len(df) < 50:
        return None

    ls_daily = df.groupby("date").apply(
        lambda g: g[g["quintile"] == 5]["future_ret"].mean() - g[g["quintile"] == 1]["future_ret"].mean()
        if len(g[g["quintile"] == 5]) > 0 and len(g[g["quintile"] == 1]) > 0 else 0
    )
    cum = (1 + ls_daily.fillna(0)).cumprod() - 1

    fig, ax = plt.subplots(figsize=(12, 4))
    color = "#60a5fa"
    ax.fill_between(cum.index, cum * 100, 0, alpha=0.2, color=color)
    ax.plot(cum.index, cum * 100, color=color, linewidth=2)
    ax.axhline(y=0, color="gray", linewidth=0.5, linestyle="--")
    ax.set_xlabel("日期", color="#94a3b8")
    ax.set_ylabel("累计收益 (%)", color="#94a3b8")
    ax.set_title(f"多空组合累计收益 (Top20% - Bottom20%, {horizon_days}日持仓)", fontsize=14, fontweight="bold", color="#e2e8f0")
    ax.set_facecolor("#0f172a")
    fig.patch.set_facecolor("#0f172a")
    ax.tick_params(colors="#94a3b8")
    ax.grid(True, alpha=0.2, color="#334155")
    plt.xticks(rotation=45, ha="right")
    fig.tight_layout()
    return fig_to_base64(fig)


def chart_ic_series(df, horizon_days):
    """每日IC序列"""
    daily_ic = df.groupby("date").apply(
        lambda g: stats.spearmanr(g["ai_score"], g["future_ret"])[0]
        if len(g) >= 5 else np.nan
    ).dropna()

    if len(daily_ic) < 5:
        return None

    fig, ax = plt.subplots(figsize=(12, 4))
    colors = ["#ef4444" if v >= 0 else "#22c55e" for v in daily_ic]
    ax.bar(daily_ic.index, daily_ic, color=colors, width=0.8)
    ax.axhline(y=daily_ic.mean(), color="#60a5fa", linewidth=1.5, linestyle="--", label=f"均值 {daily_ic.mean():.3f}")
    ax.axhline(y=0, color="gray", linewidth=0.5)
    ax.set_xlabel("日期", color="#94a3b8")
    ax.set_ylabel("IC (Spearman)", color="#94a3b8")
    ax.set_title(f"每日IC序列 ({horizon_days}日收益)", fontsize=14, fontweight="bold", color="#e2e8f0")
    ax.legend(facecolor="#1e293b", edgecolor="#334155", labelcolor="#e2e8f0")
    ax.set_facecolor("#0f172a")
    fig.patch.set_facecolor("#0f172a")
    ax.tick_params(colors="#94a3b8")
    ax.grid(True, alpha=0.2, color="#334155", axis="y")
    plt.xticks(rotation=45, ha="right")
    fig.tight_layout()
    return fig_to_base64(fig)


def save_backtest_charts(dfs, output_dir):
    """生成并保存回测图表"""
    os.makedirs(output_dir, exist_ok=True)
    charts = {}
    for horizon, df in dfs.items():
        if df is None or len(df) < 50:
            continue
        prefix = f"backtest_{horizon}d"

        q = chart_quintile_cumulative(df, horizon)
        if q:
            charts[f"{prefix}_quintile"] = q

        ls = chart_long_short_cumulative(df, horizon)
        if ls:
            charts[f"{prefix}_longshort"] = ls

        ic = chart_ic_series(df, horizon)
        if ic:
            charts[f"{prefix}_ic"] = ic

    # 保存到 JSON
    chart_path = os.path.join(DATA_DIR, "backtest_charts.json")
    with open(chart_path, "w", encoding="utf-8") as f:
        json.dump(charts, f, ensure_ascii=False, indent=2)
    print(f"  💾 回测图表已保存: {chart_path}")
    return charts


# ============ 主流程 ============


def run_backtest():
    """运行回测：历史模拟 + 日常评估"""
    print("\n" + "=" * 60)
    print(f"📈 AI评分回测 v4.1 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    history_df = load_history_prices()
    if history_df.empty:
        print("  ❌ 未找到历史数据，无法回测")
        return None

    # ====== 历史 walk-forward 模拟 ======
    sim_dfs = run_historical_simulation(history_df, STOCK_GROUPS, horizons=[1, 3, 5])
    sim_summary = {}
    if sim_dfs:
        print("\n📊 历史模拟结果汇总:")
        for horizon, df in sim_dfs.items():
            metrics = evaluate_simulation(df, horizon)
            if metrics:
                sim_summary[f"{horizon}日"] = metrics
                print(f"  {horizon}日 分位收益差: {metrics['平均分位收益差']}% | IC: {metrics['IC均值']:.4f} | IR: {metrics['IR']:.3f} | 多空夏普: {metrics['多空年化夏普']}")

        # 生成图表
        print("\n🎨 生成回测图表...")
        save_backtest_charts(sim_dfs, os.path.join(DATA_DIR, "output"))

        # 保存详细模拟数据（供后续分析）
        today = datetime.now().strftime("%Y%m%d")
        for horizon, df in sim_dfs.items():
            path = os.path.join(DATA_DIR, f"backtest_sim_{horizon}d_{today}.csv")
            df.to_csv(path, index=False, encoding="utf-8-sig")
    else:
        print("  ⚠️ 历史模拟无结果")

    # ====== 日常评估（基于已有预测文件）======
    print("\n🔍 评估已有预测文件...")
    pred_files = sorted(glob.glob(os.path.join(DATA_DIR, "predictions_*.json")))
    if len(pred_files) < 1:
        print("  ⚠️ 未找到预测文件")
    else:
        backtest_path = os.path.join(DATA_DIR, "backtest_history.json")
        backtest_records = []
        if os.path.exists(backtest_path):
            try:
                with open(backtest_path, "r", encoding="utf-8") as f:
                    backtest_records = json.load(f)
            except Exception:
                pass

        existing_dates = {r.get("预测日期") + "-" + r.get("评估周期") for r in backtest_records}
        new_results = []
        for pred_path in pred_files[-15:]:
            try:
                with open(pred_path, "r", encoding="utf-8") as f:
                    pred_data = json.load(f)
            except Exception:
                continue
            pred_date_str = pred_data.get("预测日期", "")[:10]
            if not pred_date_str:
                continue
            for horizon in [1, 3]:
                key = pred_date_str + f"-{horizon}日"
                if key not in existing_dates:
                    res = evaluate_single_prediction(pred_data, history_df, horizon)
                    if res:
                        new_results.append(res)
        if new_results:
            backtest_records.extend(new_results)
            with open(backtest_path, "w", encoding="utf-8") as f:
                json.dump(backtest_records, f, ensure_ascii=False, indent=2)
            print(f"  💾 新增 {len(new_results)} 条日常回测记录")

    # ====== 汇总输出 ======
    today = datetime.now().strftime("%Y%m%d")
    summary_path = os.path.join(DATA_DIR, f"backtest_summary_{today}.json")

    # 合并模拟汇总和日常汇总
    final_summary = {}
    if sim_summary:
        final_summary["历史模拟"] = sim_summary

    # 日常回测汇总
    if backtest_records:
        daily_summary = {}
        for period in ["1日", "3日"]:
            records = [r for r in backtest_records if r.get("评估周期") == period]
            if not records:
                continue
            total_samples = sum(r.get("样本数", 0) for r in records)
            dir_samples = sum(r.get("有方向样本", 0) for r in records)
            avg_dir = sum(r.get("方向准确率", 0) * r.get("有方向样本", 0) for r in records) / dir_samples if dir_samples else 50.0
            spreads = [r.get("分位收益差(Top-Btm)") for r in records if r.get("分位收益差(Top-Btm)") is not None]
            avg_spread = sum(spreads) / len(spreads) if spreads else 0
            daily_summary[period] = {
                "总样本数": total_samples,
                "历史天数": len(records),
                "平均方向准确率": round(avg_dir, 1),
                "平均分位收益差": round(avg_spread, 2),
            }
        if daily_summary:
            final_summary["日常回测"] = daily_summary

    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(final_summary, f, ensure_ascii=False, indent=2)
    print(f"\n💾 回测汇总已保存: {summary_path}")
    print(f"\n✅ 回测完成！")
    return final_summary


def evaluate_single_prediction(pred_data, history_df, horizon_days=1):
    """评估一组历史预测文件的质量（用于日常回测，保持兼容）"""
    pred_date = datetime.strptime(pred_data.get("预测日期", "")[:10], "%Y-%m-%d")
    predictions = pred_data.get("个股预测", {})
    if not predictions:
        return None

    records = []
    for code, p in predictions.items():
        ai_score = p.get("AI评分", 50)
        signal_level = p.get("信号级别", 0)

        stock_df = history_df[history_df["代码"] == code].sort_values("日期")
        if stock_df.empty:
            continue
        before = stock_df[stock_df["日期"] <= pred_date]
        if before.empty:
            continue
        base_price = float(before.iloc[-1]["收盘"])
        if base_price <= 0:
            continue

        dates_after = stock_df[stock_df["日期"] > pred_date]["日期"].tolist()
        if len(dates_after) < horizon_days:
            continue
        future_date = dates_after[horizon_days - 1]
        future_row = stock_df[stock_df["日期"] == future_date]
        if future_row.empty:
            continue
        future_price = float(future_row.iloc[0]["收盘"])
        if pd.isna(future_price):
            continue
        future_ret = (future_price - base_price) / base_price

        records.append({
            "ai_score": ai_score,
            "signal_level": signal_level,
            "future_ret": future_ret,
        })

    if len(records) < 5:
        return None

    df = pd.DataFrame(records)
    try:
        df["quintile"] = pd.qcut(df["ai_score"], 5, labels=[1, 2, 3, 4, 5], duplicates="drop")
    except ValueError:
        return None
    if df["quintile"].nunique() < 2:
        return None

    quintile_rets = df.groupby("quintile")["future_ret"].mean()
    spread = quintile_rets.get(5, np.nan) - quintile_rets.get(1, np.nan)
    corr, _ = stats.spearmanr(df["ai_score"], df["future_ret"])
    if pd.isna(corr):
        corr = 0

    df["pred_dir"] = df["signal_level"].apply(lambda x: 1 if x >= 1 else (-1 if x <= -1 else 0))
    df["actual_dir"] = df["future_ret"].apply(lambda x: 1 if x > 0 else (-1 if x < 0 else 0))
    dir_mask = df["pred_dir"] != 0
    dir_acc = 50.0
    if dir_mask.sum() > 0:
        correct = (df.loc[dir_mask, "pred_dir"] == df.loc[dir_mask, "actual_dir"]).sum()
        dir_acc = correct / dir_mask.sum() * 100

    strong_mask = df["ai_score"] >= 65
    strong_hit = (df.loc[strong_mask, "future_ret"] > 0).sum() / strong_mask.sum() * 100 if strong_mask.sum() > 0 else 50.0
    weak_mask = df["ai_score"] <= 35
    weak_hit = (df.loc[weak_mask, "future_ret"] < 0).sum() / weak_mask.sum() * 100 if weak_mask.sum() > 0 else 50.0

    return {
        "预测日期": pred_date.strftime("%Y-%m-%d"),
        "评估周期": f"{horizon_days}日",
        "样本数": len(df),
        "分位收益差(Top-Btm)": round(float(spread) * 100, 2) if not pd.isna(spread) else None,
        "Spearman相关": round(float(corr), 3),
        "方向准确率": round(float(dir_acc), 1),
        "有方向样本": int(dir_mask.sum()),
        "强势命中率": round(float(strong_hit), 1),
        "强势数量": int(strong_mask.sum()),
        "弱势命中率": round(float(weak_hit), 1),
        "弱势数量": int(weak_mask.sum()),
        "平均未来收益": round(float(df["future_ret"].mean() * 100), 2),
    }


if __name__ == "__main__":
    run_backtest()
