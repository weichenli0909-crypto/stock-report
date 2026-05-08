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


# ===== 大事件关键词检测 =====
EVENT_KEYWORDS = {
    "分红": ["dividend", "dividends", "payout", "distribution"],
    "财报": ["earnings", "quarterly results", "revenue", "profit", "EPS", "beat estimates", "miss estimates", "quarterly report", "Q1", "Q2", "Q3", "Q4"],
    "收购": ["acquire", "acquisition", "merger", "takeover", "buyout", "deal"],
    "建厂": ["factory", "plant", "manufacturing", "facility", "expand capacity", "new fab", "build"],
    "大单": ["contract", "order", "deal worth", "billion-dollar", "partnership", "supply agreement", "wins order"],
    "裁员": ["layoff", "lay off", "cut jobs", "restructuring", "workforce reduction"],
    "拆股": ["stock split", "split"],
    "回购": ["buyback", "repurchase", "share repurchase"],
    "上市/IPO": ["IPO", "initial public offering", "goes public", "listing"],
    "监管": ["SEC", "regulatory", "antitrust", "investigation", "lawsuit", "fine", "penalty"],
}


def detect_events(title, description=""):
    """检测新闻中的大事件标签"""
    text = (title + " " + description).lower()
    events = []
    for event_name, keywords in EVENT_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in text:
                events.append(event_name)
                break
    return events


def simple_translate(title, description=""):
    """简单的英文→中文翻译（基于关键词替换+摘要提取，免费无需API）"""
    # 常用财经词汇翻译映射
    trans_map = {
        "stock": "股票", "shares": "股份", "earnings": "财报/业绩",
        "revenue": "营收", "profit": "利润", "loss": "亏损",
        "beat estimates": "超预期", "miss estimates": "不及预期",
        "dividend": "分红", "buyback": "回购", "acquisition": "收购",
        "merger": "合并", "partnership": "合作", "contract": "合同",
        "quarterly": "季度", "annual": "年度",
        "growth": "增长", "decline": "下跌", "surge": "暴涨",
        "plunge": "暴跌", "rally": "上涨", "drop": "下跌",
        "AI": "人工智能", "chip": "芯片", "semiconductor": "半导体",
        "data center": "数据中心", "cloud": "云计算",
        "buy": "买入", "sell": "卖出", "hold": "持有",
        "upgrade": "上调评级", "downgrade": "下调评级",
        "target price": "目标价", "market cap": "市值",
        "investors": "投资者", "analyst": "分析师",
        "Nvidia": "英伟达", "Broadcom": "博通", "Microsoft": "微软",
        "Google": "谷歌", "Amazon": "亚马逊", "Meta": "Meta",
        "Apple": "苹果", "Tesla": "特斯拉", "AMD": "AMD",
        "Cisco": "思科", "Arista": "Arista",
    }
    # 生成简易中文摘要
    cn_summary = description[:100] if description else title[:80]
    # 对关键词做标注
    for en, cn in trans_map.items():
        if en.lower() in title.lower() or en.lower() in description.lower():
            cn_summary = cn_summary  # 保留原文，但我们加个中文标题
    # 生成中文标题：用关键词拼凑
    cn_keywords = []
    title_lower = title.lower()
    for en, cn in trans_map.items():
        if en.lower() in title_lower:
            cn_keywords.append(cn)
    cn_title = "｜".join(cn_keywords[:4]) if cn_keywords else ""
    return cn_title


def fetch_us_news_yahoo(ticker, max_news=5):
    """从 Yahoo Finance RSS 获取美股个股最新新闻（免费，含摘要+中文翻译+事件检测）"""
    url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US"
    text = curl_get_text(url, referer="https://finance.yahoo.com")
    if not text:
        return []

    news_list = []
    try:
        # 简单解析 RSS XML
        items = re.findall(r'<item>(.*?)</item>', text, re.DOTALL)
        for item in items[:max_news]:
            title_match = re.search(r'<title><!\[CDATA\[(.*?)\]\]></title>', item)
            if not title_match:
                title_match = re.search(r'<title>(.*?)</title>', item)
            link_match = re.search(r'<link>(.*?)</link>', item)
            pub_match = re.search(r'<pubDate>(.*?)</pubDate>', item)
            # 提取摘要/描述
            desc_match = re.search(r'<description><!\[CDATA\[(.*?)\]\]></description>', item, re.DOTALL)
            if not desc_match:
                desc_match = re.search(r'<description>(.*?)</description>', item, re.DOTALL)

            if title_match:
                title = title_match.group(1).strip()
                link = link_match.group(1).strip() if link_match else ""
                pub_date = pub_match.group(1).strip() if pub_match else ""
                # 清理摘要中的 HTML 标签
                description = ""
                if desc_match:
                    description = desc_match.group(1).strip()
                    description = re.sub(r'<[^>]+>', '', description)  # 去HTML标签
                    description = description[:200]  # 截断
                # 中文关键词翻译
                cn_title = simple_translate(title, description)
                # 大事件检测
                events = detect_events(title, description)
                news_list.append({
                    "标题": title,
                    "中文提示": cn_title,
                    "摘要": description,
                    "事件标签": events,
                    "链接": link,
                    "时间": pub_date,
                    "来源": "Yahoo Finance",
                })
    except Exception:
        pass
    return news_list


def fetch_us_news_sina(ticker):
    """从新浪财经获取美股个股新闻（中文，免费）"""
    # 新浪美股新闻 API
    url = f"https://feed.mix.sina.com.cn/api/roll/get?pageid=155&lid=2516&k=&num=5&page=1&r=0.{int(time.time())}"
    # 尝试用关键词搜索
    name_map = {
        "NVDA": "英伟达", "AVGO": "博通", "TSM": "台积电",
        "COHR": "Coherent", "LITE": "Lumentum", "ANET": "Arista",
        "MSFT": "微软", "GOOGL": "谷歌", "META": "Meta",
        "AMZN": "亚马逊", "CSCO": "思科",
    }
    keyword = name_map.get(ticker, ticker)
    search_url = f"https://search.sina.com.cn/news?q={keyword}&range=all&c=news&sort=time&col=1_7&source=&from=&country=&size=5&stype=0&dpc=1"
    # 用简单的新浪搜索（可能被反爬，做 fallback）
    text = curl_get_text(
        f"https://feed.mix.sina.com.cn/api/roll/get?pageid=155&lid=2516&k={keyword}&num=5&page=1",
        referer="https://finance.sina.com.cn"
    )
    news_list = []
    if text:
        try:
            data = json.loads(text)
            items = data.get("result", {}).get("data", [])
            for item in items[:5]:
                title = item.get("title", "").replace("<em>", "").replace("</em>", "")
                if title and keyword.lower() in title.lower() or ticker.lower() in title.lower():
                    news_list.append({
                        "标题": title,
                        "链接": item.get("url", ""),
                        "时间": item.get("ctime", ""),
                        "来源": "新浪财经",
                    })
        except Exception:
            pass
    return news_list


def collect_us_news(tickers_info):
    """采集美股新闻"""
    print("\n📰 正在采集美股重要新闻...")
    all_news = {}

    for ticker, info in tickers_info.items():
        name = info.get("名称", ticker)
        print(f"  [{ticker}] {name} 新闻...", end="")

        # 优先 Yahoo RSS（英文，稳定）
        news = fetch_us_news_yahoo(ticker, max_news=3)

        # 补充新浪中文新闻
        sina_news = fetch_us_news_sina(ticker)
        if sina_news:
            news.extend(sina_news[:2])

        if news:
            all_news[ticker] = {
                "名称": name,
                "新闻": news[:5],  # 最多5条
            }
            print(f" ✓ {len(news)} 条")
        else:
            print(" ✗ 无新闻")

        time.sleep(0.5)  # 避免太快被封

    return all_news


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
    """执行美股数据采集（行情 + 新闻）"""
    os.makedirs(DATA_DIR, exist_ok=True)

    print("\n" + "=" * 60)
    print(f"🇺🇸 开始美股关联标的采集 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    results = collect_us_stocks()

    # 采集美股新闻
    us_news = collect_us_news(US_STOCKS)

    # 保存
    today = datetime.now().strftime("%Y%m%d")
    path = os.path.join(DATA_DIR, f"us_stocks_{today}.json")
    save_data = {
        "采集时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "美股行情": results,
        "美股新闻": us_news,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(save_data, f, ensure_ascii=False, indent=2)
    print(f"\n💾 美股数据已保存: {path}")

    # 概览
    up = sum(1 for v in results.values() if v.get("涨跌幅", 0) > 0)
    down = sum(1 for v in results.values() if v.get("涨跌幅", 0) < 0)
    total_news = sum(len(v.get("新闻", [])) for v in us_news.values())
    print(f"\n📊 美股概览: 上涨 {up} 只 | 下跌 {down} 只 | 新闻 {total_news} 条")

    print("\n✅ 美股采集完成！")
    return save_data


if __name__ == "__main__":
    run_us_stock_collection()
