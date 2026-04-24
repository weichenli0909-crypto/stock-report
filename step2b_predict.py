"""
🤖 机器学习预测模块
基于历史行情数据，使用多种ML模型预测个股未来走势

特征工程：MA均线、RSI、MACD、布林带、成交量变化率、波动率等
模型组合：随机森林 + 梯度提升 + 线性回归 → 加权集成
预测目标：未来3日涨跌方向 + 预测价格区间
"""

import os
import json
import warnings
import numpy as np
import pandas as pd
from datetime import datetime

warnings.filterwarnings("ignore")

from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import cross_val_score

from config import STOCK_GROUPS, STOCK_PROFILES, DATA_DIR, OUTPUT_DIR


# ============ 技术指标计算 ============


def calc_ma(series, window):
    return series.rolling(window=window, min_periods=1).mean()


def calc_rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0).rolling(window=period, min_periods=1).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period, min_periods=1).mean()
    rs = gain / (loss + 1e-10)
    return 100 - (100 / (1 + rs))


def calc_macd(series, fast=12, slow=26, signal=9):
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd = ema_fast - ema_slow
    signal_line = macd.ewm(span=signal, adjust=False).mean()
    hist = macd - signal_line
    return macd, signal_line, hist


def calc_bollinger(series, window=20, num_std=2):
    ma = series.rolling(window=window, min_periods=1).mean()
    std = series.rolling(window=window, min_periods=1).std()
    upper = ma + num_std * std
    lower = ma - num_std * std
    return upper, ma, lower


# ============ 特征工程 ============


def build_features(df):
    """为单只股票构建ML特征"""
    df = df.copy().sort_values("日期").reset_index(drop=True)

    close = df["收盘"].astype(float)
    high = df["最高"].astype(float)
    low = df["最低"].astype(float)
    opn = df["开盘"].astype(float)
    vol = df["成交量"].astype(float)

    # 均线
    df["MA3"] = calc_ma(close, 3)
    df["MA5"] = calc_ma(close, 5)
    df["MA10"] = calc_ma(close, 10)
    df["MA20"] = calc_ma(close, 20)

    # 均线偏离度
    df["MA5_bias"] = (close - df["MA5"]) / df["MA5"] * 100
    df["MA10_bias"] = (close - df["MA10"]) / df["MA10"] * 100
    df["MA20_bias"] = (close - df["MA20"]) / df["MA20"] * 100

    # 均线多头排列信号
    df["MA_trend"] = ((df["MA5"] > df["MA10"]) & (df["MA10"] > df["MA20"])).astype(int)

    # RSI
    df["RSI14"] = calc_rsi(close, 14)
    df["RSI6"] = calc_rsi(close, 6)

    # MACD
    macd, signal, hist = calc_macd(close)
    df["MACD"] = macd
    df["MACD_signal"] = signal
    df["MACD_hist"] = hist

    # 布林带
    bb_upper, bb_mid, bb_lower = calc_bollinger(close)
    df["BB_pos"] = (close - bb_lower) / (bb_upper - bb_lower + 1e-10)

    # 涨跌幅
    df["pct_1d"] = close.pct_change(1) * 100
    df["pct_3d"] = close.pct_change(3) * 100
    df["pct_5d"] = close.pct_change(5) * 100

    # 成交量变化
    df["vol_ma5"] = calc_ma(vol, 5)
    df["vol_ratio"] = vol / (df["vol_ma5"] + 1)

    # 振幅
    df["amplitude"] = (high - low) / close * 100

    # 上下影线
    df["upper_shadow"] = (high - np.maximum(close, opn)) / (high - low + 1e-10)
    df["lower_shadow"] = (np.minimum(close, opn) - low) / (high - low + 1e-10)

    # 波动率(5日)
    df["volatility5"] = close.pct_change().rolling(5, min_periods=2).std() * 100

    # 动量
    df["momentum3"] = close / close.shift(3) - 1
    df["momentum5"] = close / close.shift(5) - 1

    # 标签：未来3日涨跌方向 (1=涨, 0=跌)
    df["future_3d_ret"] = close.shift(-3) / close - 1
    df["target_dir"] = (df["future_3d_ret"] > 0).astype(int)
    # 回归标签：未来3日收益率
    df["target_ret"] = df["future_3d_ret"] * 100

    return df


FEATURE_COLS = [
    "MA5_bias",
    "MA10_bias",
    "MA20_bias",
    "MA_trend",
    "RSI14",
    "RSI6",
    "MACD",
    "MACD_hist",
    "BB_pos",
    "pct_1d",
    "pct_3d",
    "pct_5d",
    "vol_ratio",
    "amplitude",
    "upper_shadow",
    "lower_shadow",
    "volatility5",
    "momentum3",
    "momentum5",
]


# ============ 模型训练与预测 ============


def train_and_predict_stock(df):
    """为单只股票训练模型并预测"""
    df = build_features(df)

    # 准备训练数据（去掉最后3天没有标签的数据作为训练集）
    train_df = df.dropna(subset=["target_dir", "target_ret"])
    available_features = [f for f in FEATURE_COLS if f in train_df.columns]
    train_df = train_df.dropna(subset=available_features)

    if len(train_df) < 10:
        return None

    X_train = train_df[available_features].values
    y_dir = train_df["target_dir"].values
    y_ret = train_df["target_ret"].values

    # 最新一条数据用于预测
    latest = df.iloc[-1:]
    latest_features = latest[available_features]
    if latest_features.isnull().any(axis=1).values[0]:
        # 填充NaN
        latest_features = latest_features.fillna(0)

    X_latest = latest_features.values

    # 标准化
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_latest_scaled = scaler.transform(X_latest)

    result = {
        "最新价": float(df.iloc[-1]["收盘"]),
        "日期": str(df.iloc[-1]["日期"]),
    }

    # === 方向预测（分类）===
    try:
        # 随机森林
        rf = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42)
        rf.fit(X_train_scaled, y_dir)
        rf_prob = rf.predict_proba(X_latest_scaled)[0]
        rf_up_prob = rf_prob[1] if len(rf_prob) > 1 else 0.5

        # 梯度提升
        gb = GradientBoostingClassifier(n_estimators=80, max_depth=3, random_state=42)
        gb.fit(X_train_scaled, y_dir)
        gb_prob = gb.predict_proba(X_latest_scaled)[0]
        gb_up_prob = gb_prob[1] if len(gb_prob) > 1 else 0.5

        # 集成概率（加权平均）
        ensemble_up = rf_up_prob * 0.5 + gb_up_prob * 0.5
        result["上涨概率"] = round(float(ensemble_up) * 100, 1)
        result["方向"] = "看涨" if ensemble_up > 0.5 else "看跌"

        # 交叉验证评分
        try:
            cv_scores = cross_val_score(
                rf,
                X_train_scaled,
                y_dir,
                cv=min(5, len(y_dir) // 3),
                scoring="accuracy",
            )
            result["模型准确率"] = round(float(cv_scores.mean()) * 100, 1)
        except Exception:
            result["模型准确率"] = 50.0

    except Exception:
        result["上涨概率"] = 50.0
        result["方向"] = "不确定"
        result["模型准确率"] = 50.0

    # === 价格预测（回归）===
    try:
        ridge = Ridge(alpha=1.0)
        ridge.fit(X_train_scaled, y_ret)
        pred_ret = float(ridge.predict(X_latest_scaled)[0])

        lr = LinearRegression()
        lr.fit(X_train_scaled, y_ret)
        pred_ret_lr = float(lr.predict(X_latest_scaled)[0])

        avg_ret = (pred_ret + pred_ret_lr) / 2
        current_price = float(df.iloc[-1]["收盘"])
        pred_price = current_price * (1 + avg_ret / 100)

        # 预测区间（基于历史波动率）
        vol = float(df.iloc[-1].get("volatility5", 2) or 2)
        price_high = current_price * (1 + (avg_ret + vol * 1.5) / 100)
        price_low = current_price * (1 + (avg_ret - vol * 1.5) / 100)

        result["预测收益率"] = round(avg_ret, 2)
        result["预测价格"] = round(pred_price, 2)
        result["价格上限"] = round(price_high, 2)
        result["价格下限"] = round(price_low, 2)

    except Exception:
        result["预测收益率"] = 0
        result["预测价格"] = float(df.iloc[-1]["收盘"])
        result["价格上限"] = float(df.iloc[-1]["收盘"])
        result["价格下限"] = float(df.iloc[-1]["收盘"])

    # === 特征重要性 ===
    try:
        importances = rf.feature_importances_
        top_idx = np.argsort(importances)[-3:][::-1]
        result["关键因子"] = [available_features[i] for i in top_idx]
    except Exception:
        result["关键因子"] = []

    # === 信号强度 ===
    up_prob = result["上涨概率"]
    if up_prob >= 70:
        result["信号"] = "强烈看涨 🔴🔴🔴"
        result["信号级别"] = 3
    elif up_prob >= 60:
        result["信号"] = "偏多 🔴🔴"
        result["信号级别"] = 2
    elif up_prob >= 55:
        result["信号"] = "微偏多 🔴"
        result["信号级别"] = 1
    elif up_prob >= 45:
        result["信号"] = "中性 ⚪"
        result["信号级别"] = 0
    elif up_prob >= 40:
        result["信号"] = "微偏空 🟢"
        result["信号级别"] = -1
    elif up_prob >= 30:
        result["信号"] = "偏空 🟢🟢"
        result["信号级别"] = -2
    else:
        result["信号"] = "强烈看跌 🟢🟢🟢"
        result["信号级别"] = -3

    return result


# ============ 主函数 ============


def run_prediction():
    """运行ML预测"""
    print("\n" + "=" * 60)
    print(f"🤖 开始机器学习预测 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    today = datetime.now().strftime("%Y%m%d")

    # 加载历史数据
    history_path = os.path.join(DATA_DIR, f"history_{today}.csv")
    if not os.path.exists(history_path):
        print(f"  ❌ 未找到历史数据: {history_path}")
        return None

    df_all = pd.read_csv(history_path, encoding="utf-8-sig")
    print(f"  📂 加载历史数据: {len(df_all)} 条")

    # 获取所有股票代码
    all_stocks = {}
    for group in STOCK_GROUPS.values():
        all_stocks.update(group)

    print(f"\n🔬 训练模型并预测 ({len(all_stocks)} 只股票)...")

    predictions = {}
    for code, name in all_stocks.items():
        stock_df = df_all[df_all["代码"].astype(str).str.zfill(6) == str(code).zfill(6)]
        if len(stock_df) < 10:
            print(f"  [{code}] {name} - 数据不足，跳过")
            continue

        result = train_and_predict_stock(stock_df)
        if result:
            result["名称"] = name
            result["代码"] = code
            predictions[code] = result
            signal = result["信号"]
            prob = result["上涨概率"]
            print(f"  [{code}] {name}: {signal} (上涨概率 {prob}%)")

    # 汇总统计
    if predictions:
        bullish = sum(1 for p in predictions.values() if p["上涨概率"] > 55)
        bearish = sum(1 for p in predictions.values() if p["上涨概率"] < 45)
        neutral = len(predictions) - bullish - bearish

        # 按板块汇总
        sector_predictions = {}
        for sector_name, stocks in STOCK_GROUPS.items():
            sector_preds = []
            for code in stocks:
                if code in predictions:
                    sector_preds.append(predictions[code])
            if sector_preds:
                avg_prob = np.mean([p["上涨概率"] for p in sector_preds])
                avg_ret = np.mean([p["预测收益率"] for p in sector_preds])
                sector_predictions[sector_name] = {
                    "平均上涨概率": round(float(avg_prob), 1),
                    "平均预测收益率": round(float(avg_ret), 2),
                    "看涨数": sum(1 for p in sector_preds if p["上涨概率"] > 55),
                    "看跌数": sum(1 for p in sector_preds if p["上涨概率"] < 45),
                    "个股数": len(sector_preds),
                }

        # 排行榜
        sorted_by_prob = sorted(
            predictions.values(), key=lambda x: x["上涨概率"], reverse=True
        )

        save_data = {
            "预测日期": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "预测周期": "未来3个交易日",
            "汇总": {
                "总股票数": len(predictions),
                "看涨": bullish,
                "看跌": bearish,
                "中性": neutral,
                "整体情绪": (
                    "偏多"
                    if bullish > bearish
                    else ("偏空" if bearish > bullish else "中性")
                ),
            },
            "板块预测": sector_predictions,
            "看涨Top5": [
                {
                    "代码": p["代码"],
                    "名称": p["名称"],
                    "上涨概率": p["上涨概率"],
                    "预测收益率": p["预测收益率"],
                    "信号": p["信号"],
                }
                for p in sorted_by_prob[:5]
            ],
            "看跌Top5": [
                {
                    "代码": p["代码"],
                    "名称": p["名称"],
                    "上涨概率": p["上涨概率"],
                    "预测收益率": p["预测收益率"],
                    "信号": p["信号"],
                }
                for p in sorted_by_prob[-5:][::-1]
            ],
            "个股预测": predictions,
        }

        # 保存
        path = os.path.join(DATA_DIR, f"predictions_{today}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2)
        print(f"\n💾 预测结果已保存: {path}")

        print(f"\n📊 预测汇总:")
        print(f"  看涨 {bullish} 只 | 看跌 {bearish} 只 | 中性 {neutral} 只")
        print(f"  整体情绪: {save_data['汇总']['整体情绪']}")
        print(f"\n🔥 最看涨 Top3:")
        for p in sorted_by_prob[:3]:
            print(
                f"  {p['名称']}: {p['信号']} (上涨概率 {p['上涨概率']}%, 预测收益 {p['预测收益率']}%)"
            )
        print(f"\n❄️ 最看跌 Top3:")
        for p in sorted_by_prob[-3:]:
            print(
                f"  {p['名称']}: {p['信号']} (上涨概率 {p['上涨概率']}%, 预测收益 {p['预测收益率']}%)"
            )

        print(f"\n✅ 机器学习预测完成！")
        return save_data

    print("  ❌ 无预测结果")
    return None


if __name__ == "__main__":
    run_prediction()
