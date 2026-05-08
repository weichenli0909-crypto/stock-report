"""
🤖 多因子评分模块 v5.0 — 数据驱动的方向+权重

v5.0 相对 v4.0 的升级：
  1. 🎯 因子方向不再硬编码，而是从 data/factor_ic_report.json 读取 IC 自动决定
     （在强反转行情里会自动翻转动量/RSI/距高点等因子的方向）
  2. 📊 因子权重不再硬编码，而是按 |IC| 大小加权（IC 大的因子权重大，IC 接近 0 的因子近乎失效）
  3. 🛡️ 不显著因子自动降权（|t|<1.28 的因子权重打 0.3 折）
  4. 🔄 模型每天会读取最新的 factor_ic_report.json，行情风格变化时会自动适配
     （例如从反转行情切换到趋势行情，方向会自动翻回）

如何更新 IC 报告：
  python3 step2b_factor_diag.py    # 重新诊断所有因子，生成/覆盖 factor_ic_report.json
  （建议每周运行一次；也可以自动化到 scheduler）

兼容性：
  仍输出 momentum_score / relative_score / vol_price_score / location_score / external_score
  五大类子分数和最终 AI 评分，保证前端 UI 无需修改。
"""


import os
import json
import warnings
import numpy as np
import pandas as pd
from datetime import datetime
from glob import glob

warnings.filterwarnings("ignore")

from config import STOCK_GROUPS, DATA_DIR


# ============ 特征计算 ============


def calc_features_for_stock(df):
    """为单只股票计算所有原始因子值"""
    df = df.copy().sort_values("日期").reset_index(drop=True)

    close = pd.to_numeric(df["收盘"], errors="coerce")
    high = pd.to_numeric(df["最高"], errors="coerce")
    low = pd.to_numeric(df["最低"], errors="coerce")
    vol = pd.to_numeric(df["成交量"], errors="coerce")

    # 动量
    df["ret_5d"] = close.pct_change(5) * 100
    df["ret_20d"] = close.pct_change(20) * 100

    # 位置
    high_20 = close.rolling(20, min_periods=10).max()
    low_20 = close.rolling(20, min_periods=10).min()
    df["dist_to_high"] = (close - high_20) / high_20 * 100
    df["dist_to_low"] = (close - low_20) / low_20 * 100

    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(14, min_periods=7).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14, min_periods=7).mean()
    rs = gain / (loss + 1e-10)
    df["RSI14"] = 100 - (100 / (1 + rs))

    # 量价
    df["vol_ma5"] = vol.rolling(5, min_periods=1).mean()
    df["vol_ratio"] = vol / (df["vol_ma5"] + 1)
    df["amplitude"] = (high - low) / close * 100
    df["volatility5"] = close.pct_change().rolling(5, min_periods=2).std() * 100

    # ============== 🆕 v7.0 新增 8 个零成本因子 ==============
    # 1. 成交额（近似值 = close × volume）
    turnover = close * vol
    df["turnover_20_ma"] = turnover.rolling(20, min_periods=10).mean()
    df["turnover_change_5"] = turnover.rolling(5, min_periods=2).mean() / (
        turnover.rolling(20, min_periods=10).mean() + 1
    )

    # 2. 价量相关性（20 日 rolling corr）
    # 价涨量增为正相关，价涨量缩为负相关（反转预警）
    ret = close.pct_change()
    vol_change = vol.pct_change()
    df["price_vol_corr_20"] = ret.rolling(20, min_periods=10).corr(vol_change)

    # 3. MACD 柱状图（DIF - DEA）
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    dif = ema12 - ema26
    dea = dif.ewm(span=9, adjust=False).mean()
    df["MACD_hist"] = (dif - dea) / close * 100  # 标准化，避免股价量级影响

    # 4. 布林带位置（0~100，50 = 中轨，100 = 上轨）
    ma20 = close.rolling(20, min_periods=10).mean()
    std20 = close.rolling(20, min_periods=10).std()
    bb_upper = ma20 + 2 * std20
    bb_lower = ma20 - 2 * std20
    df["BB_position"] = (close - bb_lower) / (bb_upper - bb_lower + 1e-10) * 100

    # 5. 平均真实波幅 ATR（趋势强度）
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    df["ATR_14"] = tr.rolling(14, min_periods=7).mean() / close * 100  # 标准化

    # 6. Amihud 非流动性因子（|ret| / turnover，越大越不流动）
    # 已被学术界验证的"流动性溢价"因子
    df["amihud_illiq"] = (ret.abs() / (turnover + 1)).rolling(20, min_periods=10).mean() * 1e10

    # 7. 夏普式收益波动比（20 日）
    mean_ret_20 = ret.rolling(20, min_periods=10).mean()
    std_ret_20 = ret.rolling(20, min_periods=10).std()
    df["sharpe_ratio_20"] = mean_ret_20 / (std_ret_20 + 1e-6)

    # 8. 价格加速度（近期动量 - 远期动量，捕捉加速上涨/下跌）
    df["momentum_acceleration"] = close.pct_change(5) - close.pct_change(20)

    return df



def add_market_sector_factors(panel_df, history_df, stock_groups):
    """添加市场和板块层面的因子"""
    history_df = history_df.copy()
    history_df["日期"] = pd.to_datetime(history_df["日期"])
    history_df["收盘"] = pd.to_numeric(history_df["收盘"], errors="coerce")
    history_df["代码"] = history_df["代码"].astype(str).str.zfill(6)

    daily_rets = history_df.pivot_table(index="日期", columns="代码", values="收盘").pct_change()

    # 市场动量
    market_1d = daily_rets.mean(axis=1)
    market_5d = market_1d.rolling(5).apply(lambda x: (1 + x).prod() - 1, raw=True) * 100

    market_df = pd.DataFrame({
        "日期": market_1d.index,
        "market_ret_5d": market_5d.values,
    }).fillna(0)

    panel_df["日期"] = pd.to_datetime(panel_df["日期"])
    panel_df = panel_df.merge(market_df, on="日期", how="left")

    # 板块动量
    panel_df["sector_ret_5d"] = 0.0
    for sector_name, stocks in stock_groups.items():
        codes = list(stocks.keys())
        available = [c for c in codes if c in daily_rets.columns]
        if not available:
            continue
        sector_1d = daily_rets[available].mean(axis=1)
        sector_df = pd.DataFrame({
            "日期": sector_1d.index,
            "s_ret_5d": sector_1d.rolling(5).apply(lambda x: (1 + x).prod() - 1, raw=True).values * 100,
        }).fillna(0)

        mask = panel_df["代码"].isin(codes)
        if not mask.any():
            continue
        merged = panel_df.loc[mask, ["日期"]].merge(sector_df, on="日期", how="left")
        panel_df.loc[mask, "sector_ret_5d"] = merged["s_ret_5d"].values

    panel_df["rel_to_market_5d"] = panel_df["ret_5d"] - panel_df["market_ret_5d"]
    panel_df["rel_to_sector_5d"] = panel_df["ret_5d"] - panel_df["sector_ret_5d"]

    return panel_df


def load_external_features(today_str):
    """加载当日外部特征"""
    features = {}

    fundflow_path = os.path.join(DATA_DIR, f"fundflow_{today_str}.csv")
    if os.path.exists(fundflow_path):
        ff = pd.read_csv(fundflow_path, dtype={"代码": str})
        ff["代码"] = ff["代码"].astype(str).str.zfill(6)

        def parse_amount(s):
            if pd.isna(s):
                return 0
            s = str(s).strip()
            try:
                if "亿" in s:
                    return float(s.replace("亿", "")) * 1e8
                elif "万" in s:
                    return float(s.replace("万", "")) * 1e4
                elif "千" in s:
                    return float(s.replace("千", "")) * 1e3
                else:
                    return float(s)
            except Exception:
                return 0

        for col in ["净流入", "流入资金", "流出资金"]:
            if col in ff.columns:
                ff[col] = ff[col].apply(parse_amount)

        if "成交额" in ff.columns:
            ff["成交额"] = pd.to_numeric(ff["成交额"], errors="coerce")
            ff["fundflow_ratio"] = ff["净流入"] / (ff["成交额"] + 1)

        for _, row in ff.iterrows():
            features[row["代码"]] = {
                "fundflow_net": row.get("净流入", 0),
                "fundflow_ratio": row.get("fundflow_ratio", 0),
            }

    news_path = os.path.join(DATA_DIR, f"news_{today_str}.json")
    if os.path.exists(news_path):
        try:
            with open(news_path, "r", encoding="utf-8") as f:
                news = json.load(f)
            has_llm = bool(news.get("llm_分析时间"))
            if has_llm:
                print(f"  🧠 使用 LLM 舆情分析 ({news.get('llm_provider', '?')}/{news.get('llm_model', '?')})")
            for code, data in news.get("个股舆情", {}).items():
                code = str(code).zfill(6)
                # 🆕 优先用 LLM 情绪分（-2~+2 → 归一到 -1~+1），fallback 关键词法
                llm_stats = data.get("llm_情绪统计")
                if llm_stats and llm_stats.get("条数", 0) > 0:
                    sentiment = llm_stats.get("平均分", 0) / 2.0  # [-2,2] → [-1,1]
                    sentiment_source = "llm"
                else:
                    stats = data.get("情绪统计", {})
                    total = stats.get("正面", 0) + stats.get("负面", 0) + stats.get("中性", 0)
                    sentiment = (stats.get("正面", 0) - stats.get("负面", 0)) / total if total > 0 else 0
                    sentiment_source = "keyword"
                if code not in features:
                    features[code] = {}
                features[code]["news_sentiment"] = sentiment
                features[code]["sentiment_source"] = sentiment_source
        except Exception:
            pass


    us_path = os.path.join(DATA_DIR, f"us_stocks_{today_str}.json")
    if os.path.exists(us_path):
        try:
            with open(us_path, "r", encoding="utf-8") as f:
                us_data = json.load(f)
            for ticker, data in us_data.get("美股行情", {}).items():
                us_ret = data.get("涨跌幅", 0)
                for a_code in data.get("关联A股", {}).keys():
                    a_code = str(a_code).zfill(6)
                    if a_code not in features:
                        features[a_code] = {}
                    features[a_code][f"us_{ticker.lower()}_ret"] = us_ret
        except Exception:
            pass

    return features


# ============ 多因子评分计算（v5.0 数据驱动） ============


# 18 个基础因子到 6 大类的映射（v7.0：新增 8 个零成本因子）
FACTOR_GROUPS = {
    "momentum_score": ["动量_5日涨幅", "动量_20日涨幅", "动量_加速度"],
    "relative_score": ["相对强弱_对大盘5日", "相对强弱_对板块5日", "相对强弱_夏普20日"],
    "vol_price_score": [
        "量价_成交量比", "量价_5日波动率", "量价_振幅",
        "量价_成交额环比", "量价_价量相关性20日", "量价_非流动性"
    ],
    "location_score": [
        "位置_距20日高", "位置_距20日低", "位置_RSI14",
        "位置_MACD柱", "位置_布林带", "位置_ATR14"
    ],
}

# 因子名 -> 源列名（v7.0 扩充到 18 个）
FACTOR_COLS = {
    # 动量族
    "动量_5日涨幅": "ret_5d",
    "动量_20日涨幅": "ret_20d",
    "动量_加速度": "momentum_acceleration",  # 🆕
    # 相对强弱族
    "相对强弱_对大盘5日": "rel_to_market_5d",
    "相对强弱_对板块5日": "rel_to_sector_5d",
    "相对强弱_夏普20日": "sharpe_ratio_20",  # 🆕
    # 量价族
    "量价_成交量比": "vol_ratio",
    "量价_5日波动率": "volatility5",
    "量价_振幅": "amplitude",
    "量价_成交额环比": "turnover_change_5",  # 🆕
    "量价_价量相关性20日": "price_vol_corr_20",  # 🆕
    "量价_非流动性": "amihud_illiq",  # 🆕
    # 位置/技术族
    "位置_距20日高": "dist_to_high",
    "位置_距20日低": "dist_to_low",
    "位置_RSI14": "RSI14",
    "位置_MACD柱": "MACD_hist",  # 🆕
    "位置_布林带": "BB_position",  # 🆕
    "位置_ATR14": "ATR_14",  # 🆕
}


# 默认因子方向 & 权重（IC 报告不存在时的兜底值）
DEFAULT_DIRECTIONS = {name: +1 for name in FACTOR_COLS}
DEFAULT_WEIGHTS = {name: 1.0 for name in FACTOR_COLS}


def load_factor_ic_report():
    """
    加载 IC 诊断报告，返回 {因子名: {direction, weight, significant}}。
    若不存在，用 DEFAULT 值兜底并给出提示。
    """
    path = os.path.join(DATA_DIR, "factor_ic_report.json")
    if not os.path.exists(path):
        print("  ⚠️ 未找到 factor_ic_report.json，使用默认方向+等权重")
        print("     建议运行: python3 step2b_factor_diag.py 重新诊断")
        return {
            name: {"direction": +1, "abs_ic": 0.01, "weight": 1.0, "significant": False}
            for name in FACTOR_COLS
        }

    with open(path, "r", encoding="utf-8") as f:
        report = json.load(f)

    suggestions = report.get("修正建议", {})
    result = {}
    for name in FACTOR_COLS:
        s = suggestions.get(name)
        if not s:
            result[name] = {"direction": +1, "abs_ic": 0.01, "weight": 1.0, "significant": False}
            continue
        ic = float(s.get("IC均值_5日", 0))
        sig = s.get("显著性", "不显著")
        # 权重 = |IC|, 不显著因子打 0.3 折
        weight = abs(ic) if sig != "不显著" else abs(ic) * 0.3
        # 极小因子兜底，避免全 0
        weight = max(weight, 1e-4)
        result[name] = {
            "direction": +1 if ic > 0 else -1,
            "abs_ic": abs(ic),
            "weight": weight,
            "significant": sig != "不显著",
            "raw_ic": ic,
        }
    return result


def _pct_rank(series, direction):
    """把原始值转成 0-100 分数。direction=+1 表示值大分高，-1 表示值小分高。"""
    r = series.rank(pct=True) * 100
    return r if direction > 0 else (100 - r)


def compute_factor_scores(latest_df, factor_config=None):
    """
    计算每只股票的因子得分（v5.0 数据驱动版）
    - 每个基础因子根据 IC 方向决定正反向（rank 或 100-rank）
    - 每组内部按 |IC| 加权
    - 5 大类整体也按组内总 |IC| 加权合成 AI评分
    """
    df = latest_df.copy()
    n = len(df)
    if n < 5:
        return df

    if factor_config is None:
        factor_config = load_factor_ic_report()

    # 计算每个基础因子的 0-100 分数（内部列名 <factor_name>_score）
    for fname, col in FACTOR_COLS.items():
        cfg = factor_config.get(fname, {"direction": +1})
        if col not in df.columns:
            df[f"{fname}_score"] = 50.0
            continue
        s = pd.to_numeric(df[col], errors="coerce")
        if s.notna().sum() < 3:
            df[f"{fname}_score"] = 50.0
            continue
        df[f"{fname}_score"] = _pct_rank(s.fillna(s.median()), cfg["direction"])

    # 按组内 |IC| 加权合成 5 大类子分数
    group_total_weights = {}
    for group_name, factor_names in FACTOR_GROUPS.items():
        total_w = 0.0
        weighted_sum = pd.Series(0.0, index=df.index)
        for fname in factor_names:
            w = factor_config.get(fname, {}).get("weight", 0)
            if w <= 0:
                continue
            weighted_sum = weighted_sum + df[f"{fname}_score"] * w
            total_w += w
        if total_w > 0:
            df[group_name] = weighted_sum / total_w
        else:
            df[group_name] = 50.0
        group_total_weights[group_name] = total_w

    # 外部因子（舆情 + 资金流 + 美股）独立计算，暂用等权 + 默认正向
    # 这些因子没有历史回测数据（舆情历史缺失），先保持原 v4 逻辑
    df["sentiment_score"] = 50.0
    df["fundflow_score"] = 50.0
    df["us_score"] = 50.0

    if "news_sentiment" in df.columns and df["news_sentiment"].abs().sum() > 0:
        df["sentiment_score"] = (df["news_sentiment"].clip(-1, 1) + 1) * 50

    if "fundflow_ratio" in df.columns and df["fundflow_ratio"].abs().sum() > 0:
        df["fundflow_score"] = df["fundflow_ratio"].rank(pct=True) * 100

    us_cols = [c for c in df.columns if c.startswith("us_") and c.endswith("_ret")]
    if us_cols:
        df["us_avg_ret"] = df[us_cols].mean(axis=1)
        us_min, us_max = df["us_avg_ret"].min(), df["us_avg_ret"].max()
        if us_max > us_min:
            df["us_score"] = (df["us_avg_ret"] - us_min) / (us_max - us_min) * 100

    df["external_score"] = df["sentiment_score"] * 0.4 + df["fundflow_score"] * 0.4 + df["us_score"] * 0.2

    # 综合 AI 评分 = 5 大类按组内总 |IC| 加权
    # 外部因子是独立的（无 IC 验证），给一个较小的固定权重 0.05
    ext_weight = 0.05
    grp_total = sum(group_total_weights.values())
    if grp_total <= 0:
        # 兜底：五大类等权
        df["AI评分"] = (
            df["momentum_score"] + df["relative_score"]
            + df["vol_price_score"] + df["location_score"]
        ) / 4 * (1 - ext_weight) + df["external_score"] * ext_weight
    else:
        weighted = pd.Series(0.0, index=df.index)
        for gname, w in group_total_weights.items():
            weighted = weighted + df[gname] * (w / grp_total)
        df["AI评分"] = weighted * (1 - ext_weight) + df["external_score"] * ext_weight

    return df



# ============ 主流程 ============


def load_recent_predictions(days=15):
    """
    读取最近 N 天的 predictions_*.json，返回 {日期: {代码: AI评分}}。
    日期格式为 YYYY-MM-DD（来自文件中的预测日期）。
    """
    pred_files = sorted(glob(os.path.join(DATA_DIR, "predictions_*.json")))
    if not pred_files:
        return {}

    history = {}
    for path in pred_files[-days:]:
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            date_str = data.get("预测日期", "")[:10]
            if not date_str:
                continue
            preds = data.get("个股预测", {})
            history[date_str] = {
                code: info.get("AI评分", 50)
                for code, info in preds.items()
            }
        except Exception:
            continue
    return history


def compute_signal_metrics(predictions, history, min_days=3):
    """
    基于历史评分数据，为每只股票计算信号持续性和置信度指标。
    将结果直接更新到 predictions 字典中。
    """
    if not history:
        for p in predictions.values():
            p.update({
                "评分5日均值": None,
                "较昨日变化": None,
                "近5日变化": None,
                "连续强势天数": 0,
                "连续弱势天数": 0,
                "评分趋势斜率": None,
                "评分稳定性": None,
                "置信星级": 0,
                "信号预警": "",
            })
        return predictions

    dates = sorted(history.keys())
    for code, p in predictions.items():
        scores = []
        for d in dates:
            s = history[d].get(code)
            if s is not None:
                scores.append((d, s))

        if len(scores) < min_days:
            p.update({
                "评分5日均值": None,
                "较昨日变化": None,
                "近5日变化": None,
                "连续强势天数": 0,
                "连续弱势天数": 0,
                "评分趋势斜率": None,
                "评分稳定性": None,
                "置信星级": 0,
                "信号预警": "",
            })
            continue

        # 提取评分序列
        score_vals = [s for _, s in scores]
        latest_score = p["AI评分"]
        prev_score = score_vals[-1] if len(score_vals) >= 1 else latest_score

        # 连续天数统计（从最近一天往前数）
        consecutive_bull = 0
        consecutive_bear = 0
        for _, s in reversed(scores):
            if s >= 65:
                consecutive_bull += 1
            else:
                break
        for _, s in reversed(scores):
            if s <= 35:
                consecutive_bear += 1
            else:
                break

        # 近5日均值 & 变化
        recent_5 = score_vals[-5:]
        ma5 = float(np.mean(recent_5)) if recent_5 else latest_score
        delta_1d = round(latest_score - prev_score, 1)
        delta_5d = round(latest_score - recent_5[0], 1) if len(recent_5) >= 2 else None

        # 趋势斜率：近10天（或全部）线性回归
        n = min(len(score_vals), 10)
        if n >= 3:
            x = np.arange(n)
            y = np.array(score_vals[-n:], dtype=float)
            slope = float(np.polyfit(x, y, 1)[0])
        else:
            slope = None

        # 稳定性：近10天标准差
        if len(score_vals) >= 3:
            std = float(np.std(score_vals[-10:], ddof=0))
        else:
            std = None

        # ========== 置信度星级计算（0-5星）==========
        confidence = 0.0
        # 1) 基础分：偏离中性的程度
        confidence += abs(latest_score - 50) / 20.0  # 0~2.5

        # 2) 持续性加分
        if latest_score >= 65:
            confidence += min(consecutive_bull, 5) * 0.3
        elif latest_score <= 35:
            confidence += min(consecutive_bear, 5) * 0.3

        # 3) 趋势一致性加分
        if slope is not None:
            if latest_score > 50 and slope > 0:
                confidence += min(abs(slope) * 1.5, 1.0)
            elif latest_score < 50 and slope < 0:
                confidence += min(abs(slope) * 1.5, 1.0)
            elif (latest_score > 50 and slope < 0) or (latest_score < 50 and slope > 0):
                confidence -= 0.5  # 趋势与当前方向背离，扣分

        # 4) 稳定性加分/扣分
        if std is not None:
            if std < 5:
                confidence += 0.5
            elif std > 15:
                confidence -= 0.5

        # 5) 突变扣分
        if abs(delta_1d) > 15:
            confidence -= 1.0

        stars = int(round(np.clip(confidence, 0, 5)))

        # ========== 信号预警文本 ==========
        warnings = []
        if abs(delta_1d) >= 15:
            warnings.append("信号突变" if delta_1d > 0 else "信号骤降")
        if consecutive_bull >= 3:
            warnings.append(f"持续强势{consecutive_bull}天")
        if consecutive_bear >= 3:
            warnings.append(f"持续弱势{consecutive_bear}天")
        if slope is not None:
            if slope > 2 and latest_score >= 65:
                warnings.append("加速走强")
            elif slope < -2 and latest_score <= 35:
                warnings.append("加速走弱")
            elif slope < -1 and latest_score >= 65:
                warnings.append("强势衰减")
            elif slope > 1 and latest_score <= 35:
                warnings.append("弱势反弹")

        p.update({
            "评分5日均值": round(ma5, 1) if ma5 is not None else None,
            "较昨日变化": delta_1d,
            "近5日变化": delta_5d,
            "连续强势天数": consecutive_bull,
            "连续弱势天数": consecutive_bear,
            "评分趋势斜率": round(slope, 2) if slope is not None else None,
            "评分稳定性": round(std, 1) if std is not None else None,
            "置信星级": stars,
            "信号预警": "｜".join(warnings) if warnings else "",
        })

    return predictions


def run_prediction():
    print("\n" + "=" * 60)
    print(f"🤖 开始多因子评分 v5.0 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    print("=" * 60)

    today = datetime.now().strftime("%Y%m%d")

    # 加载历史数据
    history_path = os.path.join(DATA_DIR, f"history_{today}.csv")
    if not os.path.exists(history_path):
        hist_files = sorted(glob(os.path.join(DATA_DIR, "history_*.csv")))
        if not hist_files:
            print("  ❌ 未找到任何历史数据")
            return None
        history_path = hist_files[-1]
        today = os.path.basename(history_path).replace("history_", "").replace(".csv", "")
        print(f"  ⚠️ 未找到今日数据，使用最近文件")

    history_df = pd.read_csv(history_path, dtype={"代码": str}, encoding="utf-8-sig")
    history_df["代码"] = history_df["代码"].astype(str).str.zfill(6)
    print(f"  📂 加载历史数据: {len(history_df)} 条")

    all_stocks = {}
    for group in STOCK_GROUPS.values():
        all_stocks.update(group)
    print(f"  📊 关注股票: {len(all_stocks)} 只")

    # Step 1: 计算个股因子
    print("\n🔬 计算个股因子...")
    stock_list = []
    for code in all_stocks:
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
        print("  ❌ 数据不足")
        return None

    panel = pd.concat(stock_list, ignore_index=True)
    print(f"  ✅ 面板数据: {len(panel)} 条")

    # Step 2: 添加市场/板块因子
    print("🔬 添加市场与板块因子...")
    panel = add_market_sector_factors(panel, history_df, STOCK_GROUPS)

    # 丢弃预热期
    panel["row_num"] = panel.groupby("代码").cumcount()
    panel = panel[panel["row_num"] >= 20].copy()

    # Step 3: 预测最新一天
    latest_date = panel["日期"].max()
    latest_panel = panel[panel["日期"] == latest_date].copy()
    print(f"\n🔮 评分日期: {latest_date.strftime('%Y-%m-%d')} ({len(latest_panel)} 只股票)")

    # 加载外部特征
    ext_features = load_external_features(today)
    for col in ["fundflow_ratio", "fundflow_net", "news_sentiment"]:
        latest_panel[col] = 0.0
    for col in [c for c in latest_panel.columns if c.startswith("us_")]:
        latest_panel[col] = 0.0

    for code in latest_panel["代码"].unique():
        code = str(code).zfill(6)
        if code in ext_features:
            for k, v in ext_features[code].items():
                if k in latest_panel.columns:
                    latest_panel.loc[latest_panel["代码"] == code, k] = v

    # Step 4: 计算多因子评分
    print("🔬 计算多因子评分...")
    scored = compute_factor_scores(latest_panel)

    # 构建结果
    predictions = {}
    for _, row in scored.iterrows():
        code = str(row["代码"]).zfill(6)
        ai_score = float(row.get("AI评分", 50))
        current_price = float(row["收盘"]) if pd.notna(row.get("收盘")) else 0

        result = {
            "代码": code,
            "名称": all_stocks.get(code, ""),
            "最新价": round(current_price, 2),
            "日期": str(row["日期"]),
            "AI评分": round(ai_score, 1),
            "动量得分": round(float(row.get("momentum_score", 50)), 1),
            "相对强弱得分": round(float(row.get("relative_score", 50)), 1),
            "量价得分": round(float(row.get("vol_price_score", 50)), 1),
            "位置得分": round(float(row.get("location_score", 50)), 1),
            "外部得分": round(float(row.get("external_score", 50)), 1),
            "信号": "",
            "信号级别": 0,
        }

        if ai_score >= 80:
            result["信号"] = "强烈看好 🔴🔴🔴"
            result["信号级别"] = 3
        elif ai_score >= 65:
            result["信号"] = "看好 🔴🔴"
            result["信号级别"] = 2
        elif ai_score >= 55:
            result["信号"] = "微看好 🔴"
            result["信号级别"] = 1
        elif ai_score >= 45:
            result["信号"] = "中性 ⚪"
            result["信号级别"] = 0
        elif ai_score >= 35:
            result["信号"] = "微看空 🟢"
            result["信号级别"] = -1
        elif ai_score >= 20:
            result["信号"] = "看空 🟢🟢"
            result["信号级别"] = -2
        else:
            result["信号"] = "强烈看空 🟢🟢🟢"
            result["信号级别"] = -3

        predictions[code] = result

    # ========== 🆕 信号持续性与置信度计算 ==========
    print("\n🔬 计算信号持续性与置信度...")
    history = load_recent_predictions(days=15)
    predictions = compute_signal_metrics(predictions, history)

    # 汇总
    strong = sum(1 for p in predictions.values() if p["AI评分"] >= 65)
    weak = sum(1 for p in predictions.values() if p["AI评分"] <= 35)

    sector_predictions = {}
    for sector_name, stocks in STOCK_GROUPS.items():
        sector_preds = [predictions[c] for c in stocks if c in predictions]
        if sector_preds:
            avg_score = np.mean([p["AI评分"] for p in sector_preds])
            sector_predictions[sector_name] = {
                "平均AI评分": round(float(avg_score), 1),
                "强势数": sum(1 for p in sector_preds if p["AI评分"] >= 65),
                "弱势数": sum(1 for p in sector_preds if p["AI评分"] <= 35),
                "个股数": len(sector_preds),
            }

    sorted_by_score = sorted(predictions.values(), key=lambda x: x["AI评分"], reverse=True)

    def _top_item(p):
        return {
            "代码": p["代码"],
            "名称": p["名称"],
            "AI评分": p["AI评分"],
            "动量得分": p["动量得分"],
            "相对强弱得分": p["相对强弱得分"],
            "量价得分": p["量价得分"],
            "位置得分": p["位置得分"],
            "外部得分": p["外部得分"],
            "信号": p["信号"],
            "置信星级": p.get("置信星级", 0),
            "信号预警": p.get("信号预警", ""),
            "连续强势天数": p.get("连续强势天数", 0),
            "连续弱势天数": p.get("连续弱势天数", 0),
            "较昨日变化": p.get("较昨日变化"),
            "评分趋势斜率": p.get("评分趋势斜率"),
        }

    save_data = {
        "预测日期": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "预测周期": "多因子综合评分（非收益预测）",
        "评分说明": "基于动量、相对强弱、量价、位置、舆情、资金六大因子的百分位排名",
        "汇总": {
            "总股票数": len(predictions),
            "强势(AI≥65)": strong,
            "弱势(AI≤35)": weak,
        },
        "板块预测": sector_predictions,
        "强势Top5": [_top_item(p) for p in sorted_by_score[:5]],
        "弱势Top5": [_top_item(p) for p in sorted_by_score[-5:][::-1]],
        "个股预测": predictions,
    }

    path = os.path.join(DATA_DIR, f"predictions_{today}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(save_data, f, ensure_ascii=False, indent=2)
    print(f"\n💾 评分结果已保存: {path}")

    print(f"\n📊 评分汇总:")
    print(f"  强势 {strong} 只 | 弱势 {weak} 只")
    print(f"\n🔥 AI最看好 Top3:")
    for p in sorted_by_score[:3]:
        warn = f" [{p.get('信号预警', '')}]" if p.get("信号预警") else ""
        stars = "⭐" * p.get("置信星级", 0)
        print(
            f"  {p['名称']}: {p['信号']} (AI评分{p['AI评分']}, "
            f"置信{p.get('置信星级',0)}星{stars}, {p.get('信号预警','')})"
        )
    print(f"\n❄️ AI最看空 Top3:")
    for p in sorted_by_score[-3:]:
        warn = f" [{p.get('信号预警', '')}]" if p.get("信号预警") else ""
        stars = "⭐" * p.get("置信星级", 0)
        print(
            f"  {p['名称']}: {p['信号']} (AI评分{p['AI评分']}, "
            f"置信{p.get('置信星级',0)}星{stars}, {p.get('信号预警','')})"
        )

    print(f"\n✅ 多因子评分完成！")
    return save_data


if __name__ == "__main__":
    run_prediction()
