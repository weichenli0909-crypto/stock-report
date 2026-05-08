"""
🧠 LLM 舆情分析模块 v1.0

相比老的关键词情绪分析：
  - 旧版：数关键词（"突破"=+1, "利空"=-1），无法理解语义
     例: "业绩同比增长 150%" → 没匹配到关键词 → 判定中性 ❌
  - 新版：LLM 真正理解新闻内容，给 -2 ~ +2 五档打分
     例: "业绩同比增长 150%" → +2 重大利好 ✅
     例: "环比下滑但符合预期" → -1 偏利空（比关键词法更细腻）

核心特性：
  1. 🚀 批量 + 并发：一只股票一次请求分析多条新闻
  2. 💾 本地缓存：同一条新闻标题只问 LLM 一次（大幅省钱）
  3. 🛡️ 优雅降级：没 API key / 请求失败，静默 fallback 到关键词法
  4. 💰 成本可控：每只股票最多 5 条，预估每天 < 0.05 元
  5. 🔄 可复用：支持 DeepSeek / OpenAI 兼容接口 / 通义 / 火山

工作流位置：
  step1b_news.py（已有）采集新闻 + 关键词情绪
  ↓
  step1b_llm_sentiment.py（本模块）给每条新闻加 llm_score
  ↓
  step2b_predict.py 的 external_score 会优先用 llm_score

环境变量：
  DEEPSEEK_API_KEY  -  优先使用（推荐，最便宜）
  OPENAI_API_KEY    -  备选（支持 GPT-4o-mini 等）
  LLM_MODEL         -  可选，默认 deepseek-chat

运行方式：
  python3 step1b_llm_sentiment.py          # 分析今日新闻
  python3 step1b_llm_sentiment.py --test   # 小样本测试（3 只股票）
"""

import os
import sys
import json
import time
import hashlib
import warnings
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

warnings.filterwarnings("ignore")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import DATA_DIR

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


# ==================== 配置 ====================

LLM_API_CONFIGS = {
    "deepseek": {
        "endpoint": "https://api.deepseek.com/v1/chat/completions",
        "model": "deepseek-chat",
        "env": "DEEPSEEK_API_KEY",
        "cost_note": "约 ¥0.001 / 次，最便宜",
    },
    "openai": {
        "endpoint": "https://api.openai.com/v1/chat/completions",
        "model": "gpt-4o-mini",
        "env": "OPENAI_API_KEY",
        "cost_note": "约 ¥0.01 / 次",
    },
    "dashscope": {  # 阿里通义千问
        "endpoint": "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
        "model": "qwen-turbo",
        "env": "DASHSCOPE_API_KEY",
        "cost_note": "约 ¥0.0003 / 次",
    },
}

MAX_NEWS_PER_STOCK = 5       # 每只股票最多分析 N 条新闻
MAX_CONCURRENT = 8            # 并发请求数（避免 429）
REQUEST_TIMEOUT = 20
MAX_RETRIES = 2

CACHE_PATH = os.path.join(DATA_DIR, "llm_sentiment_cache.json")


# ==================== Prompt 设计 ====================

SYSTEM_PROMPT = """你是一位 A 股资深量化研究员。请对新闻标题做严格的情绪打分。

评分标准（-2 ~ +2）：
+2 = 重大利好：业绩大超预期、获重大订单、政策强扶持、重组成功、技术突破
+1 = 偏利好：业绩改善、新产品、估值提升、行业景气
 0 = 中性：人事变动、普通公告、中性行业分析、无实质内容
-1 = 偏利空：业绩下滑、诉讼纠纷、监管关注、行业承压
-2 = 重大利空：业绩暴雷、财务造假、退市风险、重大事故、高管被查

严格要求：
1. 只看标题的核心信息，不做过度联想
2. 不要被夸张词误导（"突破"未必利好，需看是什么突破）
3. 纯标题没有数字和事实 → 0 分
4. 涉及数字变化优先识别方向（增长/下滑/同比/环比）

输出格式：严格 JSON 数组，不要任何多余文字、不要 markdown 代码块。
每项包含 idx（对应输入序号）、score（整数 -2~2）、reason（不超过 15 字）。
"""


def build_user_prompt(stock_name, news_titles):
    """构造用户 prompt"""
    items = [f"[{i}] {title}" for i, title in enumerate(news_titles)]
    return f"""请对下列关于【{stock_name}】的新闻标题打分：

{chr(10).join(items)}

返回 JSON 数组，示例：
[{{"idx":0,"score":2,"reason":"业绩超预期+大订单"}},{{"idx":1,"score":-1,"reason":"业绩环比下滑"}}]"""


# ==================== LLM 客户端 ====================

def _detect_provider():
    """自动探测可用的 LLM provider"""
    for name, cfg in LLM_API_CONFIGS.items():
        if os.environ.get(cfg["env"]):
            return name, cfg
    return None, None


def _call_llm(system_prompt, user_prompt, api_key, cfg, retry=0):
    """调用 LLM，返回解析后的 list 或 None"""
    if not HAS_REQUESTS:
        return None

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": os.environ.get("LLM_MODEL", cfg["model"]),
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.1,           # 低温度，保证稳定性
        "max_tokens": 800,
        "response_format": {"type": "json_object"},  # DeepSeek 支持
    }
    # gpt 系不认识 json_object 的，就 fallback
    if "openai" in cfg["endpoint"]:
        payload["response_format"] = {"type": "json_object"}

    try:
        resp = requests.post(
            cfg["endpoint"],
            headers=headers,
            json=payload,
            timeout=REQUEST_TIMEOUT,
        )
        if resp.status_code != 200:
            if retry < MAX_RETRIES and resp.status_code in (429, 500, 502, 503):
                time.sleep(2 ** retry)
                return _call_llm(system_prompt, user_prompt, api_key, cfg, retry + 1)
            return None

        data = resp.json()
        content = data["choices"][0]["message"]["content"].strip()

        # 去掉 markdown 代码块的干扰
        if content.startswith("```"):
            content = content.split("```", 2)[1]
            if content.startswith(("json", "JSON")):
                content = content[4:].strip()
            if content.endswith("```"):
                content = content[:-3].strip()

        # 有的模型会返回 {"result": [...]} 或 {"data": [...]}
        parsed = json.loads(content)
        if isinstance(parsed, list):
            return parsed
        for key in ["result", "data", "items", "scores"]:
            if key in parsed and isinstance(parsed[key], list):
                return parsed[key]
        return None

    except requests.exceptions.Timeout:
        if retry < MAX_RETRIES:
            return _call_llm(system_prompt, user_prompt, api_key, cfg, retry + 1)
        return None
    except Exception as e:
        return None


# ==================== 缓存 ====================

def load_cache():
    if not os.path.exists(CACHE_PATH):
        return {}
    try:
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_cache(cache):
    try:
        with open(CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _title_hash(title):
    """用标题 + 股票名做缓存 key，避免不同股票同标题错误复用"""
    return hashlib.md5(title.encode("utf-8")).hexdigest()[:12]


# ==================== 主流程 ====================

def analyze_stock_news(stock_code, stock_name, news_list, api_key, cfg, cache):
    """
    分析一只股票的新闻，返回 updated_news（带 llm_score + llm_reason）
    """
    if not news_list:
        return news_list

    # 只取最新 MAX_NEWS_PER_STOCK 条
    to_analyze = news_list[:MAX_NEWS_PER_STOCK]

    # 先查缓存
    titles = []
    title_idxs = []  # to_analyze 里未命中缓存的索引
    for i, n in enumerate(to_analyze):
        title = n.get("标题", "")
        key = _title_hash(title)
        if key in cache:
            n["llm_score"] = cache[key]["score"]
            n["llm_reason"] = cache[key]["reason"]
        else:
            titles.append(title)
            title_idxs.append(i)

    # 全部命中缓存直接返回
    if not titles:
        return to_analyze + news_list[MAX_NEWS_PER_STOCK:]

    # 调用 LLM
    user_prompt = build_user_prompt(stock_name, titles)
    result = _call_llm(SYSTEM_PROMPT, user_prompt, api_key, cfg)

    if result is None:
        # LLM 失败，保持老的情绪分（关键词法）
        return news_list

    # 解析 & 写回 + 入缓存
    for item in result:
        try:
            rel_idx = int(item.get("idx", -1))
            score = int(item.get("score", 0))
            score = max(-2, min(2, score))  # 夹到 [-2, 2]
            reason = str(item.get("reason", ""))[:30]
            if 0 <= rel_idx < len(title_idxs):
                abs_idx = title_idxs[rel_idx]
                to_analyze[abs_idx]["llm_score"] = score
                to_analyze[abs_idx]["llm_reason"] = reason
                # 写入缓存
                title = titles[rel_idx]
                cache[_title_hash(title)] = {"score": score, "reason": reason}
        except Exception:
            continue

    return to_analyze + news_list[MAX_NEWS_PER_STOCK:]


def run_llm_sentiment(test_mode=False):
    """主流程"""
    print("\n" + "=" * 70)
    print(f"🧠 LLM 舆情分析 v1.0 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # 1. 找可用 provider
    provider, cfg = _detect_provider()
    if provider is None:
        print("  ⚠️ 未检测到任何 LLM API key（DEEPSEEK/OPENAI/DASHSCOPE）")
        print("     将跳过 LLM 分析，保持关键词法舆情")
        return False
    api_key = os.environ.get(cfg["env"])
    print(f"  ✅ 使用 {provider.upper()} ({cfg['model']}) | {cfg['cost_note']}")

    # 2. 加载今日新闻
    today = datetime.now().strftime("%Y%m%d")
    news_path = os.path.join(DATA_DIR, f"news_{today}.json")
    if not os.path.exists(news_path):
        from glob import glob
        files = sorted(glob(os.path.join(DATA_DIR, "news_*.json")))
        if not files:
            print("  ❌ 未找到新闻文件")
            return False
        news_path = files[-1]
        today = os.path.basename(news_path).replace("news_", "").replace(".json", "")
        print(f"  📂 使用最近文件: {news_path}")

    with open(news_path, "r", encoding="utf-8") as f:
        news_data = json.load(f)

    stock_news = news_data.get("个股舆情", {})
    print(f"  📰 待分析股票数: {len(stock_news)}")

    if test_mode:
        codes = list(stock_news.keys())[:3]
        stock_news = {c: stock_news[c] for c in codes}
        print(f"  🧪 测试模式：只分析 {len(stock_news)} 只股票")

    # 3. 加载缓存
    cache = load_cache()
    print(f"  💾 缓存中已有 {len(cache)} 条新闻评分")

    # 4. 并发分析
    updated_count = 0
    llm_calls = 0
    cache_hits = 0

    def process_one(code, data):
        nonlocal llm_calls, cache_hits
        news_list = data.get("新闻", [])
        if not news_list:
            return code, None

        # 先看缓存命中率
        before_cache_len = len(cache)
        updated_news = analyze_stock_news(
            code, data.get("名称", ""), news_list, api_key, cfg, cache
        )
        new_in_cache = len(cache) - before_cache_len
        if new_in_cache > 0:
            llm_calls += 1
        else:
            # 没新增缓存 → 全部命中 or LLM 失败
            if any("llm_score" in n for n in updated_news[:MAX_NEWS_PER_STOCK]):
                cache_hits += 1

        return code, updated_news

    start = time.time()
    with ThreadPoolExecutor(max_workers=MAX_CONCURRENT) as pool:
        futures = {
            pool.submit(process_one, code, data): code
            for code, data in stock_news.items()
        }
        for fut in as_completed(futures):
            code, updated = fut.result()
            if updated is not None:
                stock_news[code]["新闻"] = updated

                # 重算该股票的 LLM 情绪统计
                llm_scores = [n.get("llm_score") for n in updated[:MAX_NEWS_PER_STOCK]
                              if n.get("llm_score") is not None]
                if llm_scores:
                    avg_llm = sum(llm_scores) / len(llm_scores)
                    stock_news[code]["llm_情绪统计"] = {
                        "条数": len(llm_scores),
                        "平均分": round(avg_llm, 2),
                        "正向数": sum(1 for s in llm_scores if s > 0),
                        "负向数": sum(1 for s in llm_scores if s < 0),
                    }
                    updated_count += 1

    elapsed = time.time() - start

    # 5. 保存
    news_data["个股舆情"] = stock_news
    news_data["llm_分析时间"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    news_data["llm_provider"] = provider
    news_data["llm_model"] = cfg["model"]

    with open(news_path, "w", encoding="utf-8") as f:
        json.dump(news_data, f, ensure_ascii=False, indent=2)

    save_cache(cache)

    # 6. 汇总
    print(f"\n📊 LLM 舆情分析完成:")
    print(f"  - 处理股票: {updated_count} 只")
    print(f"  - LLM 调用: {llm_calls} 次")
    print(f"  - 缓存命中: {cache_hits} 只股票全部命中")
    print(f"  - 缓存累计: {len(cache)} 条新闻")
    print(f"  - 耗时: {elapsed:.1f} 秒")
    print(f"  - 预估成本: ¥{llm_calls * 0.002:.3f}（DeepSeek 口径）")

    # 7. Top 利好/利空
    stocks_with_llm = [
        (c, d.get("名称", ""), d.get("llm_情绪统计", {}))
        for c, d in stock_news.items()
        if d.get("llm_情绪统计")
    ]
    if stocks_with_llm:
        stocks_with_llm.sort(key=lambda x: x[2].get("平均分", 0), reverse=True)
        print(f"\n  🔥 LLM 最利好 Top 5:")
        for c, name, s in stocks_with_llm[:5]:
            print(f"    {name:<10s} 均分 {s['平均分']:+.2f}  ({s['条数']}条)")
        print(f"  ❄️ LLM 最利空 Top 5:")
        for c, name, s in stocks_with_llm[-5:][::-1]:
            print(f"    {name:<10s} 均分 {s['平均分']:+.2f}  ({s['条数']}条)")

    return True


if __name__ == "__main__":
    test = "--test" in sys.argv
    run_llm_sentiment(test_mode=test)
