"""
💰 资金流向采集
采集个股实时资金流向数据（主力净流入、大单、超大单等）
"""

import os
import re
import pandas as pd
from datetime import datetime
from config import STOCK_GROUPS, DATA_DIR, get_all_stocks


def parse_chinese_amount(s):
    """将中文金额字符串解析为数值（元）"""
    if pd.isna(s) or s == "0.00":
        return 0.0
    s = str(s).strip()
    negative = -1 if s.startswith("-") else 1
    s = s.lstrip("-")
    match = re.match(r"^([\d,.]+)(.*)$", s)
    if not match:
        return 0.0
    num_str, unit = match.groups()
    num = float(num_str.replace(",", ""))
    unit = unit.strip()
    if unit == "亿":
        num *= 1e8
    elif unit == "万":
        num *= 1e4
    elif unit == "千":
        num *= 1e3
    return negative * num


def parse_pct(s):
    """解析百分比字符串"""
    if pd.isna(s):
        return 0.0
    s = str(s).strip().replace("%", "")
    try:
        return float(s)
    except Exception:
        return 0.0


def collect_fund_flow():
    """采集全市场资金流向，筛选出跟踪的股票"""
    print("\n💰 采集资金流向数据...")
    try:
        import akshare as ak

        df = ak.stock_fund_flow_individual()
        print(f"  📊 全市场数据: {len(df)} 条")

        # 统一代码格式
        df["股票代码"] = df["股票代码"].astype(str).str.zfill(6)

        # 解析金额
        df["净流入"] = df["净额"].apply(parse_chinese_amount)
        df["流入资金"] = df["流入资金"].apply(parse_chinese_amount)
        df["流出资金"] = df["流出资金"].apply(parse_chinese_amount)
        df["成交额"] = df["成交额"].apply(parse_chinese_amount)
        df["最新价"] = pd.to_numeric(df["最新价"], errors="coerce")
        df["涨跌幅"] = df["涨跌幅"].apply(parse_pct)

        # 筛选跟踪的股票
        all_codes = set(get_all_stocks().keys())
        tracked = df[df["股票代码"].isin(all_codes)].copy()
        print(f"  ✅ 匹配到 {len(tracked)} 只跟踪股票")

        # 重命名并保存
        tracked = tracked.rename(
            columns={
                "股票代码": "代码",
                "股票简称": "名称",
            }
        )
        today = datetime.now().strftime("%Y%m%d")
        path = os.path.join(DATA_DIR, f"fundflow_{today}.csv")
        tracked.to_csv(path, index=False, encoding="utf-8-sig")
        print(f"  💾 已保存: {path}")
        return tracked

    except Exception as e:
        print(f"  ❌ 资金流向采集失败: {e}")
        return pd.DataFrame()


def run_fundflow_collection():
    """执行资金流向采集入口"""
    print("\n" + "=" * 60)
    print(f"💰 资金流向采集 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    return collect_fund_flow()


if __name__ == "__main__":
    run_fundflow_collection()
