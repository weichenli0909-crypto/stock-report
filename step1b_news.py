"""
📰 舆情采集模块
采集个股相关新闻、公告，并进行简单情绪分析
"""

import os
import re
import json
import time
import subprocess
from datetime import datetime
from config import get_all_stocks, STOCK_PROFILES, DATA_DIR


def curl_get_text(url, referer="https://finance.sina.com.cn", encoding="utf-8"):
    """使用 curl 发起 GET 请求，返回文本"""
    try:
        result = subprocess.run(
            [
                "curl",
                "-s",
                "-m",
                "15",
                "-L",
                "-H",
                f"Referer: {referer}",
                "-H",
                "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                url,
            ],
            capture_output=True,
            timeout=20,
        )
        if result.returncode == 0 and result.stdout:
            try:
                return result.stdout.decode(encoding)
            except UnicodeDecodeError:
                return result.stdout.decode("utf-8", errors="replace")
    except Exception as e:
        pass
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
                "-L",
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
        if result.returncode == 0 and result.stdout.strip():
            # 处理 JSONP 回调格式
            text = result.stdout.strip()
            if text.startswith("(") and text.endswith(")"):
                text = text[1:-1]
            elif "(" in text and text.endswith(")"):
                text = text[text.index("(") + 1 : -1]
            return json.loads(text)
    except Exception:
        pass
    return None


def get_sina_code(code):
    """股票代码转新浪格式"""
    if code.startswith(("6", "9")):
        return f"sh{code}"
    return f"sz{code}"


# ==================== 情绪关键词库 ====================

POSITIVE_WORDS = [
    "大涨",
    "涨停",
    "暴涨",
    "新高",
    "突破",
    "利好",
    "超预期",
    "增长",
    "放量",
    "领涨",
    "强势",
    "翻倍",
    "机遇",
    "看好",
    "推荐",
    "买入",
    "加仓",
    "增持",
    "回购",
    "上调",
    "创新高",
    "订单",
    "中标",
    "签约",
    "合作",
    "扩产",
    "投产",
    "量产",
    "盈利",
    "分红",
    "业绩预增",
    "高增长",
    "超预期",
    "产能释放",
    "需求旺盛",
    "景气",
    "加速",
]

NEGATIVE_WORDS = [
    "大跌",
    "跌停",
    "暴跌",
    "新低",
    "破位",
    "利空",
    "不及预期",
    "下滑",
    "缩量",
    "领跌",
    "弱势",
    "腰斩",
    "风险",
    "看空",
    "减持",
    "卖出",
    "清仓",
    "减持",
    "质押",
    "下调",
    "创新低",
    "亏损",
    "诉讼",
    "处罚",
    "违规",
    "退市",
    "警告",
    "担忧",
    "压力",
    "业绩预减",
    "下降",
    "库存积压",
    "需求萎缩",
    "价格战",
    "制裁",
    "限制",
]

EVENT_KEYWORDS = {
    "财报": ["年报", "季报", "半年报", "业绩快报", "业绩预告", "营收", "净利润"],
    "收购/并购": ["收购", "并购", "重组", "合并", "股权转让", "要约收购"],
    "融资": ["定增", "增发", "配股", "可转债", "融资", "IPO"],
    "产品/技术": ["新品", "发布", "量产", "研发", "专利", "技术突破"],
    "订单/合同": ["订单", "合同", "中标", "签约", "框架协议"],
    "股东变动": ["减持", "增持", "回购", "股东", "举牌", "大宗交易"],
    "监管/处罚": ["问询函", "关注函", "处罚", "立案", "警示", "违规"],
}


def analyze_sentiment(title):
    """
    对新闻标题进行简单情绪分析
    返回: (score, label)
      score: -1.0 到 1.0
      label: "正面" / "负面" / "中性"
    """
    pos_count = sum(1 for w in POSITIVE_WORDS if w in title)
    neg_count = sum(1 for w in NEGATIVE_WORDS if w in title)

    total = pos_count + neg_count
    if total == 0:
        return 0, "中性"

    score = (pos_count - neg_count) / total
    if score > 0.2:
        return round(score, 2), "正面"
    elif score < -0.2:
        return round(score, 2), "负面"
    else:
        return round(score, 2), "中性"


def detect_events(title):
    """检测新闻中的重要事件类型"""
    events = []
    for event_type, keywords in EVENT_KEYWORDS.items():
        if any(kw in title for kw in keywords):
            events.append(event_type)
    return events


def collect_stock_news(stock_code, stock_name, count=8):
    """
    从东方财富搜索API获取个股新闻
    """
    import urllib.parse

    keyword = urllib.parse.quote(stock_name)
    param = (
        f'{{"uid":"","keyword":"{stock_name}",'
        f'"type":["cmsArticleWebOld"],'
        f'"client":"web","clientType":"web","clientVersion":"curr",'
        f'"param":{{"cmsArticleWebOld":{{"searchScope":"default","sort":"default",'
        f'"pageIndex":1,"pageSize":{count}}}}}}}'
    )
    encoded_param = urllib.parse.quote(param)
    url = f"https://search-api-web.eastmoney.com/search/jsonp?cb=jQuery&param={encoded_param}"

    text = curl_get_text(url, referer="https://so.eastmoney.com/", encoding="utf-8")
    news_list = []

    if not text:
        return news_list

    try:
        # 去掉 JSONP 包装 jQuery(...)
        import re as _re

        m = _re.search(r"jQuery\((.*)\)", text, _re.DOTALL)
        if not m:
            return news_list
        data = json.loads(m.group(1))

        articles = data.get("result", {}).get("cmsArticleWebOld", [])
        if not articles:
            return news_list

        for item in articles:
            title = item.get("title", "").strip()
            # 去掉 HTML 标签 (<em> 等)
            title = _re.sub(r"<[^>]+>", "", title)
            if not title:
                continue

            content = item.get("content", "")
            content = _re.sub(r"<[^>]+>", "", content)

            pub_time = item.get("date", "")
            source = item.get("mediaName", "")

            # 对标题+内容摘要一起做情绪分析
            analysis_text = title + " " + content[:100]
            score, label = analyze_sentiment(analysis_text)
            events = detect_events(analysis_text)

            news_list.append(
                {
                    "标题": title,
                    "摘要": content[:120] if content else "",
                    "时间": pub_time,
                    "来源": source,
                    "链接": item.get("url", ""),
                    "情绪": label,
                    "情绪分": score,
                    "事件标签": events,
                }
            )
    except Exception:
        pass

    return news_list


def collect_stock_announcements(stock_code, stock_name):
    """
    采集个股最近的重要公告
    使用巨潮资讯网 API
    """
    url = (
        f"http://www.cninfo.com.cn/new/hisAnnouncement/query?"
        f"stock={stock_code}&tabName=fulltext&pageSize=5&pageNum=1"
        f"&column=szse&isHLtitle=true"
    )

    # 巨潮资讯可能需要特殊处理，这里用备选方案
    # 从新浪公告获取
    sina_code = get_sina_code(stock_code)
    url = (
        f"https://feed.mix.sina.com.cn/api/roll/get?"
        f"pageid=155&lid=2516&k={stock_name}+公告&num=5&page=1"
    )

    data = curl_get_json(url)
    announcements = []

    if data and "result" in data and "data" in data["result"]:
        for item in data["result"]["data"]:
            title = item.get("title", "").strip()
            if not title:
                continue
            pub_time = item.get("ctime", "")
            if pub_time and pub_time.isdigit():
                pub_time = datetime.fromtimestamp(int(pub_time)).strftime("%Y-%m-%d")

            events = detect_events(title)
            announcements.append(
                {
                    "标题": title,
                    "时间": pub_time,
                    "事件标签": events,
                    "链接": item.get("url", ""),
                }
            )

    return announcements


def collect_all_news():
    """采集所有关注个股的新闻和公告"""
    print("📰 正在采集舆情新闻...")

    all_stocks = get_all_stocks()
    all_news = {}

    for i, (code, name) in enumerate(all_stocks.items()):
        print(f"  [{i+1}/{len(all_stocks)}] 采集 {name}({code}) 新闻...", end="")

        stock_data = {
            "代码": code,
            "名称": name,
            "新闻": collect_stock_news(code, name, count=8),
        }

        # 统计情绪
        news = stock_data["新闻"]
        if news:
            pos = sum(1 for n in news if n["情绪"] == "正面")
            neg = sum(1 for n in news if n["情绪"] == "负面")
            neu = sum(1 for n in news if n["情绪"] == "中性")
            stock_data["情绪统计"] = {"正面": pos, "负面": neg, "中性": neu}

            # 汇总事件
            all_events = []
            for n in news:
                all_events.extend(n["事件标签"])
            stock_data["事件汇总"] = list(set(all_events))

            print(f" ✓ {len(news)}条 (👍{pos} 👎{neg} ➖{neu})")
        else:
            stock_data["情绪统计"] = {"正面": 0, "负面": 0, "中性": 0}
            stock_data["事件汇总"] = []
            print(" ✗ 无新闻")

        all_news[code] = stock_data
        time.sleep(0.3)

    return all_news


def compute_overall_sentiment(all_news):
    """计算整体市场情绪"""
    total_pos = 0
    total_neg = 0
    total_neu = 0

    for code, data in all_news.items():
        stats = data.get("情绪统计", {})
        total_pos += stats.get("正面", 0)
        total_neg += stats.get("负面", 0)
        total_neu += stats.get("中性", 0)

    total = total_pos + total_neg + total_neu
    if total == 0:
        return {"总新闻数": 0, "情绪指数": 0, "情绪判断": "无数据"}

    sentiment_index = round((total_pos - total_neg) / total * 100, 1)

    if sentiment_index > 15:
        judgment = "🟢 偏乐观"
    elif sentiment_index > 5:
        judgment = "🔵 略偏积极"
    elif sentiment_index > -5:
        judgment = "⚪ 中性"
    elif sentiment_index > -15:
        judgment = "🟡 略偏消极"
    else:
        judgment = "🔴 偏悲观"

    return {
        "总新闻数": total,
        "正面": total_pos,
        "负面": total_neg,
        "中性": total_neu,
        "情绪指数": sentiment_index,
        "情绪判断": judgment,
    }


def run_news_collection():
    """执行新闻舆情采集"""
    os.makedirs(DATA_DIR, exist_ok=True)

    print("\n" + "=" * 60)
    print(f"📰 开始舆情采集 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # 采集新闻
    all_news = collect_all_news()

    # 计算整体情绪
    overall = compute_overall_sentiment(all_news)
    print(f"\n📊 整体舆情概览:")
    print(
        f"  总新闻 {overall['总新闻数']} 条 | "
        f"正面 {overall.get('正面', 0)} | 负面 {overall.get('负面', 0)} | "
        f"中性 {overall.get('中性', 0)}"
    )
    print(f"  情绪指数: {overall.get('情绪指数', 0)} ({overall.get('情绪判断', '')})")

    # 保存
    today = datetime.now().strftime("%Y%m%d")
    result = {
        "采集时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "整体情绪": overall,
        "个股舆情": all_news,
    }

    path = os.path.join(DATA_DIR, f"news_{today}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\n💾 舆情数据已保存: {path}")

    print("\n✅ 舆情采集完成！")
    return result


if __name__ == "__main__":
    run_news_collection()
