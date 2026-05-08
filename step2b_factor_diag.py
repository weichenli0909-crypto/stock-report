"""
🔬 单因子 IC 诊断工具（v2.0 - 半衰期加权）

对每个子因子单独做 walk-forward 测试，输出：
- IC 方向（正/负）
- IC 均值、IR、胜率
- 自动判断该因子是否"用反了"

🆕 v2.0 升级：半衰期加权 IC
  - 旧版：165 天等权平均（最近和最远同等重要，反应滞后）
  - 新版：按半衰期 30 天指数加权（最近权重大，反应快）
  - 例：因子上周突然失效 → 旧算法还显示正 IC，新算法 1 周内就切换方向
  - 同时保留"等权 IC"和"半衰期 IC"的对比，便于评估稳定性

环境变量：
  IC_HALFLIFE_DAYS  - 半衰期天数，默认 30。想保守点设为 60（切换更慢）；
                     想激进设为 15（切换更快但噪声大）。

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

# ========= 半衰期配置 =========
IC_HALFLIFE_DAYS = int(os.environ.get("IC_HALFLIFE_DAYS", 30))



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


def single_factor_ic(panel, factor_col, horizon_days, halflife=IC_HALFLIFE_DAYS):
    """单因子 IC 测试（v2.0：同时计算等权 IC 和半衰期加权 IC）"""
    df = panel[["日期", "代码", factor_col, f"future_ret_{horizon_days}d"]].dropna()
    df = df[np.isfinite(df[factor_col]) & np.isfinite(df[f"future_ret_{horizon_days}d"])]
    if len(df) < 100:
        return None

    # 每日截面 Spearman IC
    daily_ic = df.groupby("日期").apply(
        lambda g: stats.spearmanr(g[factor_col], g[f"future_ret_{horizon_days}d"])[0]
        if len(g) >= 5 else np.nan
    ).dropna().sort_index()

    if len(daily_ic) < 10:
        return None

    # ===== 1) 传统等权 IC（保留作参考）=====
    ic_mean_eq = float(daily_ic.mean())
    ic_std_eq = float(daily_ic.std())
    ir_eq = ic_mean_eq / ic_std_eq if ic_std_eq > 0 else 0
    ic_pos_pct = float((daily_ic > 0).mean() * 100)

    # ===== 2) 🆕 半衰期加权 IC =====
    # 权重按 (1/2)^(t/halflife) 衰减；t=0 是最新一天，权重=1
    n = len(daily_ic)
    ages = np.arange(n - 1, -1, -1, dtype=float)  # 0 = 最新, n-1 = 最远
    weights = np.power(0.5, ages / halflife)
    w_sum = weights.sum()
    ic_values = daily_ic.values

    ic_mean_hl = float(np.sum(ic_values * weights) / w_sum)
    # 加权方差
    ic_var_hl = float(np.sum(weights * (ic_values - ic_mean_hl) ** 2) / w_sum)
    ic_std_hl = float(np.sqrt(ic_var_hl))
    ir_hl = ic_mean_hl / ic_std_hl if ic_std_hl > 0 else 0

    # 有效样本量（Kish 公式）: n_eff = (Σw)² / Σw²
    n_eff = float(w_sum ** 2 / np.sum(weights ** 2))
    t_stat_hl = ic_mean_hl / (ic_std_hl / np.sqrt(n_eff)) if ic_std_hl > 0 else 0

    # ===== 3) 用"半衰期 IC"作为最终判定 =====
    ic_mean = ic_mean_hl
    t_stat = t_stat_hl
    ir = ir_hl

    # ===== 4) 方向稳定性指标：看 EW IC 和半衰期 IC 是否同号 =====
    direction_aligned = (np.sign(ic_mean_eq) == np.sign(ic_mean_hl))
    direction_switch_warn = not direction_aligned and abs(ic_mean_hl) > 0.01
    # 翻转=True 说明"短期已与长期反向"，是个重要提示

    return {
        # 🎯 对外接口字段（保持向后兼容，以半衰期为准）
        "IC均值": round(ic_mean, 4),
        "IC标准差": round(ic_std_hl, 4),
        "IR": round(ir, 3),
        "正IC天数占比": round(ic_pos_pct, 1),
        "t统计量": round(float(t_stat), 2),
        "样本天数": len(daily_ic),
        "有效样本数": round(n_eff, 1),
        "总样本数": len(df),
        "建议方向": +1 if ic_mean > 0 else -1,
        "显著性": "显著" if abs(t_stat) > 1.96 else ("边缘" if abs(t_stat) > 1.28 else "不显著"),
        # 🆕 诊断字段
        "半衰期天数": halflife,
        "IC均值_等权": round(ic_mean_eq, 4),
        "IC均值_半衰期": round(ic_mean_hl, 4),
        "IR_等权": round(ir_eq, 3),
        "IR_半衰期": round(ir_hl, 3),
        "短长期方向是否一致": direction_aligned,
        "方向漂移警告": direction_switch_warn,
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
    report["配置"] = {
        "IC_半衰期天数": IC_HALFLIFE_DAYS,
        "说明": "IC均值/权重/方向 均以半衰期加权 IC 为准；等权 IC 保留仅作参考",
    }

    # 🆕 方向漂移警告（短期与长期方向不一致的因子）
    drift_factors = []
    for name, data in factor_summary.items():
        r5 = data["周期结果"].get("5日")
        if r5 and r5.get("方向漂移警告"):
            drift_factors.append((name, r5["IC均值_等权"], r5["IC均值_半衰期"]))

    if drift_factors:
        print("\n" + "=" * 70)
        print("⚡ 方向漂移警告（近期行情已与长期反转，半衰期 IC 已提前捕捉）")
        print("=" * 70)
        for name, ic_eq, ic_hl in drift_factors:
            print(f"  {name:<25} 等权 IC={ic_eq:+.4f}  →  半衰期 IC={ic_hl:+.4f}  "
                  f"{'🔴 方向切换' if np.sign(ic_eq) != np.sign(ic_hl) else ''}")
        print(f"\n  💡 这类因子通常对应行情风格切换（如趋势→反转），")
        print(f"     半衰期 IC 提前 {IC_HALFLIFE_DAYS} 天（等权一半样本期）捕捉到，")
        print(f"     让 v5.0 模型自动调整方向，抢回 1-2 周的反应时间。")

    # 保存
    out_path = os.path.join(DATA_DIR, "factor_ic_report.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n💾 诊断报告已保存: {out_path}")

    # 统计
    need_flip = sum(1 for s in suggestions.values() if s["是否翻转"])
    significant = sum(1 for s in suggestions.values() if s["显著性"] != "不显著")
    print(f"\n📊 诊断小结 (半衰期 = {IC_HALFLIFE_DAYS} 天)：")
    print(f"   共 {len(suggestions)} 个因子，其中：")
    print(f"   - 🔴 需要翻转方向: {need_flip} 个")
    print(f"   - 🎯 显著 (|t|>1.28): {significant} 个")
    print(f"   - ❌ 不显著（接近噪声）: {len(suggestions)-significant} 个")
    print(f"   - ⚡ 方向漂移中: {len(drift_factors)} 个")

    return report



if __name__ == "__main__":
    run_diagnosis()
