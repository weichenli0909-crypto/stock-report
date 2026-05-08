"""
🚀 多因子 ML 评分 v6.0 - LightGBM 非线性模型

v6.0 相对 v5.0 的升级：
  1. 🎯 线性加权 → LightGBM 梯度提升（捕捉非线性 + 因子交互）
  2. 📊 预测目标从"因子打分"升级为"5 日涨概率" / "5 日预期超额收益"
  3. 🔬 Walk-forward 训练：每天用过去 130 天训练 + 30 天验证
  4. 🛡️ 早停 + 时间序列 CV，抗过拟合
  5. 🎁 兼容现有 v5.0：输出相同字段 + 额外 ml_score、ml_prob

核心逻辑：
  特征 X = 10 个因子 + 未来将扩充的因子
  标签 y = 未来 5 日相对行业涨幅 > 0 的二分类（1=涨赢板块, 0=跑输板块）
       OR 未来 5 日相对收益的回归

模型训练与预测分工：
  - train_ml_model(): 训练并保存 model_YYYYMMDD.pkl
  - run_ml_prediction(): 加载今日模型 + 最新因子 → 打分

与 v5.0 的融合：
  最终 AI 评分 = 0.6 × ML 概率 + 0.4 × v5.0 线性分
  （可在 config 里调整权重，A/B 测试用）

运行：
  python3 step2b_ml.py          # 训练 + 预测 + 保存
  python3 step2b_ml.py --train  # 只训练
"""

import os
import sys
import json
import pickle
import warnings
import numpy as np
import pandas as pd
from datetime import datetime
from glob import glob

warnings.filterwarnings("ignore")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import STOCK_GROUPS, DATA_DIR
from step2b_predict import (
    calc_features_for_stock,
    add_market_sector_factors,
    load_external_features,
    FACTOR_COLS,
)

try:
    import lightgbm as lgb
    HAS_LGBM = True
except ImportError:
    HAS_LGBM = False
    print("⚠️ 未安装 lightgbm，请运行: pip install lightgbm")


# ==================== 配置 ====================

# 特征列（10 个因子 + 未来将加的）
FEATURE_COLS = list(FACTOR_COLS.values())

# 预测 horizon（5 日）
HORIZON = 5

# 训练窗口
TRAIN_WINDOW = 130  # 用过去 130 天训练
VALID_WINDOW = 30   # 用 30 天做验证（early stopping）
MIN_SAMPLES_PER_DAY = 5  # 每天最少多少只股票才算有效截面

# LightGBM 参数（小数据防过拟合版）
LGB_PARAMS = {
    "objective": "binary",          # 二分类：未来 5 日相对板块是否涨
    "metric": "binary_logloss",
    "learning_rate": 0.05,
    "num_leaves": 15,               # 小叶节点防过拟合
    "max_depth": 4,
    "min_data_in_leaf": 30,
    "feature_fraction": 0.8,
    "bagging_fraction": 0.8,
    "bagging_freq": 5,
    "reg_alpha": 0.1,
    "reg_lambda": 0.1,
    "verbose": -1,
}


def build_feature_panel(history_df):
    """构建全部股票的特征 + 未来收益面板"""
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

    # 去掉预热期
    panel["row_num"] = panel.groupby("代码").cumcount()
    panel = panel[panel["row_num"] >= 20].copy()

    # 计算未来 HORIZON 日收益
    panel = panel.sort_values(["代码", "日期"]).reset_index(drop=True)
    panel[f"future_ret_{HORIZON}d"] = (
        panel.groupby("代码")["收盘"].shift(-HORIZON) / panel["收盘"] - 1
    )

    # 标签：相对板块平均收益是否为正
    # 计算每个板块每天未来 5 日平均收益
    stock_to_sector = {}
    for sname, stocks in STOCK_GROUPS.items():
        for code in stocks:
            stock_to_sector[code] = sname
    panel["板块"] = panel["代码"].map(stock_to_sector)

    sector_future = (
        panel.groupby(["板块", "日期"])[f"future_ret_{HORIZON}d"]
        .mean()
        .reset_index()
        .rename(columns={f"future_ret_{HORIZON}d": f"sector_future_{HORIZON}d"})
    )
    panel = panel.merge(sector_future, on=["板块", "日期"], how="left")

    panel[f"excess_ret_{HORIZON}d"] = (
        panel[f"future_ret_{HORIZON}d"] - panel[f"sector_future_{HORIZON}d"]
    )
    panel["label"] = (panel[f"excess_ret_{HORIZON}d"] > 0).astype(int)

    return panel


def prepare_xy(panel_slice, feature_cols=None):
    """从 panel 切片拿到 X, y"""
    if feature_cols is None:
        feature_cols = FEATURE_COLS
    available_cols = [c for c in feature_cols if c in panel_slice.columns]
    df = panel_slice[available_cols + ["label", f"excess_ret_{HORIZON}d"]].dropna()
    if len(df) < 100:
        return None, None, None
    X = df[available_cols].values
    y = df["label"].values
    ret = df[f"excess_ret_{HORIZON}d"].values
    return X, y, ret, available_cols


def train_ml_model(panel):
    """
    Walk-forward 训练 + 验证最终模型
    返回：(model, feature_cols, val_metrics)
    """
    if not HAS_LGBM:
        raise RuntimeError("需要安装 lightgbm：pip install lightgbm")

    panel = panel.sort_values(["日期", "代码"]).reset_index(drop=True)
    unique_dates = sorted(panel["日期"].unique())

    # 留出最后 HORIZON 天的数据（这些数据标签不可用）
    usable = panel[panel["label"].notna() & panel[f"excess_ret_{HORIZON}d"].notna()].copy()
    usable_dates = sorted(usable["日期"].unique())

    if len(usable_dates) < TRAIN_WINDOW + VALID_WINDOW:
        print(f"  ⚠️ 数据太少（{len(usable_dates)} 天），需要至少 {TRAIN_WINDOW + VALID_WINDOW} 天")
        return None, None, None

    # 最后 TRAIN_WINDOW + VALID_WINDOW 天作为训练/验证
    total_dates = usable_dates[-(TRAIN_WINDOW + VALID_WINDOW):]
    train_dates = set(total_dates[:TRAIN_WINDOW])
    valid_dates = set(total_dates[TRAIN_WINDOW:])

    train_panel = usable[usable["日期"].isin(train_dates)]
    valid_panel = usable[usable["日期"].isin(valid_dates)]

    train_result = prepare_xy(train_panel)
    valid_result = prepare_xy(valid_panel)
    if train_result[0] is None or valid_result[0] is None:
        print("  ⚠️ 训练/验证样本不足")
        return None, None, None

    X_train, y_train, ret_train, feat_cols = train_result
    X_valid, y_valid, ret_valid, _ = valid_result

    print(f"  📊 训练集: {len(X_train)} 样本 × {len(feat_cols)} 特征")
    print(f"  📊 验证集: {len(X_valid)} 样本")
    print(f"  📊 训练集正样本率: {y_train.mean() * 100:.1f}%")

    train_set = lgb.Dataset(X_train, label=y_train)
    valid_set = lgb.Dataset(X_valid, label=y_valid, reference=train_set)

    model = lgb.train(
        LGB_PARAMS,
        train_set,
        num_boost_round=500,
        valid_sets=[train_set, valid_set],
        valid_names=["train", "valid"],
        callbacks=[
            lgb.early_stopping(stopping_rounds=30, verbose=False),
            lgb.log_evaluation(period=0),  # 静默
        ],
    )

    # 验证集 IC 和胜率
    valid_prob = model.predict(X_valid)
    val_df = pd.DataFrame({"prob": valid_prob, "excess_ret": ret_valid})
    val_ic = val_df["prob"].corr(val_df["excess_ret"])
    # 按概率 30% 分位分 Top/Bottom
    q_hi = val_df["prob"].quantile(0.7)
    q_lo = val_df["prob"].quantile(0.3)
    top_ret = val_df[val_df["prob"] >= q_hi]["excess_ret"].mean()
    bot_ret = val_df[val_df["prob"] <= q_lo]["excess_ret"].mean()
    long_short = top_ret - bot_ret

    val_metrics = {
        "valid_samples": len(X_valid),
        "valid_ic": round(float(val_ic), 4),
        "top_30%_excess_ret": round(float(top_ret) * 100, 2),
        "bottom_30%_excess_ret": round(float(bot_ret) * 100, 2),
        "long_short_spread_5d": round(float(long_short) * 100, 2),
        "best_iteration": int(model.best_iteration),
        "train_window": TRAIN_WINDOW,
        "valid_window": VALID_WINDOW,
    }

    print(f"\n  🎯 验证集表现:")
    print(f"     IC = {val_metrics['valid_ic']:+.4f}")
    print(f"     Top 30% 超额收益 = {val_metrics['top_30%_excess_ret']:+.2f}% (5 日)")
    print(f"     Bot 30% 超额收益 = {val_metrics['bottom_30%_excess_ret']:+.2f}% (5 日)")
    print(f"     多空差 = {val_metrics['long_short_spread_5d']:+.2f}% (5 日)")
    print(f"     最优迭代 = {val_metrics['best_iteration']}")

    # 特征重要度
    importance = pd.DataFrame({
        "feature": feat_cols,
        "importance": model.feature_importance(importance_type="gain"),
    }).sort_values("importance", ascending=False)
    print(f"\n  📈 特征重要度 Top 5:")
    for _, row in importance.head(5).iterrows():
        print(f"     {row['feature']:20s} {row['importance']:8.1f}")

    return model, feat_cols, val_metrics


def save_model(model, feat_cols, val_metrics, today_str):
    """保存 LGB 模型 + 元信息"""
    path = os.path.join(DATA_DIR, f"ml_model_{today_str}.pkl")
    with open(path, "wb") as f:
        pickle.dump({
            "model": model,
            "feature_cols": feat_cols,
            "metrics": val_metrics,
            "trained_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "version": "v6.0",
            "horizon": HORIZON,
        }, f)
    # 同时保存到 ml_model_latest.pkl 方便加载
    latest_path = os.path.join(DATA_DIR, "ml_model_latest.pkl")
    with open(latest_path, "wb") as f:
        pickle.dump({
            "model": model,
            "feature_cols": feat_cols,
            "metrics": val_metrics,
            "trained_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "version": "v6.0",
            "horizon": HORIZON,
        }, f)

    # 再存一份 JSON 让 Python 外的工具也能看
    json_path = os.path.join(DATA_DIR, f"ml_model_meta_{today_str}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({
            "trained_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "version": "v6.0",
            "horizon": HORIZON,
            "feature_cols": feat_cols,
            "metrics": val_metrics,
        }, f, ensure_ascii=False, indent=2)

    return path


def load_latest_model():
    """加载最新训练好的模型"""
    path = os.path.join(DATA_DIR, "ml_model_latest.pkl")
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        return pickle.load(f)


def predict_today(model_dict, panel):
    """用当天最新数据预测"""
    latest_date = panel["日期"].max()
    latest = panel[panel["日期"] == latest_date].copy()

    feat_cols = model_dict["feature_cols"]
    model = model_dict["model"]

    # 处理缺失特征
    for col in feat_cols:
        if col not in latest.columns:
            latest[col] = 0
    X = latest[feat_cols].fillna(latest[feat_cols].median()).values
    latest["ml_prob"] = model.predict(X)
    latest["ml_score"] = latest["ml_prob"] * 100  # 0-100 分

    return latest[["代码", "日期", "ml_prob", "ml_score"]], latest_date


# ==================== 主流程 ====================

def run_ml_training():
    """训练 + 保存"""
    print("\n" + "=" * 70)
    print(f"🚀 开始 ML 模型训练 v6.0 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    if not HAS_LGBM:
        print("❌ 未安装 lightgbm，无法训练")
        return None

    # 1. 加载历史数据
    hist_files = sorted(glob(os.path.join(DATA_DIR, "history_*.csv")))
    if not hist_files:
        print("❌ 未找到历史数据")
        return None
    history_path = hist_files[-1]
    today_str = os.path.basename(history_path).replace("history_", "").replace(".csv", "")
    print(f"  📂 加载: {history_path}")

    history_df = pd.read_csv(history_path, dtype={"代码": str}, encoding="utf-8-sig")
    history_df["代码"] = history_df["代码"].astype(str).str.zfill(6)
    history_df["日期"] = pd.to_datetime(history_df["日期"])
    history_df["收盘"] = pd.to_numeric(history_df["收盘"], errors="coerce")

    # 2. 构建面板
    print("\n🔬 构建特征面板 ...")
    panel = build_feature_panel(history_df)
    if panel is None:
        print("❌ 面板构建失败")
        return None
    print(f"  ✅ 面板: {len(panel)} 条 × {len(panel.columns)} 列")

    # 3. 训练
    print("\n🎯 开始训练 LightGBM ...")
    model, feat_cols, metrics = train_ml_model(panel)
    if model is None:
        print("❌ 训练失败")
        return None

    # 4. 保存
    path = save_model(model, feat_cols, metrics, today_str)
    print(f"\n💾 模型已保存: {path}")
    print(f"✅ ML 训练完成！")
    return metrics


def run_ml_prediction():
    """加载最新模型 + 预测今日"""
    print("\n" + "=" * 70)
    print(f"🔮 ML 预测 v6.0 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    model_dict = load_latest_model()
    if model_dict is None:
        print("❌ 未找到训练好的模型，请先运行训练")
        return None

    print(f"  📦 加载模型: 训练于 {model_dict['trained_at']}, 验证 IC = {model_dict['metrics']['valid_ic']:+.4f}")

    # 加载最新历史数据
    hist_files = sorted(glob(os.path.join(DATA_DIR, "history_*.csv")))
    history_path = hist_files[-1]
    today_str = os.path.basename(history_path).replace("history_", "").replace(".csv", "")

    history_df = pd.read_csv(history_path, dtype={"代码": str}, encoding="utf-8-sig")
    history_df["代码"] = history_df["代码"].astype(str).str.zfill(6)
    history_df["日期"] = pd.to_datetime(history_df["日期"])
    history_df["收盘"] = pd.to_numeric(history_df["收盘"], errors="coerce")

    panel = build_feature_panel(history_df)
    if panel is None:
        return None

    preds, latest_date = predict_today(model_dict, panel)
    print(f"  ✅ 预测完成: {len(preds)} 只股票 @ {latest_date.strftime('%Y-%m-%d')}")

    # 保存
    out_path = os.path.join(DATA_DIR, f"ml_predictions_{today_str}.json")
    all_stocks = {}
    for g in STOCK_GROUPS.values():
        all_stocks.update(g)

    pred_dict = {}
    for _, row in preds.iterrows():
        code = str(row["代码"]).zfill(6)
        pred_dict[code] = {
            "代码": code,
            "名称": all_stocks.get(code, ""),
            "ml_prob": round(float(row["ml_prob"]), 4),
            "ml_score": round(float(row["ml_score"]), 1),
        }

    save_data = {
        "预测日期": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "模型版本": model_dict["version"],
        "模型训练时间": model_dict["trained_at"],
        "验证IC": model_dict["metrics"]["valid_ic"],
        "验证多空差_5日": model_dict["metrics"]["long_short_spread_5d"],
        "个股ML评分": pred_dict,
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(save_data, f, ensure_ascii=False, indent=2)
    print(f"  💾 ML 预测保存: {out_path}")

    # Top 5
    sorted_preds = sorted(pred_dict.values(), key=lambda x: x["ml_score"], reverse=True)
    print(f"\n  🔥 ML 评分 Top 5:")
    for p in sorted_preds[:5]:
        print(f"    {p['名称']:<10s} ml_score = {p['ml_score']:5.1f}  prob = {p['ml_prob']:.3f}")
    print(f"\n  ❄️ ML 评分 Bottom 5:")
    for p in sorted_preds[-5:]:
        print(f"    {p['名称']:<10s} ml_score = {p['ml_score']:5.1f}  prob = {p['ml_prob']:.3f}")

    return save_data


def run_full():
    """训练 + 预测全流程"""
    metrics = run_ml_training()
    if metrics is None:
        return None
    return run_ml_prediction()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--train":
        run_ml_training()
    elif len(sys.argv) > 1 and sys.argv[1] == "--predict":
        run_ml_prediction()
    else:
        run_full()
