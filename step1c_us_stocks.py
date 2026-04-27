"""
🇺🇸 美股关联标的数据采集
采集美股前一交易日行情，并匹配A股关联关系
"""

import os
import json
import subprocess
import re
import time
from datetime import datetime
from config import US_STOCKS, DATA_DIR


def curl_get_text(url, referer="", encoding="utf-8"):
    try:
        cmd = [
            "curl",
            "-s",
            "-m",
            "15",
            "-L",
            "-H",
            "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        ]
        if referer:
            cmd += ["-H", f"Referer: {referer}"]
        cmd.append(url)
        result = subprocess.run(cmd, capture_output=True, timeout=20)
        if result.returncode == 0 and result.stdout:
            return result.stdout.decode(encoding, errors="replace")
    except Exception:
        pass
    return ""


def fetch_us_stock_sina(ticker):
    """从新浪获取美股行情 (前一交易日收盘数据)"""
    url = f"https://hq.sinajs.cn/list=gb_{ticker.lower()}"
    text = curl_get_text(url, referer="https://finance.sina.com.cn")
    if not text or "=" not in text:
        return None

    try:
        # 格式: var hq_str_gb_nvda="英伟达,xxx,xxx,..."
        data_str = text.split('"')[1]
        fields = data_str.split(",")
        if len(fields) < 15:
            return None

        return {
            "代码": ticker.upper(),
            "中文名": fields[0],
            "最新价": float(fields[1]) if fields[1] else 0,
            "涨跌额": float(fields[2]) if fields[2] else 0,
            "涨跌幅": (
                float(fields[2]) / float(fields[26]) * 100
                if fields[26] and float(fields[26]) != 0
                else 0
            ),
            "今开": float(fields[5]) if fields[5] else 0,
            "最高": float(fields[6]) if fields[6] else 0,
            "最低": float(fields[7]) if fields[7] else 0,
            "昨收": float(fields[26]) if fields[26] else 0,
            "成交量": fields[10],
            "市值(亿美元)": (
                round(float(fields[12]) / 100000000, 1) if fields[12] else 0
            ),
            "52周最高": float(fields[8]) if fields[8] else 0,
            "52周最低": float(fields[9]) if fields[9] else 0,
            "更新时间": fields[3] if len(fields) > 3 else "",
        }
    except (IndexError, ValueError, ZeroDivisionError):
        return None


def collect_us_stocks():
    """采集所有美股关联标的行情"""
    print("🇺🇸 正在采集美股关联标的行情...")

    results = {}
    for ticker, info in US_STOCKS.items():
        print(f"  [{ticker}] {info['名称']}...", end="")
        quote = fetch_us_stock_sina(ticker)
        if quote:
            quote["简介"] = info["简介"]
            quote["关联A股"] = info["关联A股"]
            results[ticker] = quote
            change = quote["涨跌幅"]
            emoji = "🔴" if change > 0 else ("🟢" if change < 0 else "⚪")
            print(f" ✓ ${quote['最新价']:.2f} {emoji}{change:+.2f}%")
        else:
            print(" ✗ 获取失败")
            # 存一个空壳保留关联信息
            results[ticker] = {
                "代码": ticker,
                "中文名": info["名称"],
                "简介": info["简介"],
                "关联A股": info["关联A股"],
                "最新价": 0,
                "涨跌幅": 0,
            }
        time.sleep(0.3)

    return results


def run_us_stock_collection():
    """执行美股数据采集"""
    os.makedirs(DATA_DIR, exist_ok=True)

    print("\n" + "=" * 60)
    print(f"🇺🇸 开始美股关联标的采集 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    results = collect_us_stocks()

    # 保存
    today = datetime.now().strftime("%Y%m%d")
    path = os.path.join(DATA_DIR, f"us_stocks_{today}.json")
    save_data = {
        "采集时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "美股行情": results,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(save_data, f, ensure_ascii=False, indent=2)
    print(f"\n💾 美股数据已保存: {path}")

    # 概览
    up = sum(1 for v in results.values() if v.get("涨跌幅", 0) > 0)
    down = sum(1 for v in results.values() if v.get("涨跌幅", 0) < 0)
    print(f"\n📊 美股概览: 上涨 {up} 只 | 下跌 {down} 只")

    print("\n✅ 美股采集完成！")
    return save_data


if __name__ == "__main__":
    run_us_stock_collection()
