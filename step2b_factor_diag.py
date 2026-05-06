"""
🔬 单因子 IC 诊断工具
对每个子因子单独做 walk-forward 测试，输出：
- IC 方向（正/负）
- IC 均值、IR、胜率
- 自动判断该因子是否"用反了"

运行方式：python3 step2b_factor_diag.py
输出：data/factor_ic_report.json
"""

import os
import json
import warnings
import numpy as np
import pandas as pd
from datetime import datetime
from scipy import stats

warnings.filterwarnings("ignore")

from config import STOCK_GROUPS, DATA_DIR
from step2b_predict import calc_features_for_stock, add_market_sector_factors


# ========= 原始因子定义 =========
# (因子名, 列名, 当前方向假设: +1=正向用, -1=反向用)
FACTOR_DEFS = [
    # 原 v5.0 的 10 个因子
    ("动量_5日涨幅", "ret_5d", +1),
    ("动量_20日涨幅", "ret_20d", +1),
    ("相对强弱_对大盘5日", "rel_to_market_5d", +1),
    ("相对强弱_对板块5日", "rel_to_sector_5d", +1),
    ("量价_成交量比", "vol_ratio", +1),
    ("量价_5日波动率", "volatility5", +1),
    ("量价_振幅", "amplitude", +1),
    ("位置_距20日高", "dist_to_high", +1),
    ("位置_距20日低", "dist_to_low", +1),
    ("位置_RSI14", "RSI14", +1),
    # 🆕 v7.0 新增 8 个零成本因子
    ("动量_加速度", "momentum_acceleration", +1),
    ("相对强弱_夏普20日", "sharpe_ratio_20", +1),
    ("量价_成交额环比", "turnover_change_5", +1),
    ("量价_价量相关性20日", "price_vol_corr_20", +1),
    ("量价_非流动性", "amihud_illiq", +1),
    ("位置_MACD柱", "MACD_hist", +1),
    ("位置_布林带", "BB_position", +1),
    ("位置_ATR14", "ATR_14", +1),
]



def load_history():
    path = os.path.join(DATA_DIR, "history_")
    import glob
    files = sorted(glob.glob(path + "*.csv"))
    if not files:
        print("❌ 未找到历史数据")
        return None
    df = pd.read_csv(files[-1], dtype={"代码": str}, encoding="utf-8-sig")
    df["代码"] = df["代码"].astype(str).str.zfill(6)
    df["日期"] = pd.to_datetime(df["日期"])
    df["收盘"] = pd.to_numeric(df["收盘"], errors="coerce")
    return df


def build_panel(history_df):
    """计算全部股票的因子面板"""
    all_codes = set()
    for grp in STOCK_GROUPS.values():
        all_codes.update(grp.keys())

    stock_list = []
    for code in all_codes:
        stock_df = history_df[history_df["代码"] == code]
        if len(stock_df) < 30:
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
    panel = add_market_sector_factors(panel, history_df, STOCK_GROUPS)

    # 丢弃预热期
    panel["row_num"] = panel.groupby("代码").cumcount()
    panel = panel[panel["row_num"] >= 20].copy()
    return panel


def compute_future_returns(panel, horizons=[1, 3, 5]):
    """为每行计算未来 N 日收益"""
    panel = panel.sort_values(["代码", "日期"]).reset_index(drop=True)
    for h in horizons:
        panel[f"future_ret_{h}d"] = (
            panel.groupby("代码")["收盘"].shift(-h) / panel["收盘"] - 1
        )
    return panel


def single_factor_ic(panel, factor_col, horizon_days):
    """单因子 IC 测试"""
    df = panel[["日期", "代码", factor_col, f"future_ret_{horizon_days}d"]].dropna()
    df = df[np.isfinite(df[factor_col]) & np.isfinite(df[f"future_ret_{horizon_days}d"])]
    if len(df) < 100:
        return None

    # 每日截面 Spearman IC
    daily_ic = df.groupby("日期").apply(
        lambda g: stats.spearmanr(g[factor_col], g[f"future_ret_{horizon_days}d"])[0]
        if len(g) >= 5 else np.nan
    ).dropna()

    if len(daily_ic) < 10:
        return None

    ic_mean = float(daily_ic.mean())
    ic_std = float(daily_ic.std())
    ir = ic_mean / ic_std if ic_std > 0 else 0
    ic_pos_pct = float((daily_ic > 0).mean() * 100)  # 正 IC 天数占比

    # t 统计量
    t_stat = ic_mean / (ic_std / np.sqrt(len(daily_ic))) if ic_std > 0 else 0

    return {
        "IC均值": round(ic_mean, 4),
        "IC标准差": round(ic_std, 4),
        "IR": round(ir, 3),
        "正IC天数占比": round(ic_pos_pct, 1),
        "t统计量": round(float(t_stat), 2),
        "样本天数": len(daily_ic),
        "总样本数": len(df),
        "建议方向": +1 if ic_mean > 0 else -1,
        "显著性": "显著" if abs(t_stat) > 1.96 else ("边缘" if abs(t_stat) > 1.28 else "不显著"),
    }


def run_diagnosis():
    print("\n" + "=" * 70)
    print("🔬 单因子 IC 诊断（walk-forward）")
    print("=" * 70)

    history_df = load_history()
    if history_df is None:
        return

    print(f"  📂 加载历史数据: {len(history_df)} 条, "
          f"{history_df['日期'].min().strftime('%Y-%m-%d')} ~ "
          f"{history_df['日期'].max().strftime('%Y-%m-%d')}")

    print("\n🔬 计算因子面板...")
    panel = build_panel(history_df)
    if panel is None:
        print("  ❌ 面板构建失败")
        return
    print(f"  ✅ 面板规模: {len(panel)} 行, {panel['代码'].nunique()} 只股票, "
          f"{panel['日期'].nunique()} 天")

    print("\n🔬 计算未来收益...")
    panel = compute_future_returns(panel, horizons=[1, 3, 5])

    print("\n🔬 逐因子 IC 检验...")
    report = {
        "生成时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "因子诊断": {},
    }

    # 表头
    print(f"\n{'因子名':<25} {'周期':>4} {'当前用':>6} {'IC均值':>9} {'IR':>7} "
          f"{'正IC%':>7} {'t值':>6} {'显著性':>8} {'建议':>6} {'改变?':>6}")
    print("-" * 100)

    factor_summary = {}
    for factor_name, col, current_direction in FACTOR_DEFS:
        factor_summary[factor_name] = {
            "列名": col,
            "当前方向": current_direction,
            "周期结果": {},
        }
        for h in [1, 3, 5]:
            res = single_factor_ic(panel, col, h)
            if res is None:
                continue
            factor_summary[factor_name]["周期结果"][f"{h}日"] = res
            change = "✅保持" if res["建议方向"] == current_direction else "🔴翻转"
            direction_str = "正向(+1)" if current_direction > 0 else "反向(-1)"
            print(
                f"{factor_name:<25} {h:>4}日 {direction_str:>6} "
                f"{res['IC均值']:>9.4f} {res['IR']:>7.3f} "
                f"{res['正IC天数占比']:>6.1f}% {res['t统计量']:>6.2f} "
                f"{res['显著性']:>8} "
                f"{('正向' if res['建议方向']>0 else '反向'):>6} "
                f"{change:>6}"
            )

    report["因子诊断"] = factor_summary

    # 聚合建议：用 5 日 IC 作为方向判定
    print("\n" + "=" * 70)
    print("🎯 方向修正建议（基于 5 日 IC）")
    print("=" * 70)

    suggestions = {}
    for factor_name, data in factor_summary.items():
        r5 = data["周期结果"].get("5日")
        if r5 is None:
            continue
        ic = r5["IC均值"]
        new_dir = r5["建议方向"]
        old_dir = data["当前方向"]
        significance = r5["显著性"]
        abs_ic = abs(ic)

        # 权重：IC 绝对值，但不显著的降权
        weight = abs_ic if significance != "不显著" else abs_ic * 0.3
        suggestions[factor_name] = {
            "原方向": old_dir,
            "建议方向": new_dir,
            "是否翻转": old_dir != new_dir,
            "IC均值_5日": ic,
            "显著性": significance,
            "建议权重": round(weight * 100, 2),  # 方便阅读
        }
        flip_str = "🔴 需翻转方向" if old_dir != new_dir else "✅ 方向正确"
        print(f"  {factor_name:<25} IC={ic:+.4f} ({significance})  {flip_str}")

    report["修正建议"] = suggestions

    # 保存
    out_path = os.path.join(DATA_DIR, "factor_ic_report.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n💾 诊断报告已保存: {out_path}")

    # 统计需要翻转的因子数
    need_flip = sum(1 for s in suggestions.values() if s["是否翻转"])
    significant = sum(1 for s in suggestions.values() if s["显著性"] != "不显著")
    print(f"\n📊 诊断小结：")
    print(f"   共 {len(suggestions)} 个因子，其中：")
    print(f"   - 🔴 需要翻转方向: {need_flip} 个")
    print(f"   - 🎯 显著 (|t|>1.28): {significant} 个")
    print(f"   - ❌ 不显著（接近噪声）: {len(suggestions)-significant} 个")

    return report


if __name__ == "__main__":
    run_diagnosis()
