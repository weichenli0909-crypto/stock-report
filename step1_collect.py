"""
📥 第一步：数据采集
通过新浪财经 API 获取个股的实时行情和历史数据
"""

import os
import json
import time
import subprocess
import pandas as pd
from datetime import datetime, timedelta
from config import get_all_stocks, STOCK_GROUPS, DATA_DIR


def ensure_dirs():
    """确保数据目录存在"""
    os.makedirs(DATA_DIR, exist_ok=True)


def curl_get_text(url, referer="https://finance.sina.com.cn"):
    """使用 curl 发起 GET 请求，返回文本"""
    try:
        result = subprocess.run(
            [
                "curl",
                "-s",
                "-m",
                "15",
                "-H",
                f"Referer: {referer}",
                "-H",
                "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
                url,
            ],
            capture_output=True,
            timeout=20,
        )
        if result.returncode == 0 and result.stdout:
            # 新浪接口返回 GBK 编码
            try:
                return result.stdout.decode("gbk")
            except UnicodeDecodeError:
                return result.stdout.decode("utf-8", errors="replace")
    except Exception as e:
        print(f"    请求失败: {e}")
    return ""


def curl_get_json(url, referer="https://finance.sina.com.cn"):
    """使用 curl 发起 GET 请求，返回 JSON"""
    try:
        result = subprocess.run(
            [
                "curl",
                "-s",
                "-m",
                "15",
                "-H",
                f"Referer: {referer}",
                "-H",
                "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
                url,
            ],
            capture_output=True,
            text=True,
            timeout=20,
        )
        if result.returncode == 0 and result.stdout:
            return json.loads(result.stdout)
    except Exception as e:
        print(f"    请求失败: {e}")
    return None


def get_sina_code(code):
    """将股票代码转为新浪格式：sh600498 / sz300308"""
    if code.startswith(("6", "9")):
        return f"sh{code}"
    else:
        return f"sz{code}"


def collect_realtime_quotes():
    """
    采集所有关注个股的实时行情
    使用新浪实时行情接口
    """
    print("📥 正在采集实时行情数据...")

    all_stocks = get_all_stocks()

    # 构建批量查询代码列表
    sina_codes = ",".join(get_sina_code(code) for code in all_stocks.keys())
    url = f"https://hq.sinajs.cn/list={sina_codes}"

    text = curl_get_text(url)
    if not text:
        print("  ⚠️ 获取实时行情失败")
        return pd.DataFrame()

    # 解析新浪实时行情数据
    # 格式: var hq_str_sz300308="名称,今开,昨收,最新价,最高,最低,买一,卖一,成交量,成交额,..."
    rows = []
    for line in text.strip().split("\n"):
        line = line.strip()
        if not line or '="' not in line:
            continue
        try:
            # 提取代码
            var_part = line.split("=")[0]
            code_part = var_part.replace("var hq_str_", "").strip()
            code6 = code_part[2:]  # 去掉 sh/sz 前缀

            # 提取数据
            data_str = line.split('"')[1]
            if not data_str:
                continue
            fields = data_str.split(",")
            if len(fields) < 32:
                continue

            name = fields[0]
            # 如果名称是乱码，用配置里的名称
            if not name or any(ord(c) > 0xFFFF for c in name):
                name = all_stocks.get(code6, code6)

            rows.append(
                {
                    "代码": code6,
                    "名称": name,
                    "今开": float(fields[1]) if fields[1] else 0,
                    "昨收": float(fields[2]) if fields[2] else 0,
                    "最新价": float(fields[3]) if fields[3] else 0,
                    "最高": float(fields[4]) if fields[4] else 0,
                    "最低": float(fields[5]) if fields[5] else 0,
                    "成交量": int(fields[8]) if fields[8] else 0,
                    "成交额": float(fields[9]) if fields[9] else 0,
                }
            )
        except (IndexError, ValueError) as e:
            continue

    if not rows:
        print("  ⚠️ 解析实时行情失败")
        return pd.DataFrame()

    df = pd.DataFrame(rows)

    # 计算涨跌幅和换手率
    df["涨跌幅"] = ((df["最新价"] - df["昨收"]) / df["昨收"] * 100).round(2)
    df["涨跌额"] = (df["最新价"] - df["昨收"]).round(2)
    df["振幅"] = ((df["最高"] - df["最低"]) / df["昨收"] * 100).round(2)

    print(f"  ✅ 成功获取 {len(df)} 只股票的实时行情")
    return df


def collect_stock_history(stock_code, days=180):
    """
    采集单只股票的近期历史数据
    使用新浪 K 线数据接口
    """
    sina_code = get_sina_code(stock_code)
    url = (
        f"https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/"
        f"CN_MarketData.getKLineData?symbol={sina_code}&scale=240&ma=no&datalen={days}"
    )

    data = curl_get_json(url)
    if not data or not isinstance(data, list):
        return pd.DataFrame()

    rows = []
    for item in data:
        rows.append(
            {
                "日期": item.get("day", ""),
                "开盘": float(item.get("open", 0)),
                "收盘": float(item.get("close", 0)),
                "最高": float(item.get("high", 0)),
                "最低": float(item.get("low", 0)),
                "成交量": int(item.get("volume", 0)),
            }
        )

    return pd.DataFrame(rows)


def collect_all_history(days=180):
    """采集所有关注个股的历史数据"""
    print(f"📥 正在采集近 {days} 天历史数据...")

    all_stocks = get_all_stocks()
    all_history = []

    for i, (code, name) in enumerate(all_stocks.items()):
        print(f"  [{i+1}/{len(all_stocks)}] 获取 {name}({code})...", end="")
        df = collect_stock_history(code, days)
        if not df.empty:
            df["代码"] = code
            df["名称"] = name
            all_history.append(df)
            print(f" ✓ {len(df)}条")
        else:
            print(" ✗ 无数据")
        time.sleep(0.3)  # 避免请求过快

    if all_history:
        result = pd.concat(all_history, ignore_index=True)
        print(
            f"  ✅ 成功获取 {len(all_stocks)} 只股票的历史数据，共 {len(result)} 条记录"
        )
        return result
    else:
        print("  ❌ 未获取到任何历史数据")
        return pd.DataFrame()


def build_sector_from_realtime(df_realtime):
    """
    根据实时行情数据，计算各板块表现
    （替代板块资金流向接口）
    """
    print("📥 正在计算板块表现...")

    if df_realtime.empty:
        return pd.DataFrame()

    rows = []
    for sector_name, stocks in STOCK_GROUPS.items():
        sector_codes = list(stocks.keys())
        sector_df = df_realtime[df_realtime["代码"].isin(sector_codes)]
        if not sector_df.empty:
            rows.append(
                {
                    "板块": sector_name,
                    "平均涨跌幅": round(float(sector_df["涨跌幅"].mean()), 2),
                    "成交额(亿)": round(float(sector_df["成交额"].sum() / 1e8), 2),
                    "上涨数": int((sector_df["涨跌幅"] > 0).sum()),
                    "下跌数": int((sector_df["涨跌幅"] < 0).sum()),
                    "个股数": len(sector_df),
                    "最大涨幅": round(float(sector_df["涨跌幅"].max()), 2),
                    "最大跌幅": round(float(sector_df["涨跌幅"].min()), 2),
                }
            )

    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values("平均涨跌幅", ascending=False).reset_index(drop=True)
    print(f"  ✅ 成功计算 {len(df)} 个板块的表现")
    return df


def run_collection():
    """执行完整的数据采集流程"""
    ensure_dirs()
    today = datetime.now().strftime("%Y%m%d")

    print("=" * 60)
    print(f"📥 开始数据采集 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # 1. 采集实时行情
    df_realtime = collect_realtime_quotes()
    if not df_realtime.empty:
        path = os.path.join(DATA_DIR, f"realtime_{today}.csv")
        df_realtime.to_csv(path, index=False, encoding="utf-8-sig")
        print(f"  💾 实时行情已保存: {path}")

    # 2. 采集历史数据
    df_history = collect_all_history(days=180)
    if not df_history.empty:
        path = os.path.join(DATA_DIR, f"history_{today}.csv")
        df_history.to_csv(path, index=False, encoding="utf-8-sig")
        print(f"  💾 历史数据已保存: {path}")

    # 3. 从实时数据计算板块表现
    df_sector = build_sector_from_realtime(df_realtime)
    if not df_sector.empty:
        path = os.path.join(DATA_DIR, f"sector_funds_{today}.csv")
        df_sector.to_csv(path, index=False, encoding="utf-8-sig")
        print(f"  💾 板块表现已保存: {path}")

    print("\n✅ 数据采集完成！")
    return df_realtime, df_history, df_sector


if __name__ == "__main__":
    run_collection()
