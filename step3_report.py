"""
📊 第三步：可视化与报告生成
生成图表和 HTML 报告（含板块介绍、产业链、个股档案、舆情分析）
"""

import os
import json
import base64
from io import BytesIO
from datetime import datetime

import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams["font.sans-serif"] = [
    "Arial Unicode MS",  # macOS
    "PingFang SC",  # macOS
    "Noto Sans CJK SC",  # Linux (GitHub Actions)
    "WenQuanYi Micro Hei",  # Linux 备选
    "SimHei",  # Windows
    "Microsoft YaHei",  # Windows
]
plt.rcParams["axes.unicode_minus"] = False

from config import STOCK_GROUPS, SECTOR_INFO, STOCK_PROFILES, DATA_DIR, OUTPUT_DIR


def ensure_dirs():
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def fig_to_base64(fig):
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=120, bbox_inches="tight")
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode("utf-8")
    plt.close(fig)
    return img_base64


# ============ 图表生成 ============


def chart_sector_performance(analysis):
    sector_data = analysis.get("实时分析", {}).get("板块表现", [])
    if not sector_data:
        return None
    names = [s["板块"] for s in sector_data]
    changes = [s["平均涨跌幅"] for s in sector_data]
    colors = ["#ef4444" if v >= 0 else "#22c55e" for v in changes]
    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.barh(names, changes, color=colors, height=0.6)
    ax.set_xlabel("平均涨跌幅 (%)")
    ax.set_title("各板块今日平均涨跌幅", fontsize=14, fontweight="bold")
    ax.axvline(x=0, color="gray", linewidth=0.5)
    for bar, val in zip(bars, changes):
        ax.text(
            bar.get_width() + (0.1 if val >= 0 else -0.1),
            bar.get_y() + bar.get_height() / 2,
            f"{val}%",
            ha="left" if val >= 0 else "right",
            va="center",
            fontsize=10,
        )
    ax.invert_yaxis()
    fig.tight_layout()
    path = os.path.join(OUTPUT_DIR, "sector_performance.png")
    fig.savefig(path, dpi=120, bbox_inches="tight")
    print(f"  [图表] 板块表现图已保存")
    return fig_to_base64(fig)


def chart_stock_heatmap(analysis):
    realtime = analysis.get("实时分析", {})
    top5 = realtime.get("涨幅Top5", [])
    bottom5 = realtime.get("跌幅Top5", [])
    if not top5 and not bottom5:
        return None
    all_stocks = top5 + bottom5
    names = [s["名称"] for s in all_stocks]
    changes = [float(s["涨跌幅"]) for s in all_stocks]
    fig, ax = plt.subplots(figsize=(10, 4))
    colors = ["#ef4444" if v >= 0 else "#22c55e" for v in changes]
    bars = ax.bar(range(len(names)), changes, color=colors, width=0.7)
    ax.set_xticks(range(len(names)))
    ax.set_xticklabels(names, rotation=45, ha="right", fontsize=9)
    ax.set_ylabel("涨跌幅 (%)")
    ax.set_title("涨幅 Top5 vs 跌幅 Top5", fontsize=14, fontweight="bold")
    ax.axhline(y=0, color="gray", linewidth=0.5)
    for bar, val in zip(bars, changes):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + (0.1 if val >= 0 else -0.3),
            f"{val}%",
            ha="center",
            va="bottom" if val >= 0 else "top",
            fontsize=9,
        )
    fig.tight_layout()
    path = os.path.join(OUTPUT_DIR, "stock_top_bottom.png")
    fig.savefig(path, dpi=120, bbox_inches="tight")
    print(f"  [图表] 涨跌排行图已保存")
    return fig_to_base64(fig)


def chart_history_trend(analysis):
    trends = analysis.get("趋势分析", {}).get("个股趋势", [])
    if not trends:
        return None
    trends = trends[:15]
    names = [t["名称"] for t in trends]
    changes = [t["近5日涨跌幅"] for t in trends]
    colors = ["#ef4444" if v >= 0 else "#22c55e" for v in changes]
    fig, ax = plt.subplots(figsize=(12, 5))
    bars = ax.barh(names, changes, color=colors, height=0.6)
    ax.set_xlabel("近5日涨跌幅 (%)")
    ax.set_title("个股近5日涨跌幅排名", fontsize=14, fontweight="bold")
    ax.axvline(x=0, color="gray", linewidth=0.5)
    for bar, val in zip(bars, changes):
        ax.text(
            bar.get_width() + (0.2 if val >= 0 else -0.2),
            bar.get_y() + bar.get_height() / 2,
            f"{val}%",
            ha="left" if val >= 0 else "right",
            va="center",
            fontsize=9,
        )
    ax.invert_yaxis()
    fig.tight_layout()
    path = os.path.join(OUTPUT_DIR, "history_trend.png")
    fig.savefig(path, dpi=120, bbox_inches="tight")
    print(f"  [图表] 近期趋势图已保存")
    return fig_to_base64(fig)


def chart_volume_pie(analysis):
    sector_data = analysis.get("实时分析", {}).get("板块表现", [])
    if not sector_data:
        return None
    names = [s["板块"] for s in sector_data]
    amounts = [max(s["成交额(亿)"], 0.01) for s in sector_data]
    fig, ax = plt.subplots(figsize=(8, 6))
    colors_palette = [
        "#ef4444",
        "#f97316",
        "#eab308",
        "#22c55e",
        "#3b82f6",
        "#8b5cf6",
        "#ec4899",
        "#06b6d4",
    ]
    ax.pie(
        amounts,
        labels=names,
        autopct="%1.1f%%",
        colors=colors_palette[: len(names)],
        startangle=90,
    )
    ax.set_title("各板块成交额占比", fontsize=14, fontweight="bold")
    fig.tight_layout()
    path = os.path.join(OUTPUT_DIR, "volume_pie.png")
    fig.savefig(path, dpi=120, bbox_inches="tight")
    print(f"  [图表] 成交额占比图已保存")
    return fig_to_base64(fig)


def chart_sentiment(news_data):
    """生成舆情情绪分布图"""
    if not news_data:
        return None
    overall = news_data.get("整体情绪", {})
    if not overall or overall.get("总新闻数", 0) == 0:
        return None
    labels = ["正面", "负面", "中性"]
    sizes = [overall.get("正面", 0), overall.get("负面", 0), overall.get("中性", 0)]
    colors = ["#ef4444", "#22c55e", "#94a3b8"]
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.pie(sizes, labels=labels, autopct="%1.0f%%", colors=colors, startangle=90)
    ax.set_title("舆情情绪分布", fontsize=14, fontweight="bold")
    fig.tight_layout()
    path = os.path.join(OUTPUT_DIR, "sentiment_pie.png")
    fig.savefig(path, dpi=120, bbox_inches="tight")
    print(f"  [图表] 舆情情绪图已保存")
    return fig_to_base64(fig)


# ============ HTML 生成辅助 ============


def make_table(data_list, columns=None):
    if not data_list:
        return '<p style="color:#64748b">暂无数据</p>'
    if columns is None:
        columns = list(data_list[0].keys())
    rows = ""
    for item in data_list:
        cells = ""
        for col in columns:
            val = item.get(col, "")
            if "涨跌幅" in str(col) and isinstance(val, (int, float)):
                color = "#ef4444" if val >= 0 else "#22c55e"
                cells += f'<td style="color:{color};font-weight:bold">{val}%</td>'
            elif "成交额" in str(col) and isinstance(val, (int, float)):
                cells += f"<td>{val:,.0f}</td>"
            else:
                cells += f"<td>{val}</td>"
        rows += f"<tr>{cells}</tr>"
    headers = "".join(f"<th>{c}</th>" for c in columns)
    return f"<table><thead><tr>{headers}</tr></thead><tbody>{rows}</tbody></table>"


def img_html(base64_str, alt="chart"):
    if base64_str:
        return f'<img src="data:image/png;base64,{base64_str}" alt="{alt}" style="max-width:100%;border-radius:8px;margin:10px 0;">'
    return ""


# ============ 各板块 HTML 内容 ============


def build_sector_intro_html():
    """生成板块介绍 & 产业链 HTML"""
    html = ""
    for name, info in SECTOR_INFO.items():
        upstream = " → ".join(info["上游"])
        downstream = " → ".join(info["下游"])
        html += f"""
        <div class="sector-card">
            <h3>{name}</h3>
            <p class="desc">{info['描述']}</p>
            <div class="chain-row">
                <div class="chain-box upstream">
                    <div class="chain-label">⬆️ 上游</div>
                    <div class="chain-items">{''.join(f'<span class="tag tag-blue">{x}</span>' for x in info["上游"])}</div>
                </div>
                <div class="chain-arrow">→ {name} →</div>
                <div class="chain-box downstream">
                    <div class="chain-label">⬇️ 下游</div>
                    <div class="chain-items">{''.join(f'<span class="tag tag-green">{x}</span>' for x in info["下游"])}</div>
                </div>
            </div>
            <div class="meta-row">
                <span class="tag tag-yellow">🔥 {info['核心驱动']}</span>
            </div>
            <div class="meta-row">
                <span class="tag tag-red">⚠️ {info['风险提示']}</span>
            </div>
        </div>"""
    return html


def build_stock_profiles_html(analysis):
    """生成按板块分类的个股档案 HTML（含子Tab切换）"""
    trends = analysis.get("趋势分析", {}).get("个股趋势", [])
    trend_map = {str(t["代码"]): t for t in trends}

    # 板块子Tab按钮
    sector_names = list(STOCK_GROUPS.keys())
    btns = ""
    for i, name in enumerate(sector_names):
        active = " active" if i == 0 else ""
        btns += f'<button class="sub-tab{active}" onclick="switchSubTab(this,\'sector-{i}\')">{name} ({len(STOCK_GROUPS[name])})</button>'
    html = f'<div class="sub-tabs">{btns}</div>'

    # 每个板块的个股
    for i, (sector, stocks) in enumerate(STOCK_GROUPS.items()):
        display = "block" if i == 0 else "none"
        html += (
            f'<div id="sector-{i}" class="sub-tab-content" style="display:{display}">'
        )
        for code, name in stocks.items():
            profile = STOCK_PROFILES.get(code, {})
            if not profile:
                continue
            trend = trend_map.get(code, {})
            price = trend.get("最新价", "-")
            change_5d = trend.get("近5日涨跌幅", "-")
            ma5 = trend.get("MA5", "-")
            ma20 = trend.get("MA20", "-")
            vol = trend.get("波动率(年化%)", "-")
            risk = profile.get("风险", "暂无")
            sectors = [s for s, st in STOCK_GROUPS.items() if code in st]
            sector_tags = "".join(
                f'<span class="tag tag-purple">{s}</span>' for s in sectors
            )
            change_color = (
                "#ef4444"
                if isinstance(change_5d, (int, float)) and change_5d >= 0
                else "#22c55e"
            )
            html += f"""
            <div class="stock-card">
                <div class="stock-header">
                    <div><span class="stock-name">{profile['名称']}</span><span class="stock-code">{code}</span>{sector_tags}</div>
                    <div class="stock-price"><span class="price" data-stock-code="{code}">{price}</span><span style="color:{change_color};font-size:13px;">近5日 {change_5d}%</span></div>
                </div>
                <div class="stock-body">
                    <div class="stock-info">
                        <div><strong>主营业务：</strong>{profile['主营']}</div>
                        <div><strong>核心亮点：</strong>{profile['亮点']}</div>
                        <div><strong>关注要点：</strong><span style="color:#f59e0b">{profile['关注点']}</span></div>
                        <div class="risk-line">⚠️ <strong>风险提示：</strong><span style="color:#fca5a5">{risk}</span></div>
                    </div>
                    <div class="stock-metrics">
                        <div class="metric"><span class="metric-label">MA5</span><span>{ma5}</span></div>
                        <div class="metric"><span class="metric-label">MA20</span><span>{ma20}</span></div>
                        <div class="metric"><span class="metric-label">波动率</span><span>{vol}%</span></div>
                    </div>
                </div>
            </div>"""
        html += "</div>"
    return html


def build_us_stocks_html(us_data):
    """生成美股关联标的 HTML"""
    if not us_data:
        return '<p style="color:#64748b">暂无美股数据（请运行完整工作流采集）</p>'

    stocks = us_data.get("美股行情", {})
    if not stocks:
        return '<p style="color:#64748b">暂无美股数据</p>'

    html = ""
    for ticker, data in stocks.items():
        price = data.get("最新价", 0)
        change = data.get("涨跌幅", 0)
        change_color = (
            "#ef4444" if change > 0 else ("#22c55e" if change < 0 else "#94a3b8")
        )
        change_sign = "+" if change > 0 else ""
        mkt_cap = data.get("市值(亿美元)", 0)
        high52 = data.get("52周最高", 0)
        low52 = data.get("52周最低", 0)
        intro = data.get("简介", "")
        related = data.get("关联A股", {})

        html += f"""
        <div class="us-stock-card">
            <div class="us-stock-header">
                <div>
                    <span class="us-ticker">{ticker}</span>
                    <span class="us-name">{data.get('中文名', '')}</span>
                </div>
                <div class="us-price-area">
                    <span class="us-price" data-us-ticker="{ticker}">${price:.2f}</span>
                    <span style="color:{change_color};font-weight:bold;font-size:15px;">{change_sign}{change:.2f}%</span>
                </div>
            </div>
            <div class="us-intro">{intro}</div>
            <div class="us-metrics">
                <span>市值: {mkt_cap}亿美元</span>
                <span>52周高: ${high52:.2f}</span>
                <span>52周低: ${low52:.2f}</span>
            </div>
            <div class="us-related">
                <div class="us-related-title">🔗 关联A股标的</div>"""
        for code, desc in related.items():
            html += f'<div class="us-related-item"><span class="tag tag-blue">{code}</span> {desc}</div>'
        html += """
            </div>
        </div>"""

    return html


def build_predictions_html(pred_data):
    """生成ML预测结果 HTML"""
    if not pred_data:
        return '<p style="color:#64748b">暂无预测数据（请运行完整工作流）</p>'

    summary = pred_data.get("汇总", {})
    sector_pred = pred_data.get("板块预测", {})
    top5 = pred_data.get("看涨Top5", [])
    bottom5 = pred_data.get("看跌Top5", [])
    all_preds = pred_data.get("个股预测", {})

    # 汇总卡片
    mood = summary.get("整体情绪", "中性")
    mood_color = (
        "#ef4444" if "多" in mood else ("#22c55e" if "空" in mood else "#94a3b8")
    )
    html = f"""
    <div class="summary-cards">
        <div class="card"><div class="label">预测周期</div><div class="number" style="color:#60a5fa;font-size:18px">{pred_data.get('预测周期','')}</div></div>
        <div class="card"><div class="label">看涨</div><div class="number up">{summary.get('看涨',0)}</div></div>
        <div class="card"><div class="label">看跌</div><div class="number down">{summary.get('看跌',0)}</div></div>
        <div class="card"><div class="label">中性</div><div class="number" style="color:#94a3b8">{summary.get('中性',0)}</div></div>
        <div class="card"><div class="label">整体情绪</div><div class="number" style="color:{mood_color}">{mood}</div></div>
    </div>"""

    # 板块预测
    html += "<h3>📊 板块预测概览</h3>"
    html += '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:12px;margin:12px 0;">'
    for name, data in sector_pred.items():
        avg_prob = data.get("平均上涨概率", 50)
        avg_ret = data.get("平均预测收益率", 0)
        prob_color = (
            "#ef4444" if avg_prob > 55 else ("#22c55e" if avg_prob < 45 else "#94a3b8")
        )
        ret_color = "#ef4444" if avg_ret > 0 else "#22c55e"
        bar_width = int(avg_prob)
        html += f"""
        <div class="sector-card" style="margin:0">
            <h3 style="font-size:14px">{name}</h3>
            <div style="display:flex;justify-content:space-between;margin:8px 0">
                <span style="color:{prob_color};font-size:20px;font-weight:bold">{avg_prob}%</span>
                <span style="color:{ret_color};font-size:14px">预测收益 {avg_ret:+.2f}%</span>
            </div>
            <div style="background:#0f172a;border-radius:4px;height:8px;overflow:hidden">
                <div style="background:linear-gradient(90deg,#22c55e,#eab308,#ef4444);width:{bar_width}%;height:100%;border-radius:4px"></div>
            </div>
            <div style="display:flex;justify-content:space-between;font-size:11px;color:#64748b;margin-top:4px">
                <span>看涨 {data.get('看涨数',0)}</span>
                <span>看跌 {data.get('看跌数',0)}</span>
                <span>共 {data.get('个股数',0)} 只</span>
            </div>
        </div>"""
    html += "</div>"

    # Top5 看涨/看跌
    html += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin:16px 0">'
    html += "<div><h3>🔥 最看涨 Top5</h3>"
    for p in top5:
        prob = p.get("上涨概率", 50)
        html += f"""<div class="stock-card" style="padding:10px;margin:6px 0">
            <div style="display:flex;justify-content:space-between;align-items:center">
                <div><strong>{p['名称']}</strong> <span style="color:#64748b;font-size:12px">{p['代码']}</span></div>
                <div style="text-align:right"><span style="color:#ef4444;font-weight:bold;font-size:16px">{prob}%</span><br><span style="font-size:11px;color:#94a3b8">{p.get('信号','')}</span></div>
            </div>
        </div>"""
    html += "</div>"

    html += "<div><h3>❄️ 最看跌 Top5</h3>"
    for p in bottom5:
        prob = p.get("上涨概率", 50)
        html += f"""<div class="stock-card" style="padding:10px;margin:6px 0">
            <div style="display:flex;justify-content:space-between;align-items:center">
                <div><strong>{p['名称']}</strong> <span style="color:#64748b;font-size:12px">{p['代码']}</span></div>
                <div style="text-align:right"><span style="color:#22c55e;font-weight:bold;font-size:16px">{prob}%</span><br><span style="font-size:11px;color:#94a3b8">{p.get('信号','')}</span></div>
            </div>
        </div>"""
    html += "</div></div>"

    # 全部个股预测表格
    html += "<h3>📋 全部个股预测明细</h3>"
    html += "<table><thead><tr><th>代码</th><th>名称</th><th>最新价</th><th>上涨概率</th><th>预测收益率</th><th>预测价格</th><th>价格区间</th><th>信号</th><th>关键因子</th></tr></thead><tbody>"
    sorted_preds = sorted(
        all_preds.values(), key=lambda x: x.get("上涨概率", 50), reverse=True
    )
    for p in sorted_preds:
        prob = p.get("上涨概率", 50)
        prob_color = "#ef4444" if prob > 55 else ("#22c55e" if prob < 45 else "#94a3b8")
        ret = p.get("预测收益率", 0)
        ret_color = "#ef4444" if ret > 0 else "#22c55e"
        factors = ", ".join(p.get("关键因子", [])[:3])
        html += f"""<tr>
            <td>{p.get('代码','')}</td>
            <td>{p.get('名称','')}</td>
            <td>{p.get('最新价','')}</td>
            <td style="color:{prob_color};font-weight:bold">{prob}%</td>
            <td style="color:{ret_color};font-weight:bold">{ret:+.2f}%</td>
            <td>{p.get('预测价格','')}</td>
            <td style="font-size:11px">{p.get('价格下限','')}-{p.get('价格上限','')}</td>
            <td>{p.get('信号','')}</td>
            <td style="font-size:11px;color:#94a3b8">{factors}</td>
        </tr>"""
    html += "</tbody></table>"

    html += '<p style="color:#64748b;font-size:11px;margin-top:12px">⚠️ 模型基于历史半年数据训练（随机森林+梯度提升+岭回归集成），仅供参考，不构成投资建议。上涨概率为模型对未来3个交易日方向的预测置信度。</p>'
    return html


def build_news_html(news_data):
    """生成舆情新闻 HTML"""
    if not news_data:
        return '<p style="color:#64748b">暂无舆情数据（请运行完整工作流采集）</p>'

    overall = news_data.get("整体情绪", {})
    stocks_news = news_data.get("个股舆情", {})

    # 情绪概览
    html = f"""
    <div class="sentiment-overview">
        <div class="sentiment-score">
            <div class="score-number">{overall.get('情绪指数', 0)}</div>
            <div class="score-label">情绪指数</div>
        </div>
        <div class="sentiment-detail">
            <div>{overall.get('情绪判断', '无数据')}</div>
            <div style="margin-top:8px;color:#94a3b8">
                总新闻 {overall.get('总新闻数', 0)} 条 |
                <span style="color:#ef4444">正面 {overall.get('正面', 0)}</span> |
                <span style="color:#22c55e">负面 {overall.get('负面', 0)}</span> |
                中性 {overall.get('中性', 0)}
            </div>
        </div>
    </div>"""

    # 重要事件汇总
    all_events = []
    for code, data in stocks_news.items():
        for news_item in data.get("新闻", [])[:3]:
            if news_item.get("事件标签"):
                all_events.append(
                    {
                        "股票": data["名称"],
                        "标题": news_item["标题"],
                        "摘要": news_item.get("摘要", ""),
                        "事件": "、".join(news_item["事件标签"]),
                        "情绪": news_item["情绪"],
                        "时间": news_item.get("时间", ""),
                        "来源": news_item.get("来源", ""),
                    }
                )

    if all_events:
        html += "<h3>🔔 重要事件追踪</h3>"
        html += '<div class="events-list">'
        for evt in all_events[:15]:
            emoji = (
                "🔴"
                if evt["情绪"] == "正面"
                else ("🟢" if evt["情绪"] == "负面" else "⚪")
            )
            summary = evt.get("摘要", "")
            html += f"""
            <div class="event-card">
                <div class="event-card-header">
                    <span class="event-stock">{evt['股票']}</span>
                    <span class="tag tag-yellow">{evt['事件']}</span>
                    <span class="event-meta">{emoji} {evt['时间']}</span>
                </div>
                <div class="event-card-title">{evt['标题']}</div>
                <div class="event-card-summary">{summary}</div>
                <div class="event-card-source">{evt.get('来源', '')}</div>
            </div>"""
        html += "</div>"

    # 各股新闻
    html += "<h3>📰 个股新闻动态</h3>"
    for code, data in stocks_news.items():
        news = data.get("新闻", [])
        if not news:
            continue
        stats = data.get("情绪统计", {})
        html += f"""
        <div class="stock-news-section">
            <div class="stock-news-header">
                <strong>{data['名称']}({code})</strong>
                <span style="margin-left:10px;font-size:12px;color:#94a3b8">
                    👍{stats.get('正面',0)} 👎{stats.get('负面',0)} ➖{stats.get('中性',0)}
                </span>
            </div>
            <div class="news-list">"""
        for n in news[:5]:
            emoji = {"正面": "🔴", "负面": "🟢", "中性": "⚪"}.get(n["情绪"], "⚪")
            tags = "".join(
                f'<span class="tag tag-sm">{t}</span>' for t in n.get("事件标签", [])
            )
            summary = n.get("摘要", "")
            source = n.get("来源", "")
            link = n.get("链接", "")
            title_html = (
                f'<a href="{link}" target="_blank" style="color:#e2e8f0;text-decoration:none;">{n["标题"]}</a>'
                if link
                else n["标题"]
            )
            html += f"""
                <div class="news-card">
                    <div class="news-card-header">
                        <span class="news-emoji">{emoji}</span>
                        <span class="news-card-title">{title_html}</span>
                        {tags}
                    </div>
                    <div class="news-card-summary">{summary}</div>
                    <div class="news-card-footer">
                        <span class="news-source">{source}</span>
                        <span class="news-time">{n.get('时间', '')}</span>
                    </div>
                </div>"""
        html += "</div></div>"

    return html


# ============ 主报告生成 ============


def generate_html_report(
    analysis, charts, news_data=None, us_data=None, pred_data=None
):
    date_str = analysis.get("分析日期", datetime.now().strftime("%Y-%m-%d"))
    realtime = analysis.get("实时分析", {})
    trend = analysis.get("趋势分析", {})
    stats = realtime.get("整体统计", {})

    # 构建新浪实时行情代码列表（供前端 JS 直接调用）
    sina_code_list = []
    for sector, stocks in STOCK_GROUPS.items():
        for code in stocks.keys():
            prefix = "sh" if code.startswith(("6", "9")) else "sz"
            sina_code_list.append(f"{prefix}{code}")
    sina_codes_str = ",".join(sina_code_list)

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta http-equiv="refresh" content="300">
<title>AI/光通信板块日报 - {date_str}</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif; background:#0f172a; color:#e2e8f0; padding:20px; max-width:1300px; margin:0 auto; }}
h1 {{ color:#60a5fa; text-align:center; margin:20px 0; font-size:28px; }}
h2 {{ color:#f8fafc; margin:20px 0 15px; padding-bottom:8px; border-bottom:2px solid #334155; font-size:20px; }}
h3 {{ color:#94a3b8; margin:20px 0 10px; font-size:16px; }}
.subtitle {{ text-align:center; color:#64748b; margin-bottom:20px; }}

/* 顶部Tab导航 */
.main-tabs {{ display:flex; gap:0; background:#1e293b; border-radius:12px; padding:4px; margin:20px 0; position:sticky; top:10px; z-index:100; box-shadow:0 4px 20px rgba(0,0,0,0.4); }}
.main-tab {{ flex:1; padding:12px 8px; text-align:center; border:none; background:transparent; color:#94a3b8; font-size:14px; font-weight:600; cursor:pointer; border-radius:10px; transition:all 0.3s; }}
.main-tab:hover {{ color:#e2e8f0; background:#334155; }}
.main-tab.active {{ background:#3b82f6; color:#ffffff; box-shadow:0 2px 8px rgba(59,130,246,0.4); }}
.tab-panel {{ display:none; animation:fadeIn 0.3s ease; }}
.tab-panel.active {{ display:block; }}
@keyframes fadeIn {{ from {{ opacity:0; transform:translateY(8px); }} to {{ opacity:1; transform:translateY(0); }} }}

/* 子Tab */
.sub-tabs {{ display:flex; gap:6px; flex-wrap:wrap; margin:12px 0; }}
.sub-tab {{ padding:8px 16px; border:1px solid #334155; background:#1e293b; color:#94a3b8; border-radius:20px; cursor:pointer; font-size:13px; transition:all 0.2s; }}
.sub-tab:hover {{ border-color:#60a5fa; color:#60a5fa; }}
.sub-tab.active {{ background:#3b82f6; color:#fff; border-color:#3b82f6; }}

.summary-cards {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(160px,1fr)); gap:12px; margin:20px 0; }}
.card {{ background:#1e293b; padding:18px; border-radius:12px; text-align:center; border:1px solid #334155; }}
.card .number {{ font-size:26px; font-weight:bold; margin:6px 0; }}
.card .label {{ color:#94a3b8; font-size:13px; }}
.up {{ color:#ef4444; }}
.down {{ color:#22c55e; }}
table {{ width:100%; border-collapse:collapse; margin:12px 0; background:#1e293b; border-radius:8px; overflow:hidden; }}
th {{ background:#334155; padding:10px 12px; text-align:left; font-size:12px; color:#94a3b8; }}
td {{ padding:8px 12px; border-bottom:1px solid #1e293b; font-size:13px; }}
tr:hover {{ background:#334155; }}
.chart-container {{ background:#1e293b; padding:12px; border-radius:12px; margin:12px 0; }}
.section {{ margin-bottom:20px; }}
.tag {{ display:inline-block; padding:3px 8px; border-radius:12px; font-size:11px; margin:2px; }}
.tag-blue {{ background:#1e3a5f; color:#60a5fa; }}
.tag-green {{ background:#14532d; color:#86efac; }}
.tag-red {{ background:#7f1d1d; color:#fca5a5; }}
.tag-yellow {{ background:#713f12; color:#fde047; }}
.tag-purple {{ background:#3b0764; color:#c084fc; }}
.tag-sm {{ background:#334155; color:#94a3b8; font-size:10px; padding:2px 6px; }}

.sector-card {{ background:#1e293b; border:1px solid #334155; border-radius:12px; padding:16px; margin:12px 0; }}
.sector-card h3 {{ color:#60a5fa; margin:0 0 8px; font-size:16px; }}
.sector-card .desc {{ color:#94a3b8; font-size:13px; line-height:1.6; margin-bottom:10px; }}
.chain-row {{ display:flex; align-items:center; gap:12px; margin:10px 0; flex-wrap:wrap; }}
.chain-box {{ background:#0f172a; border-radius:8px; padding:10px; flex:1; min-width:200px; }}
.chain-label {{ font-size:12px; color:#64748b; margin-bottom:6px; }}
.chain-arrow {{ color:#60a5fa; font-weight:bold; font-size:13px; white-space:nowrap; }}
.meta-row {{ margin:6px 0; }}

.stock-card {{ background:#1e293b; border:1px solid #334155; border-radius:12px; padding:14px; margin:10px 0; }}
.stock-header {{ display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; }}
.stock-name {{ font-size:16px; font-weight:bold; color:#f8fafc; }}
.stock-code {{ color:#64748b; font-size:13px; margin:0 8px; }}
.stock-price {{ text-align:right; }}
.price {{ font-size:20px; font-weight:bold; color:#60a5fa; margin-right:8px; }}
.stock-body {{ margin-top:10px; display:flex; gap:20px; flex-wrap:wrap; }}
.stock-info {{ flex:3; min-width:300px; font-size:13px; line-height:1.8; color:#cbd5e1; }}
.stock-metrics {{ flex:1; min-width:120px; display:flex; flex-direction:column; gap:6px; }}
.metric {{ display:flex; justify-content:space-between; background:#0f172a; padding:6px 10px; border-radius:6px; font-size:12px; }}
.metric-label {{ color:#64748b; }}
.risk-line {{ margin-top:4px; padding:6px 8px; background:#1a0000; border:1px solid #7f1d1d; border-radius:6px; }}

.sentiment-overview {{ display:flex; align-items:center; gap:20px; background:#1e293b; padding:20px; border-radius:12px; margin:12px 0; }}
.sentiment-score {{ text-align:center; }}
.score-number {{ font-size:36px; font-weight:bold; color:#60a5fa; }}
.score-label {{ color:#64748b; font-size:12px; }}
.sentiment-detail {{ font-size:16px; }}
.events-list {{ margin:10px 0; }}
.event-stock {{ color:#60a5fa; font-weight:bold; min-width:60px; }}
.event-meta {{ color:#64748b; font-size:12px; white-space:nowrap; }}
.stock-news-section {{ background:#1e293b; border-radius:10px; padding:12px; margin:8px 0; }}
.stock-news-header {{ border-bottom:1px solid #334155; padding-bottom:6px; margin-bottom:6px; }}
.news-emoji {{ flex-shrink:0; }}
.news-time {{ color:#475569; font-size:11px; white-space:nowrap; }}
.event-card {{ background:#1e293b; border:1px solid #334155; border-radius:10px; padding:12px 16px; margin:8px 0; }}
.event-card-header {{ display:flex; align-items:center; gap:8px; flex-wrap:wrap; margin-bottom:6px; }}
.event-card-title {{ font-size:14px; font-weight:bold; color:#f8fafc; margin-bottom:4px; }}
.event-card-summary {{ font-size:13px; color:#94a3b8; line-height:1.6; margin-bottom:6px; padding:6px 0; }}
.event-card-source {{ font-size:11px; color:#475569; }}
.news-card {{ background:#0f172a; border:1px solid #1e293b; border-radius:8px; padding:10px 12px; margin:6px 0; }}
.news-card-header {{ display:flex; align-items:center; gap:6px; flex-wrap:wrap; }}
.news-card-title {{ font-size:13px; font-weight:600; color:#e2e8f0; flex:1; }}
.news-card-title a:hover {{ color:#60a5fa !important; text-decoration:underline !important; }}
.news-card-summary {{ font-size:12px; color:#94a3b8; line-height:1.6; margin:6px 0; padding-left:22px; }}
.news-card-footer {{ display:flex; justify-content:space-between; padding-left:22px; }}
.news-source {{ font-size:11px; color:#475569; }}

/* 美股卡片 */
.us-stock-card {{ background:#1e293b; border:1px solid #334155; border-radius:12px; padding:16px; margin:12px 0; }}
.us-stock-header {{ display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; margin-bottom:8px; }}
.us-ticker {{ font-size:20px; font-weight:bold; color:#60a5fa; margin-right:10px; }}
.us-name {{ font-size:14px; color:#94a3b8; }}
.us-price-area {{ text-align:right; }}
.us-price {{ font-size:22px; font-weight:bold; color:#f8fafc; margin-right:10px; }}
.us-intro {{ font-size:13px; color:#94a3b8; line-height:1.6; margin-bottom:10px; padding:8px 0; border-bottom:1px solid #334155; }}
.us-metrics {{ display:flex; gap:16px; font-size:12px; color:#64748b; margin-bottom:10px; }}
.us-related {{ background:#0f172a; border-radius:8px; padding:12px; }}
.us-related-title {{ font-size:13px; font-weight:bold; color:#f59e0b; margin-bottom:8px; }}
.us-related-item {{ font-size:12px; color:#cbd5e1; padding:4px 0; line-height:1.6; }}

.footer {{ text-align:center; color:#475569; margin-top:40px; padding-top:20px; border-top:1px solid #334155; font-size:13px; }}

/* 刷新按钮区域 */
.refresh-bar {{ display:flex; justify-content:flex-end; align-items:center; gap:8px; margin-bottom:8px; flex-wrap:wrap; }}
.refresh-btn {{ padding:8px 18px; border:none; border-radius:8px; font-size:13px; font-weight:600; cursor:pointer; transition:all 0.3s; display:flex; align-items:center; gap:6px; }}
.refresh-btn.quick {{ background:linear-gradient(135deg,#3b82f6,#2563eb); color:#fff; }}
.refresh-btn.quick:hover {{ background:linear-gradient(135deg,#60a5fa,#3b82f6); transform:translateY(-1px); box-shadow:0 4px 12px rgba(59,130,246,0.4); }}
.refresh-btn.full {{ background:linear-gradient(135deg,#f59e0b,#d97706); color:#fff; }}
.refresh-btn.full:hover {{ background:linear-gradient(135deg,#fbbf24,#f59e0b); transform:translateY(-1px); box-shadow:0 4px 12px rgba(245,158,11,0.4); }}
.refresh-btn:disabled {{ opacity:0.6; cursor:not-allowed; transform:none !important; }}
.refresh-btn .spin {{ animation:spin 1s linear infinite; }}
@keyframes spin {{ from {{ transform:rotate(0deg); }} to {{ transform:rotate(360deg); }} }}
.refresh-toast {{ position:fixed; top:20px; right:20px; padding:14px 22px; border-radius:12px; font-size:14px; font-weight:600; z-index:9999; transition:all 0.4s ease; opacity:0; transform:translateY(-20px); pointer-events:none; max-width:400px; box-shadow:0 8px 30px rgba(0,0,0,0.5); }}
.refresh-toast.show {{ opacity:1; transform:translateY(0); pointer-events:auto; }}
.refresh-toast.info {{ background:#1e3a5f; color:#60a5fa; border:1px solid #3b82f6; }}
.refresh-toast.success {{ background:#14532d; color:#86efac; border:1px solid #22c55e; }}
.refresh-toast.error {{ background:#7f1d1d; color:#fca5a5; border:1px solid #ef4444; }}
.refresh-progress {{ margin-top:8px; background:#0f172a; border-radius:4px; height:6px; overflow:hidden; }}
.refresh-progress-bar {{ height:100%; background:linear-gradient(90deg,#3b82f6,#60a5fa); border-radius:4px; transition:width 0.5s ease; }}
.refresh-time {{ color:#475569; font-size:11px; }}
</style>
</head>
<body>

<h1>📊 AI/光通信板块深度日报</h1>
<p class="subtitle">生成时间：{date_str} | 聚焦：AI算力 · CPO · 光模块 · 光通信 · OCS · PCB</p>

<!-- 刷新按钮 + Toast提示 -->
<div class="refresh-bar">
    <span class="refresh-time" id="refreshTime"></span>
    <button class="refresh-btn quick" id="btnQuick" onclick="doRefresh('quick')">⚡ 快速刷新</button>
    <button class="refresh-btn full" id="btnFull" onclick="doRefresh('full')">🔄 完整刷新</button>
</div>
<div class="refresh-toast" id="toast"></div>

<!-- ========== 顶部Tab导航 ========== -->
<div class="main-tabs">
    <button class="main-tab active" onclick="switchTab('tab-overview')">🎯 今日概览</button>
    <button class="main-tab" onclick="switchTab('tab-sector')">🔗 板块分析</button>
    <button class="main-tab" onclick="switchTab('tab-stocks')">📋 个股档案</button>
    <button class="main-tab" onclick="switchTab('tab-trend')">📈 趋势分析</button>
    <button class="main-tab" onclick="switchTab('tab-news')">📰 舆情监测</button>
    <button class="main-tab" onclick="switchTab('tab-us')">🇺🇸 美股关联</button>
    <button class="main-tab" onclick="switchTab('tab-ai')">🤖 AI预测</button>
    <button class="main-tab" onclick="switchTab('tab-search')">🔍 个股搜索</button>
</div>

<!-- ========== TAB 1: 今日概览 ========== -->
<div id="tab-overview" class="tab-panel active">
<h2>🎯 今日概览</h2>
<div class="summary-cards">
    <div class="card"><div class="label">上涨</div><div class="number up" id="rt-up">{stats.get('上涨数','-')}</div></div>
    <div class="card"><div class="label">下跌</div><div class="number down" id="rt-down">{stats.get('下跌数','-')}</div></div>
    <div class="card"><div class="label">平均涨跌幅</div><div class="number {'up' if stats.get('平均涨跌幅',0)>=0 else 'down'}" id="rt-avg">{stats.get('平均涨跌幅','-')}%</div></div>
    <div class="card"><div class="label">总成交额</div><div class="number" style="color:#60a5fa" id="rt-amount">{stats.get('总成交额(亿)','-')}亿</div></div>
</div>
<div class="section">
    <div class="chart-container">{img_html(charts.get('sector'))}</div>
    {make_table(realtime.get('板块表现', []))}
</div>
<div class="section">
    <h2>📈 涨跌幅排行</h2>
    <div class="chart-container">{img_html(charts.get('stock_rank'))}</div>
    <h3>🔴 涨幅 Top 5</h3>
    {make_table(realtime.get('涨幅Top5', []))}
    <h3>🟢 跌幅 Top 5</h3>
    {make_table(realtime.get('跌幅Top5', []))}
    <h3>💎 成交额 Top 5</h3>
    {make_table(realtime.get('成交额Top5', []))}
</div>
</div>

<!-- ========== TAB 2: 板块分析 ========== -->
<div id="tab-sector" class="tab-panel">
<h2>🔗 板块介绍 & 上下游产业链</h2>
<div class="chart-container">{img_html(charts.get('volume_pie'))}</div>
{build_sector_intro_html()}
</div>

<!-- ========== TAB 3: 个股档案 ========== -->
<div id="tab-stocks" class="tab-panel">
<h2>📋 个股详细档案（按板块分类）</h2>
{build_stock_profiles_html(analysis)}
</div>

<!-- ========== TAB 4: 趋势分析 ========== -->
<div id="tab-trend" class="tab-panel">
<h2>📈 近5日走势排名</h2>
<div class="chart-container">{img_html(charts.get('history'))}</div>
{make_table(trend.get('个股趋势', []))}
<h3>⚡ 近期强势股（5日涨幅 &gt; 5%）</h3>
{make_table(trend.get('强势股', []))}
<h3>⚠️ 近期弱势股（5日跌幅 &gt; 5%）</h3>
{make_table(trend.get('弱势股', []))}
</div>

<!-- ========== TAB 5: 舆情监测 ========== -->
<div id="tab-news" class="tab-panel">
<h2>📰 舆情监测 & 情绪分析</h2>
<div class="chart-container">{img_html(charts.get('sentiment'))}</div>
{build_news_html(news_data)}
</div>

<!-- ========== TAB 6: 美股关联 ========== -->
<div id="tab-us" class="tab-panel">
<h2>🇺🇸 美股关联标的（前一交易日行情）</h2>
<p style="color:#94a3b8;margin-bottom:16px;">展示与A股光通信/AI产业链深度关联的美股标的，及其与国内上市公司的供应链关系</p>
{build_us_stocks_html(us_data)}
</div>

<!-- ========== TAB 7: AI预测 ========== -->
<div id="tab-ai" class="tab-panel">
<h2>🤖 机器学习预测（未来3个交易日）</h2>
<p style="color:#94a3b8;margin-bottom:12px;">基于历史半年数据，使用随机森林 + 梯度提升 + 岭回归集成模型预测</p>
{build_predictions_html(pred_data)}
</div>

<!-- ========== TAB 8: 个股搜索 ========== -->
<div id="tab-search" class="tab-panel">
<h2>🔍 个股搜索分析</h2>
<p style="color:#94a3b8;margin-bottom:16px;">输入任意A股6位代码，获取实时行情与简要分析（本地服务器支持全市场搜索）</p>
<div style="display:flex;gap:12px;margin-bottom:20px;flex-wrap:wrap;">
    <input type="text" id="searchInput" placeholder="输入股票代码，如 000001" maxlength="6" style="flex:1;min-width:200px;padding:12px 16px;border:1px solid #334155;border-radius:10px;background:#0f172a;color:#e2e8f0;font-size:15px;outline:none;">
    <button onclick="doSearch()" style="padding:12px 24px;border:none;border-radius:10px;background:linear-gradient(135deg,#3b82f6,#2563eb);color:#fff;font-size:15px;font-weight:600;cursor:pointer;">🔍 搜索分析</button>
</div>
<div id="searchResult"></div>
</div>

<div class="footer">
    <p>📊 AI/光通信板块数据工作流 | 自动生成 | 数据来源：新浪财经 & 东方财富</p>
    <p>⚠️ 以上数据仅供学习参考，不构成投资建议</p>
</div>

<script>
function switchTab(tabId) {{
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.main-tab').forEach(b => b.classList.remove('active'));
    document.getElementById(tabId).classList.add('active');
    event.currentTarget.classList.add('active');
    window.scrollTo({{top:0,behavior:'smooth'}});
}}
function switchSubTab(btn, panelId) {{
    btn.parentElement.querySelectorAll('.sub-tab').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    btn.parentElement.parentElement.querySelectorAll('.sub-tab-content').forEach(p => p.style.display='none');
    document.getElementById(panelId).style.display='block';
}}

/* ====== 刷新按钮逻辑 ====== */
let pollTimer = null;
const toast = document.getElementById('toast');
const btnQuick = document.getElementById('btnQuick');
const btnFull = document.getElementById('btnFull');

function showToast(msg, type, duration) {{
    toast.textContent = msg;
    toast.className = 'refresh-toast ' + type + ' show';
    if (duration) setTimeout(() => toast.classList.remove('show'), duration);
}}

function setButtonsDisabled(disabled) {{
    btnQuick.disabled = disabled;
    btnFull.disabled = disabled;
    if (disabled) {{
        btnQuick.innerHTML = '<span class="spin">⏳</span> 刷新中...';
        btnFull.innerHTML = '<span class="spin">⏳</span> 刷新中...';
    }} else {{
        btnQuick.innerHTML = '⚡ 快速刷新';
        btnFull.innerHTML = '🔄 完整刷新';
    }}
}}

function doRefresh(mode) {{
    const url = mode === 'full' ? '/api/refresh' : '/api/quick-refresh';
    const label = mode === 'full' ? '完整刷新（约60秒）' : '快速刷新（约20秒）';

    setButtonsDisabled(true);
    showToast('🔄 ' + label + '...', 'info');

    fetch(url)
        .then(r => r.json())
        .then(data => {{
            if (data.status === 'busy') {{
                showToast('⏳ ' + data.message, 'info', 3000);
                setButtonsDisabled(false);
                return;
            }}
            // 开始轮询状态
            pollTimer = setInterval(pollStatus, 2000);
        }})
        .catch(err => {{
            showToast('❌ 无法连接服务器，请确保 web_server.py 正在运行', 'error', 5000);
            setButtonsDisabled(false);
        }});
}}

function pollStatus() {{
    fetch('/api/status')
        .then(r => r.json())
        .then(data => {{
            if (data.running) {{
                const pct = Math.round((data.step / data.total_steps) * 100);
                showToast(data.progress + ' (' + pct + '%)', 'info');
            }} else {{
                clearInterval(pollTimer);
                pollTimer = null;
                if (data.last_result === 'success') {{
                    showToast('✅ 刷新成功！3秒后自动刷新页面...', 'success');
                    setTimeout(() => location.reload(), 3000);
                }} else if (data.last_result) {{
                    showToast('❌ ' + data.progress, 'error', 8000);
                    setButtonsDisabled(false);
                }}
            }}
        }})
        .catch(() => {{
            clearInterval(pollTimer);
            pollTimer = null;
            setButtonsDisabled(false);
        }});
}}

// 显示上次刷新时间
document.getElementById('refreshTime').textContent = '报告生成: {date_str}';

/* ====== 实时行情自动更新（30秒轮询，直连新浪） ====== */
const QUOTE_INTERVAL = 30000;
let quoteTimer = null;
const SINA_CODES = '{sina_codes_str}';

function fetchSinaQuotes() {{
    const scriptId = 'sina-quote-loader';
    const oldScript = document.getElementById(scriptId);
    if (oldScript) oldScript.remove();

    const script = document.createElement('script');
    script.id = scriptId;
    script.src = 'https://hq.sinajs.cn/list=' + SINA_CODES;
    script.onload = function() {{
        const data = parseSinaQuotes();
        updateQuotes(data);
        const now = new Date().toLocaleTimeString();
        document.getElementById('refreshTime').textContent =
            '报告生成: {date_str} | 行情更新: ' + now;
        script.remove();
    }};
    script.onerror = function() {{
        console.warn('新浪行情加载失败');
        script.remove();
    }};
    document.head.appendChild(script);
}}

function parseSinaQuotes() {{
    const quotes = {{}};
    const codes = SINA_CODES.split(',');
    for (const sinaCode of codes) {{
        const dataStr = window['hq_str_' + sinaCode];
        if (!dataStr) continue;
        const fields = dataStr.split(',');
        if (fields.length < 5) continue;
        const code6 = sinaCode.substring(2);
        const name = fields[0];
        const open = parseFloat(fields[1]) || 0;
        const prevClose = parseFloat(fields[2]) || 0;
        const price = parseFloat(fields[3]) || 0;
        const high = parseFloat(fields[4]) || 0;
        const low = parseFloat(fields[5]) || 0;
        const volume = parseInt(fields[8]) || 0;
        const amount = parseFloat(fields[9]) || 0;
        const changePct = prevClose > 0 ? parseFloat(((price - prevClose) / prevClose * 100).toFixed(2)) : 0;
        quotes[code6] = {{
            name: name,
            price: price,
            open: open,
            prev_close: prevClose,
            high: high,
            low: low,
            volume: volume,
            amount: amount,
            change_pct: changePct,
        }};
    }}
    return {{
        time: new Date().toLocaleTimeString(),
        count: Object.keys(quotes).length,
        quotes: quotes,
    }};
}}

function updateQuotes(data) {{
    const quotes = data.quotes || {{}};
    let upCount = 0, downCount = 0, totalChange = 0, totalAmount = 0;

    // 更新个股档案中的价格
    document.querySelectorAll('[data-stock-code]').forEach(el => {{
        const code = el.getAttribute('data-stock-code');
        const q = quotes[code];
        if (!q) return;
        el.textContent = q.price.toFixed(2);
        el.style.color = q.change_pct >= 0 ? '#ef4444' : '#22c55e';
    }});

    // 更新美股价格
    document.querySelectorAll('[data-us-ticker]').forEach(el => {{
        const ticker = el.getAttribute('data-us-ticker');
        const q = quotes[ticker];
        if (!q) return;
        el.textContent = '$' + q.price.toFixed(2);
        el.style.color = q.change_pct >= 0 ? '#ef4444' : '#22c55e';
    }});

    // 计算概览统计
    for (const q of Object.values(quotes)) {{
        if (q.change_pct > 0) upCount++;
        else if (q.change_pct < 0) downCount++;
        totalChange += q.change_pct;
        totalAmount += q.amount;
    }}
    const count = Object.keys(quotes).length;
    const avgChange = count > 0 ? (totalChange / count).toFixed(2) : '-';

    const upEl = document.getElementById('rt-up');
    const downEl = document.getElementById('rt-down');
    const avgEl = document.getElementById('rt-avg');
    const amountEl = document.getElementById('rt-amount');

    if (upEl) upEl.textContent = upCount;
    if (downEl) downEl.textContent = downCount;
    if (avgEl) {{
        avgEl.textContent = avgChange + '%';
        avgEl.className = 'number ' + (parseFloat(avgChange) >= 0 ? 'up' : 'down');
    }}
    if (amountEl) amountEl.textContent = (totalAmount / 1e8).toFixed(1) + '亿';
}}

function doSearch() {{
    const code = document.getElementById('searchInput').value.trim();
    const resultDiv = document.getElementById('searchResult');
    if (!code || !/^\d{{6}}$/.test(code)) {{
        resultDiv.innerHTML = '<p style="color:#fca5a5;">❌ 请输入6位数字股票代码</p>';
        return;
    }}
    const known = document.querySelector('[data-stock-code="' + code + '"]');
    if (known) {{
        document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
        document.querySelectorAll('.main-tab').forEach(b => b.classList.remove('active'));
        document.getElementById('tab-stocks').classList.add('active');
        window.scrollTo({{top:0,behavior:'smooth'}});
        setTimeout(() => {{ known.scrollIntoView({{behavior:'smooth',block:'center'}}); known.style.background='#1e3a5f'; setTimeout(()=>known.style.background='',2000); }}, 300);
        return;
    }}
    if (location.hostname === 'localhost' || location.hostname === '127.0.0.1') {{
        resultDiv.innerHTML = '<p style="color:#94a3b8;">⏳ 正在分析...</p>';
        fetch('/api/search?code=' + code)
            .then(r => r.json())
            .then(data => {{
                if (data.error) {{ resultDiv.innerHTML = '<p style="color:#fca5a5;">❌ ' + data.error + '</p>'; return; }}
                renderSearchResult(data);
            }})
            .catch(err => {{ resultDiv.innerHTML = '<p style="color:#fca5a5;">❌ 查询失败</p>'; }});
    }} else {{
        resultDiv.innerHTML = '<div class="stock-card"><p style="color:#94a3b8;">GitHub Pages 静态托管模式下无法实时查询任意股票。</p><p style="color:#94a3b8;margin-top:8px;">建议：</p><ul style="color:#cbd5e1;margin:8px 0;padding-left:20px;"><li>本地运行 <code style="background:#0f172a;padding:2px 6px;border-radius:4px;">python3 web_server.py</code> 后搜索任意股票</li><li>或访问 <a href="https://quote.eastmoney.com/concept/' + code + '.html" target="_blank" style="color:#60a5fa;">东方财富个股页面</a></li></ul></div>';
    }}
}}

function renderSearchResult(data) {{
    const q = data.行情;
    const color = q.涨跌幅 >= 0 ? '#ef4444' : '#22c55e';
    const sign = q.涨跌幅 >= 0 ? '+' : '';
    let newsHtml = '';
    if (data.新闻 && data.新闻.length > 0) {{
        newsHtml = '<h3 style="margin-top:16px;">📰 相关新闻</h3>';
        for (const n of data.新闻) {{
            newsHtml += '<div class="news-card" style="margin:8px 0;"><div style="font-size:13px;font-weight:600;color:#e2e8f0;">' + n.标题 + '</div><div style="font-size:12px;color:#94a3b8;margin:4px 0;">' + n.摘要 + '</div><div style="display:flex;justify-content:space-between;font-size:11px;color:#475569;"><span>' + n.来源 + '</span><span>' + n.时间 + '</span></div></div>';
        }}
    }}
    document.getElementById('searchResult').innerHTML =
        '<div class="stock-card">' +
        '<div class="stock-header"><div><span class="stock-name">' + q.名称 + '</span><span class="stock-code">' + data.代码 + '</span></div>' +
        '<div class="stock-price"><span class="price" style="color:' + color + ';">' + q.最新价.toFixed(2) + '</span><span style="color:' + color + ';font-size:15px;font-weight:bold;">' + sign + q.涨跌幅 + '%</span></div></div>' +
        '<div class="stock-body" style="margin-top:12px;"><div class="stock-metrics" style="flex-direction:row;flex-wrap:wrap;gap:12px;">' +
        '<div class="metric"><span class="metric-label">今开</span><span>' + q.今开.toFixed(2) + '</span></div>' +
        '<div class="metric"><span class="metric-label">最高</span><span>' + q.最高.toFixed(2) + '</span></div>' +
        '<div class="metric"><span class="metric-label">最低</span><span>' + q.最低.toFixed(2) + '</span></div>' +
        '<div class="metric"><span class="metric-label">昨收</span><span>' + q.昨收.toFixed(2) + '</span></div>' +
        '<div class="metric"><span class="metric-label">成交额</span><span>' + (q.成交额/1e8).toFixed(2) + '亿</span></div>' +
        '</div></div>' +
        '<div style="margin-top:12px;padding:10px;background:#0f172a;border-radius:8px;font-size:13px;color:#94a3b8;">状态: <span style="color:' + color + ';font-weight:bold;">' + data.分析.状态 + '</span> | 波动: ' + data.分析.波动 + '</div>' +
        newsHtml +
        '</div>';
}}

document.addEventListener('DOMContentLoaded', function() {{
    const inp = document.getElementById('searchInput');
    if (inp) inp.addEventListener('keypress', function(e) {{ if (e.key === 'Enter') doSearch(); }});
}});

// 启动自动刷新
quoteTimer = setInterval(fetchSinaQuotes, QUOTE_INTERVAL);
fetchSinaQuotes();
</script>
</body></html>"""

    path = os.path.join(OUTPUT_DIR, "report.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  📄 HTML 报告已保存: {path}")
    return path


def run_report():
    ensure_dirs()
    print("\n" + "=" * 60)
    print(f"📊 开始生成报告 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    today = datetime.now().strftime("%Y%m%d")

    # 加载分析结果
    analysis_path = os.path.join(DATA_DIR, f"analysis_{today}.json")
    if not os.path.exists(analysis_path):
        print(f"  ❌ 未找到分析结果: {analysis_path}")
        return None
    with open(analysis_path, "r", encoding="utf-8") as f:
        analysis = json.load(f)
    print(f"  📂 加载分析结果")

    # 加载舆情数据（可选）
    news_data = None
    news_path = os.path.join(DATA_DIR, f"news_{today}.json")
    if os.path.exists(news_path):
        with open(news_path, "r", encoding="utf-8") as f:
            news_data = json.load(f)
        print(f"  📂 加载舆情数据")
    else:
        print(f"  ⚠️ 未找到舆情数据（跳过）")

    # 生成图表
    print("\n🎨 生成图表...")
    charts = {
        "sector": chart_sector_performance(analysis),
        "stock_rank": chart_stock_heatmap(analysis),
        "history": chart_history_trend(analysis),
        "volume_pie": chart_volume_pie(analysis),
        "sentiment": chart_sentiment(news_data),
    }

    # 加载美股数据（可选）
    us_data = None
    us_path = os.path.join(DATA_DIR, f"us_stocks_{today}.json")
    if os.path.exists(us_path):
        with open(us_path, "r", encoding="utf-8") as f:
            us_data = json.load(f)
        print(f"  📂 加载美股数据")
    else:
        print(f"  ⚠️ 未找到美股数据（跳过）")

    # 加载预测数据（可选）
    pred_data = None
    pred_path = os.path.join(DATA_DIR, f"predictions_{today}.json")
    if os.path.exists(pred_path):
        with open(pred_path, "r", encoding="utf-8") as f:
            pred_data = json.load(f)
        print(f"  📂 加载ML预测数据")
    else:
        print(f"  ⚠️ 未找到ML预测数据（跳过）")

    # 生成报告
    print("\n📝 生成 HTML 报告...")
    report_path = generate_html_report(analysis, charts, news_data, us_data, pred_data)

    print(f"\n✅ 报告生成完成！")
    print(f"  📄 打开报告: open {report_path}")
    return report_path


if __name__ == "__main__":
    run_report()
