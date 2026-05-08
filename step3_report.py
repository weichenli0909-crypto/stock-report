"""
📊 第三步：可视化与报告生成
生成图表和 HTML 报告（含板块介绍、产业链、个股档案、舆情分析）
"""

import os
import json
import glob
import base64
from io import BytesIO
from datetime import datetime

import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager


def _setup_chinese_font():
    """跨平台中文字体设置：按优先级尝试，找不到就直接扫描系统字体文件。"""
    preferred = [
        "Arial Unicode MS",  # macOS 内置
        "PingFang SC",  # macOS
        "Heiti SC",  # macOS 黑体
        "Noto Sans CJK SC",  # Linux (GitHub Actions)
        "Noto Sans CJK JP",
        "Noto Serif CJK SC",
        "WenQuanYi Zen Hei",  # Linux 备选
        "WenQuanYi Micro Hei",
        "Microsoft YaHei",  # Windows
        "SimHei",
        "SimSun",
    ]
    # 第一轮：按名称设置
    plt.rcParams["font.sans-serif"] = preferred + plt.rcParams["font.sans-serif"]
    plt.rcParams["axes.unicode_minus"] = False

    # 第二轮：如果 font_manager 找不到上面任何字体，直接扫描系统字体文件路径
    available = {f.name for f in font_manager.fontManager.ttflist}
    if not any(name in available for name in preferred):
        # 典型的 Linux 中文字体路径
        candidate_paths = [
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansCJK.ttc",
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
            "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        ]
        import os as _os
        for p in candidate_paths:
            if _os.path.exists(p):
                try:
                    font_manager.fontManager.addfont(p)
                    fp = font_manager.FontProperties(fname=p)
                    plt.rcParams["font.sans-serif"] = [fp.get_name()] + plt.rcParams["font.sans-serif"]
                    print(f"  [字体] 已注册中文字体: {p} -> {fp.get_name()}")
                    break
                except Exception as e:
                    print(f"  [字体] 注册失败 {p}: {e}")


_setup_chinese_font()


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


def chart_sector_trend_line(analysis):
    """生成板块累计涨跌幅对比折线图"""
    sector_trend = analysis.get("板块走势", {})
    if not sector_trend:
        return None

    fig, ax = plt.subplots(figsize=(12, 6))
    colors = [
        "#ef4444",
        "#3b82f6",
        "#22c55e",
        "#f59e0b",
        "#a855f7",
        "#06b6d4",
        "#ec4899",
    ]

    for i, (sector, data) in enumerate(sector_trend.items()):
        dates = data.get("dates", [])
        values = data.get("values", [])
        if not dates or not values:
            continue
        # 只保留最近15个交易日，避免X轴太密
        if len(dates) > 15:
            dates = dates[-15:]
            values = values[-15:]
        color = colors[i % len(colors)]
        ax.plot(
            dates,
            values,
            label=sector,
            color=color,
            linewidth=2,
            marker="o",
            markersize=4,
        )

    ax.axhline(y=0, color="gray", linewidth=0.5, linestyle="--")
    ax.set_xlabel("日期", color="#94a3b8")
    ax.set_ylabel("累计涨跌幅 (%)", color="#94a3b8")
    ax.set_title(
        "各板块近15日累计涨跌幅走势对比",
        fontsize=14,
        fontweight="bold",
        color="#e2e8f0",
    )
    ax.legend(
        loc="upper left", facecolor="#1e293b", edgecolor="#334155", labelcolor="#e2e8f0"
    )
    ax.set_facecolor("#0f172a")
    fig.patch.set_facecolor("#0f172a")
    ax.tick_params(colors="#94a3b8")
    ax.grid(True, alpha=0.2, color="#334155")
    plt.xticks(rotation=45, ha="right")
    fig.tight_layout()
    path = os.path.join(OUTPUT_DIR, "sector_trend_line.png")
    fig.savefig(path, dpi=120, bbox_inches="tight")
    print("  [图表] 板块走势对比图已保存")
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


def chart_score_history(pred_data, days=15):
    """
    生成强势/弱势Top5股票的近N天AI评分走势组合图。
    读取最近N天的 predictions_*.json 构建历史序列。
    """
    if not pred_data:
        return None

    # 读取历史预测文件
    pred_files = sorted(glob.glob(os.path.join(DATA_DIR, "predictions_*.json")))
    if not pred_files:
        return None

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

    if len(history) < 2:
        return None

    dates = sorted(history.keys())

    # 获取当前强势Top5和弱势Top5
    top5 = pred_data.get("强势Top5", [])
    bottom5 = pred_data.get("弱势Top5", [])

    if not top5 and not bottom5:
        return None

    fig, axes = plt.subplots(2, 1, figsize=(14, 8), sharex=True)

    # 颜色池
    colors_top = ["#ef4444", "#f97316", "#eab308", "#f59e0b", "#fca5a5"]
    colors_btm = ["#22c55e", "#06b6d4", "#3b82f6", "#60a5fa", "#86efac"]

    # 强势走势
    ax_top = axes[0]
    for i, p in enumerate(top5):
        code = p.get("代码", "")
        name = p.get("名称", code)
        scores = [history[d].get(code, 50) for d in dates]
        ax_top.plot(dates, scores, label=name, color=colors_top[i % len(colors_top)],
                    linewidth=2.5, marker="o", markersize=4)

    ax_top.axhline(y=65, color="#ef4444", linewidth=1, linestyle="--", alpha=0.5)
    ax_top.axhline(y=50, color="#64748b", linewidth=0.8, linestyle="--", alpha=0.4)
    ax_top.fill_between(dates, 65, 100, alpha=0.05, color="#ef4444")
    ax_top.set_ylabel("AI评分", color="#94a3b8")
    ax_top.set_title(f"强势Top5 近{len(dates)}天AI评分走势", fontsize=14, fontweight="bold", color="#e2e8f0")
    ax_top.legend(loc="upper left", facecolor="#1e293b", edgecolor="#334155", labelcolor="#e2e8f0", fontsize=10)
    ax_top.set_facecolor("#0f172a")
    ax_top.tick_params(colors="#94a3b8")
    ax_top.grid(True, alpha=0.2, color="#334155")
    ax_top.set_ylim(30, 100)

    # 弱势走势
    ax_btm = axes[1]
    for i, p in enumerate(bottom5):
        code = p.get("代码", "")
        name = p.get("名称", code)
        scores = [history[d].get(code, 50) for d in dates]
        ax_btm.plot(dates, scores, label=name, color=colors_btm[i % len(colors_btm)],
                    linewidth=2.5, marker="o", markersize=4)

    ax_btm.axhline(y=35, color="#22c55e", linewidth=1, linestyle="--", alpha=0.5)
    ax_btm.axhline(y=50, color="#64748b", linewidth=0.8, linestyle="--", alpha=0.4)
    ax_btm.fill_between(dates, 0, 35, alpha=0.05, color="#22c55e")
    ax_btm.set_xlabel("日期", color="#94a3b8")
    ax_btm.set_ylabel("AI评分", color="#94a3b8")
    ax_btm.set_title(f"弱势Top5 近{len(dates)}天AI评分走势", fontsize=14, fontweight="bold", color="#e2e8f0")
    ax_btm.legend(loc="upper left", facecolor="#1e293b", edgecolor="#334155", labelcolor="#e2e8f0", fontsize=10)
    ax_btm.set_facecolor("#0f172a")
    fig.patch.set_facecolor("#0f172a")
    ax_btm.tick_params(colors="#94a3b8")
    ax_btm.grid(True, alpha=0.2, color="#334155")
    ax_btm.set_ylim(0, 70)

    plt.xticks(rotation=45, ha="right")
    fig.tight_layout()
    path = os.path.join(OUTPUT_DIR, "score_history.png")
    fig.savefig(path, dpi=120, bbox_inches="tight")
    print(f"  [图表] AI评分历史走势图已保存")
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


def build_stock_profiles_html(analysis, finance_map=None):
    """生成按板块分类的个股档案 HTML（含子Tab切换+财务简报）"""
    trends = analysis.get("趋势分析", {}).get("个股趋势", [])
    trend_map = {str(t["代码"]): t for t in trends}
    finance_map = finance_map or {}

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
            # 财务简报
            fin = finance_map.get(code, {})
            pe = fin.get("pe", "-")
            pb = fin.get("pb", "-")
            mv = fin.get("total_mv", 0)
            mv_str = f"{mv/1e8:.1f}亿" if mv else "-"
            # 资金流向
            fund = analysis.get("资金流向", {}).get("个股资金映射", {}).get(code, {})
            net = fund.get("净流入(亿)", 0)
            fund_color = "#ef4444" if net > 0 else ("#22c55e" if net < 0 else "#94a3b8")
            fund_sign = "+" if net > 0 else ""
            html += f"""
            <div class="stock-card" data-stock-code="{code}" data-stock-name="{profile.get('名称', name)}">
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
                        <div class="metric"><span class="metric-label">MACD</span><span>{trend.get('MACD', '-')}</span></div>
                        <div class="metric"><span class="metric-label">DIF</span><span>{trend.get('DIF', '-')}</span></div>
                        <div class="metric"><span class="metric-label">DEA</span><span>{trend.get('DEA', '-')}</span></div>
                        <div class="metric"><span class="metric-label">K</span><span>{trend.get('K', '-')}</span></div>
                        <div class="metric"><span class="metric-label">D</span><span>{trend.get('D', '-')}</span></div>
                        <div class="metric"><span class="metric-label">J</span><span>{trend.get('J', '-')}</span></div>
                        <div class="metric"><span class="metric-label">RSI6</span><span>{trend.get('RSI6', '-')}</span></div>
                        <div class="metric"><span class="metric-label">主力净流</span><span style="color:{fund_color}">{fund_sign}{net}亿</span></div>
                        <div class="metric"><span class="metric-label">PE</span><span>{pe}</span></div>
                        <div class="metric"><span class="metric-label">PB</span><span>{pb}</span></div>
                        <div class="metric"><span class="metric-label">市值</span><span>{mv_str}</span></div>
                    </div>
                </div>
            </div>"""
        html += "</div>"
    return html


def build_us_stocks_html(us_data):
    """生成美股关联标的 HTML（含最新新闻）"""
    if not us_data:
        return '<p style="color:#64748b">暂无美股数据（请运行完整工作流采集）</p>'

    stocks = us_data.get("美股行情", {})
    if not stocks:
        return '<p style="color:#64748b">暂无美股数据</p>'

    us_news = us_data.get("美股新闻", {})

    # ====== 大事件监控面板（置顶） ======
    all_events = []
    for ticker, news_info in us_news.items():
        stock_name = news_info.get("名称", ticker)
        for n in news_info.get("新闻", []):
            events = n.get("事件标签", [])
            if events:
                all_events.append({
                    "ticker": ticker,
                    "stock": stock_name,
                    "title": n.get("标题", ""),
                    "cn_hint": n.get("中文提示", ""),
                    "events": events,
                    "link": n.get("链接", ""),
                    "time": n.get("时间", ""),
                    "summary": n.get("摘要", "")[:100],
                })

    html = ""
    if all_events:
        event_colors = {"分红": "#f59e0b", "财报": "#3b82f6", "收购": "#ef4444", "建厂": "#22c55e", "大单": "#a855f7", "裁员": "#dc2626", "拆股": "#06b6d4", "回购": "#f97316", "上市/IPO": "#ec4899", "监管": "#dc2626"}
        event_emojis = {"分红": "💰", "财报": "📊", "收购": "🏢", "建厂": "🏭", "大单": "📝", "裁员": "✂️", "拆股": "🔄", "回购": "💵", "上市/IPO": "🎉", "监管": "⚖️"}

        html += """
        <div style="background:linear-gradient(135deg,rgba(239,68,68,0.08),rgba(59,130,246,0.08));border:2px solid rgba(239,68,68,0.3);border-radius:16px;padding:20px 24px;margin-bottom:24px;">
            <div style="display:flex;align-items:center;gap:10px;margin-bottom:16px;">
                <span style="font-size:24px;">🚨</span>
                <span style="font-size:18px;font-weight:800;color:#f8fafc;">大事件监控</span>
                <span style="font-size:12px;color:#94a3b8;background:#1e293b;padding:4px 10px;border-radius:10px;">""" + f'{len(all_events)} 条重大事件' + """</span>
            </div>
            <div style="display:grid;gap:10px;">"""

        for evt in all_events:
            evt_tags_html = ""
            for e in evt["events"]:
                c = event_colors.get(e, "#64748b")
                emoji = event_emojis.get(e, "⚡")
                evt_tags_html += f'<span style="display:inline-flex;align-items:center;gap:3px;padding:4px 10px;border-radius:12px;font-size:12px;font-weight:700;background:{c}22;color:{c};border:1px solid {c}44;">{emoji} {e}</span>'

            title_html = f'<a href="{evt["link"]}" target="_blank" style="color:#e2e8f0;text-decoration:none;">{evt["title"][:70]}</a>' if evt["link"] else evt["title"][:70]
            cn_html = f'<span style="color:#60a5fa;font-size:12px;margin-left:8px;">({evt["cn_hint"]})</span>' if evt["cn_hint"] else ""

            html += f"""
                <div style="background:rgba(15,23,42,0.6);border:1px solid #334155;border-radius:10px;padding:12px 16px;display:flex;align-items:flex-start;gap:12px;">
                    <div style="flex-shrink:0;display:flex;flex-direction:column;align-items:center;gap:4px;">
                        <span style="font-size:13px;font-weight:800;color:#60a5fa;">{evt["ticker"]}</span>
                        <span style="font-size:11px;color:#94a3b8;">{evt["stock"]}</span>
                    </div>
                    <div style="flex:1;">
                        <div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:6px;">{evt_tags_html}</div>
                        <div style="font-size:13px;line-height:1.5;color:#e2e8f0;">{title_html}{cn_html}</div>
                        <div style="font-size:11px;color:#64748b;margin-top:4px;">{evt.get("summary", "")}</div>
                    </div>
                </div>"""

        html += "</div></div>"
    else:
        html += """
        <div style="background:rgba(34,197,94,0.05);border:1px solid rgba(34,197,94,0.3);border-radius:12px;padding:16px 20px;margin-bottom:20px;text-align:center;">
            <span style="font-size:16px;">✅</span>
            <span style="color:#94a3b8;font-size:14px;margin-left:8px;">今日暂无重大事件（分红/财报/收购/建厂/大单等）</span>
        </div>"""

    # ====== 个股卡片 ======
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
            </div>"""

        # 美股新闻部分
        ticker_news = us_news.get(ticker, {}).get("新闻", [])
        if ticker_news:
            html += """
            <div class="us-news-section" style="margin-top:10px;padding:12px 14px;background:rgba(59,130,246,0.05);border-radius:8px;border-left:3px solid #3b82f6;">
                <div style="font-size:13px;font-weight:600;color:#3b82f6;margin-bottom:10px;">📰 最新重要信息</div>"""
            for news_item in ticker_news[:3]:
                title = news_item.get("标题", "")
                link = news_item.get("链接", "")
                source = news_item.get("来源", "")
                summary = news_item.get("摘要", "")
                pub_time = news_item.get("时间", "")
                cn_hint = news_item.get("中文提示", "")
                events = news_item.get("事件标签", [])
                # 截断过长的标题
                display_title = title[:80] + "..." if len(title) > 80 else title
                # 摘要截断
                display_summary = summary[:150] + "..." if len(summary) > 150 else summary
                # 事件标签 HTML
                event_tags = ""
                if events:
                    event_colors = {"分红": "#f59e0b", "财报": "#3b82f6", "收购": "#ef4444", "建厂": "#22c55e", "大单": "#a855f7", "裁员": "#dc2626", "拆股": "#06b6d4", "回购": "#f97316", "监管": "#dc2626"}
                    for evt in events:
                        c = event_colors.get(evt, "#64748b")
                        event_tags += f'<span style="display:inline-block;padding:2px 6px;border-radius:10px;font-size:10px;font-weight:600;background:{c}22;color:{c};margin-left:4px;">⚡{evt}</span>'
                html += '<div style="margin-bottom:10px;padding-bottom:8px;border-bottom:1px solid rgba(71,85,105,0.3);">'
                if link:
                    html += f'<div style="font-size:13px;line-height:1.5;"><a href="{link}" target="_blank" style="color:#e2e8f0;text-decoration:none;border-bottom:1px dashed #475569;font-weight:500;">{display_title}</a> <span style="color:#64748b;font-size:10px;">[{source}]</span>{event_tags}</div>'
                else:
                    html += f'<div style="font-size:13px;line-height:1.5;color:#e2e8f0;font-weight:500;">{display_title} <span style="color:#64748b;font-size:10px;">[{source}]</span>{event_tags}</div>'
                if cn_hint:
                    html += f'<div style="font-size:12px;color:#60a5fa;margin-top:3px;">🇨🇳 {cn_hint}</div>'
                if display_summary:
                    html += f'<div style="font-size:12px;color:#94a3b8;line-height:1.6;margin-top:4px;padding-left:2px;">{display_summary}</div>'
                if pub_time:
                    html += f'<div style="font-size:10px;color:#475569;margin-top:3px;">{pub_time}</div>'
                html += '</div>'
            html += "</div>"

        html += """
            <div class="us-related">
                <div class="us-related-title">🔗 关联A股标的</div>"""
        for code, desc in related.items():
            html += f'<div class="us-related-item"><span class="tag tag-blue">{code}</span> {desc}</div>'
        html += """
            </div>
        </div>"""

    return html


def build_factor_bars_html(p):
    """生成因子分解横向条形图 HTML"""
    def bar(val, color):
        w = max(2, min(100, val))
        return f'<div style="background:#0f172a;border-radius:3px;height:6px;overflow:hidden;width:80px;display:inline-block;vertical-align:middle;margin-left:6px;"><div style="background:{color};width:{w}%;height:100%;"></div></div>'
    mom = p.get("动量得分", 50)
    rel = p.get("相对强弱得分", 50)
    vol = p.get("量价得分", 50)
    loc = p.get("位置得分", 50)
    ext = p.get("外部得分", 50)
    return (
        f'<span style="font-size:11px;color:#94a3b8">'
        f'动量{mom:.0f}{bar(mom, "#ef4444")} '
        f'强弱{rel:.0f}{bar(rel, "#3b82f6")} '
        f'量价{vol:.0f}{bar(vol, "#22c55e")} '
        f'位置{loc:.0f}{bar(loc, "#f59e0b")} '
        f'外部{ext:.0f}{bar(ext, "#a855f7")}'
        f'</span>'
    )


def build_predictions_html(pred_data, backtest_data=None):
    """生成多因子评分结果 HTML（含回测质量评估）"""
    if not pred_data:
        return '<p style="color:#64748b">暂无评分数据（请运行完整工作流）</p>'

    summary = pred_data.get("汇总", {})
    sector_pred = pred_data.get("板块预测", {})
    top5 = pred_data.get("强势Top5", [])
    bottom5 = pred_data.get("弱势Top5", [])
    all_preds = pred_data.get("个股预测", {})

    total = summary.get("总股票数", 0)
    strong = summary.get("强势(AI≥65)", 0)
    weak = summary.get("弱势(AI≤35)", 0)
    neutral = max(0, total - strong - weak)

    html = f"""
    <div class="summary-cards">
        <div class="card"><div class="label">评分体系</div><div class="number" style="color:#60a5fa;font-size:18px">{pred_data.get('预测周期','')}</div></div>
        <div class="card"><div class="label">强势(AI≥65)</div><div class="number up">{strong}</div></div>
        <div class="card"><div class="label">弱势(AI≤35)</div><div class="number down">{weak}</div></div>
        <div class="card"><div class="label">中性</div><div class="number" style="color:#94a3b8">{neutral}</div></div>
        <div class="card"><div class="label">总标的</div><div class="number" style="color:#60a5fa">{total}</div></div>
    </div>"""

    # 回测质量展示
    if backtest_data:
        # 加载图表
        bt_charts = {}
        chart_path = os.path.join(DATA_DIR, "backtest_charts.json")
        if os.path.exists(chart_path):
            with open(chart_path, "r", encoding="utf-8") as f:
                bt_charts = json.load(f)

        # 历史模拟
        sim = backtest_data.get("历史模拟", {})
        if sim:
            html += "<h3>📈 历史 Walk-forward 模拟回测</h3>"
            html += '<p style="color:#94a3b8;font-size:12px;margin-bottom:8px;">基于历史数据每日收盘后计算AI评分，评估未来收益。每个周期独立统计。</p>'
            html += '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;margin:12px 0;">'
            for period, s in sim.items():
                spread = s.get("平均分位收益差", 0)
                ic = s.get("IC均值", 0)
                ir = s.get("IR", 0)
                ls_sharpe = s.get("多空年化夏普", 0)
                spread_color = "#ef4444" if spread > 0 else ("#22c55e" if spread < 0 else "#94a3b8")
                ic_color = "#ef4444" if ic > 0 else ("#22c55e" if ic < 0 else "#94a3b8")
                html += f"""
                <div class="card" style="text-align:left">
                    <div style="color:#94a3b8;font-size:12px;margin-bottom:4px;">{period}持仓 ({s.get('交易天数',0)}天)</div>
                    <div style="display:flex;justify-content:space-between;align-items:center">
                        <span style="color:#94a3b8;font-size:12px">分位收益差</span>
                        <span style="color:{spread_color};font-size:18px;font-weight:bold">{spread:+.2f}%</span>
                    </div>
                    <div style="display:flex;justify-content:space-between;margin-top:6px">
                        <span style="color:{ic_color};font-size:12px">IC {ic:.3f}</span>
                        <span style="color:#94a3b8;font-size:12px">IR {ir:.2f}</span>
                    </div>
                    <div style="margin-top:6px;font-size:12px;color:#64748b">
                        多空夏普 {ls_sharpe:.2f} | 样本 {s.get('总样本数',0):,} 条
                    </div>
                </div>"""
            html += "</div>"

            # 图表展示
            for period_label in ["1日", "3日", "5日"]:
                p = period_label.replace("日", "d")
                q_key = f"backtest_{p}_quintile"
                ls_key = f"backtest_{p}_longshort"
                ic_key = f"backtest_{p}_ic"
                has_any = any(k in bt_charts for k in [q_key, ls_key, ic_key])
                if not has_any:
                    continue
                html += f"<h3>📊 {period_label}持仓回测图表</h3>"
                html += '<div style="display:grid;grid-template-columns:1fr;gap:12px;margin:12px 0;">'
                if q_key in bt_charts:
                    html += f'<div class="chart-container"><img src="data:image/png;base64,{bt_charts[q_key]}" style="max-width:100%;border-radius:8px;"></div>'
                if ls_key in bt_charts:
                    html += f'<div class="chart-container"><img src="data:image/png;base64,{bt_charts[ls_key]}" style="max-width:100%;border-radius:8px;"></div>'
                if ic_key in bt_charts:
                    html += f'<div class="chart-container"><img src="data:image/png;base64,{bt_charts[ic_key]}" style="max-width:100%;border-radius:8px;"></div>'
                html += "</div>"

        # 日常回测（如果有）
        daily = backtest_data.get("日常回测", {})
        if daily:
            html += "<h3>📈 近期预测回测</h3>"
            html += '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px;margin:12px 0;">'
            for period, s in daily.items():
                acc = s.get("平均方向准确率", 50)
                spread = s.get("平均分位收益差", 0)
                acc_color = "#ef4444" if acc >= 55 else ("#22c55e" if acc < 45 else "#94a3b8")
                html += f"""
                <div class="card" style="text-align:left">
                    <div style="color:#94a3b8;font-size:12px;margin-bottom:4px;">{period}持仓</div>
                    <div style="display:flex;justify-content:space-between;align-items:center">
                        <span style="color:#94a3b8;font-size:12px">方向准确率</span>
                        <span style="color:{acc_color};font-size:20px;font-weight:bold">{acc}%</span>
                    </div>
                    <div style="margin-top:6px;font-size:12px;color:#64748b">
                        样本 {s.get('总样本数',0)} 条 | 历史 {s.get('历史天数',0)} 天
                    </div>
                </div>"""
            html += "</div>"

    # 板块预测
    html += "<h3>📊 板块评分概览</h3>"
    html += '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:12px;margin:12px 0;">'
    for name, data in sector_pred.items():
        avg_score = data.get("平均AI评分", 50)
        strong_n = data.get("强势数", 0)
        weak_n = data.get("弱势数", 0)
        score_color = "#ef4444" if avg_score >= 65 else ("#22c55e" if avg_score <= 35 else "#94a3b8")
        bar_width = int(avg_score)
        html += f"""
        <div class="sector-card" style="margin:0">
            <h3 style="font-size:14px">{name}</h3>
            <div style="display:flex;justify-content:space-between;margin:8px 0">
                <span style="color:{score_color};font-size:20px;font-weight:bold">{avg_score:.1f}</span>
                <span style="color:#94a3b8;font-size:12px">{data.get('个股数',0)} 只</span>
            </div>
            <div style="background:#0f172a;border-radius:4px;height:8px;overflow:hidden">
                <div style="background:linear-gradient(90deg,#22c55e,#eab308,#ef4444);width:{bar_width}%;height:100%;border-radius:4px"></div>
            </div>
            <div style="display:flex;justify-content:space-between;font-size:11px;color:#64748b;margin-top:4px">
                <span>强势 {strong_n}</span>
                <span>弱势 {weak_n}</span>
            </div>
        </div>"""
    html += "</div>"

    # Top5 强势/弱势（含置信星级与预警）
    html += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin:16px 0">'
    html += "<div><h3>🔥 AI强势 Top5</h3>"
    for p in top5:
        score = p.get("AI评分", 50)
        stars = p.get("置信星级", 0)
        warn = p.get("信号预警", "")
        star_str = "⭐" * stars if stars else ""
        warn_html = f'<span style="display:inline-block;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:600;background:rgba(239,68,68,0.15);color:#ef4444;margin-left:6px;">{warn}</span>' if warn else ""
        delta_1d = p.get("较昨日变化")
        delta_html = ""
        if delta_1d is not None:
            d_color = "#ef4444" if delta_1d >= 0 else "#22c55e"
            d_sign = "+" if delta_1d >= 0 else ""
            delta_html = f'<span style="color:{d_color};font-size:11px;margin-left:6px;">{d_sign}{delta_1d:.1f}</span>'
        html += f"""<div class="stock-card" style="padding:10px;margin:6px 0">
            <div style="display:flex;justify-content:space-between;align-items:center">
                <div><strong>{p['名称']}</strong> <span style="color:#64748b;font-size:12px">{p['代码']}</span>{warn_html}</div>
                <div style="text-align:right"><span style="color:#ef4444;font-weight:bold;font-size:16px">{score:.1f}</span>{delta_html}<br><span style="font-size:11px;color:#f59e0b">{star_str}</span></div>
            </div>
            <div style="margin-top:6px">{build_factor_bars_html(p)}</div>
        </div>"""
    html += "</div>"

    html += "<div><h3>❄️ AI弱势 Top5</h3>"
    for p in bottom5:
        score = p.get("AI评分", 50)
        stars = p.get("置信星级", 0)
        warn = p.get("信号预警", "")
        star_str = "⭐" * stars if stars else ""
        warn_html = f'<span style="display:inline-block;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:600;background:rgba(34,197,94,0.15);color:#22c55e;margin-left:6px;">{warn}</span>' if warn else ""
        delta_1d = p.get("较昨日变化")
        delta_html = ""
        if delta_1d is not None:
            d_color = "#ef4444" if delta_1d >= 0 else "#22c55e"
            d_sign = "+" if delta_1d >= 0 else ""
            delta_html = f'<span style="color:{d_color};font-size:11px;margin-left:6px;">{d_sign}{delta_1d:.1f}</span>'
        html += f"""<div class="stock-card" style="padding:10px;margin:6px 0">
            <div style="display:flex;justify-content:space-between;align-items:center">
                <div><strong>{p['名称']}</strong> <span style="color:#64748b;font-size:12px">{p['代码']}</span>{warn_html}</div>
                <div style="text-align:right"><span style="color:#22c55e;font-weight:bold;font-size:16px">{score:.1f}</span>{delta_html}<br><span style="font-size:11px;color:#f59e0b">{star_str}</span></div>
            </div>
            <div style="margin-top:6px">{build_factor_bars_html(p)}</div>
        </div>"""
    html += "</div></div>"

    # 全部个股评分表格
    html += "<h3>📋 全部个股评分明细</h3>"
    html += "<table><thead><tr><th>代码</th><th>名称</th><th>最新价</th><th>AI评分</th><th>动量</th><th>相对强弱</th><th>量价</th><th>位置</th><th>外部</th><th>信号</th></tr></thead><tbody>"
    sorted_preds = sorted(
        all_preds.values(), key=lambda x: x.get("AI评分", 50), reverse=True
    )
    for p in sorted_preds:
        score = p.get("AI评分", 50)
        score_color = "#ef4444" if score >= 65 else ("#22c55e" if score <= 35 else "#94a3b8")
        html += f"""<tr>
            <td>{p.get('代码','')}</td>
            <td>{p.get('名称','')}</td>
            <td>{p.get('最新价','')}</td>
            <td style="color:{score_color};font-weight:bold">{score:.1f}</td>
            <td>{p.get('动量得分','-')}</td>
            <td>{p.get('相对强弱得分','-')}</td>
            <td>{p.get('量价得分','-')}</td>
            <td>{p.get('位置得分','-')}</td>
            <td>{p.get('外部得分','-')}</td>
            <td>{p.get('信号','')}</td>
        </tr>"""
    html += "</tbody></table>"

    html += '<p style="color:#64748b;font-size:11px;margin-top:12px">⚠️ AI评分为多因子综合百分位排名（0-100），非收益预测。由动量(30%) + 相对强弱(25%) + 量价(20%) + 位置(15%) + 外部(10%)加权构成。仅供学习参考，不构成投资建议。</p>'
    return html


def build_news_html(news_data):
    """生成舆情新闻 HTML（优化版：仪表盘+Top5速报+折叠+筛选）"""
    if not news_data:
        return '<p style="color:#64748b">暂无舆情数据（请运行完整工作流采集）</p>'

    overall = news_data.get("整体情绪", {})
    stocks_news = news_data.get("个股舆情", {})
    llm_provider = news_data.get("llm_provider", "")
    llm_time = news_data.get("llm_分析时间", "")

    # 统计全市场 LLM 覆盖率 & 收集所有新闻
    llm_total = 0
    llm_pos = 0
    llm_neg = 0
    all_news_flat = []  # 所有新闻扁平列表

    for _code, _data in stocks_news.items():
        for _n in _data.get("新闻", []):
            _n["_stock_name"] = _data.get("名称", "")
            _n["_stock_code"] = _code
            all_news_flat.append(_n)
            if _n.get("llm_score") is not None:
                llm_total += 1
                if _n.get("llm_score", 0) > 0:
                    llm_pos += 1
                elif _n.get("llm_score", 0) < 0:
                    llm_neg += 1

    llm_badge = ""
    if llm_provider:
        llm_badge = (
            f'<div style="margin-top:6px;font-size:12px;color:#a78bfa">'
            f'🤖 大模型点评：<b>{llm_provider.upper()}</b> 已点评 <b>{llm_total}</b> 条'
            f'（<span style="color:#ef4444">利好 {llm_pos}</span> / '
            f'<span style="color:#22c55e">利空 {llm_neg}</span>）'
            f'{"｜" + llm_time if llm_time else ""}'
            f'</div>'
        )

    html = ""

    # ====== A股大事件监控面板 ======
    a_events = []
    for _code, _data in stocks_news.items():
        for _n in _data.get("新闻", []):
            evts = _n.get("事件标签", [])
            if evts:
                a_events.append({
                    "stock": _data.get("名称", ""),
                    "code": _code,
                    "title": _n.get("标题", ""),
                    "events": evts,
                    "sentiment": _n.get("情绪", "中性"),
                    "link": _n.get("链接", ""),
                    "time": _n.get("时间", ""),
                })

    if a_events:
        event_colors_a = {"业绩": "#3b82f6", "分红": "#f59e0b", "收购": "#ef4444", "产能": "#22c55e", "订单": "#a855f7", "人事": "#f97316", "回购": "#06b6d4", "增减持": "#ec4899", "违规": "#dc2626", "政策": "#8b5cf6"}
        event_emojis_a = {"业绩": "📊", "分红": "💰", "收购": "🏢", "产能": "🏭", "订单": "📝", "人事": "👔", "回购": "💵", "增减持": "📈", "违规": "⚠️", "政策": "📋"}
        show_default = 3
        total_a_events = len(a_events)

        # 统计每种事件类型出现的次数
        a_event_type_counts = {}
        for evt in a_events:
            for e in evt["events"]:
                a_event_type_counts[e] = a_event_type_counts.get(e, 0) + 1

        # 事件类型筛选按钮
        filter_btns_html = '<button class="evt-filter-btn active" onclick="filterEventByType(\'all\',this,\'aEventsList\')">全部</button>'
        for etype, count in sorted(a_event_type_counts.items(), key=lambda x: -x[1]):
            c = event_colors_a.get(etype, "#64748b")
            emoji = event_emojis_a.get(etype, "⚡")
            filter_btns_html += f'<button class="evt-filter-btn" onclick="filterEventByType(\'{etype}\',this,\'aEventsList\')" style="--btn-color:{c};">{emoji}{etype} <span style="opacity:0.7">{count}</span></button>'

        html += f"""
    <div style="background:linear-gradient(135deg,rgba(59,130,246,0.08),rgba(168,85,247,0.08));border:2px solid rgba(59,130,246,0.3);border-radius:16px;padding:18px 22px;margin-bottom:20px;">
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;">
            <div style="display:flex;align-items:center;gap:10px;">
                <span style="font-size:22px;">🚨</span>
                <span style="font-size:16px;font-weight:800;color:var(--text-primary);">A股大事件监控</span>
                <span style="font-size:12px;color:var(--text-dim);background:var(--bg-tertiary);padding:3px 8px;border-radius:10px;">{total_a_events} 条</span>
            </div>
            <button onclick="toggleEventPanel(this,'aEventsMore')" style="padding:6px 14px;border:1px solid var(--border-color);background:var(--bg-secondary);color:var(--text-muted);border-radius:var(--radius-pill);cursor:pointer;font-size:12px;">{'展开全部 ▼' if total_a_events > show_default else ''}</button>
        </div>
        <div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:12px;">{filter_btns_html}</div>
        <div id="aEventsList" style="display:grid;gap:8px;">"""

        for i, evt in enumerate(a_events):
            hidden_style = ' style="display:none;"' if i >= show_default else ""
            extra_class = ' class="aEventsMore"' if i >= show_default else ""
            evt_tags_html = ""
            for e in evt["events"]:
                c = event_colors_a.get(e, "#64748b")
                emoji = event_emojis_a.get(e, "⚡")
                evt_tags_html += f'<span style="display:inline-flex;align-items:center;gap:2px;padding:3px 8px;border-radius:10px;font-size:11px;font-weight:600;background:{c}22;color:{c};">{emoji}{e}</span>'
            s_emoji = "🔴" if evt["sentiment"] == "正面" else ("🟢" if evt["sentiment"] == "负面" else "⚪")
            title_html = f'<a href="{evt["link"]}" target="_blank" style="color:var(--text-secondary);text-decoration:none;">{evt["title"][:65]}</a>' if evt["link"] else evt["title"][:65]

            html += f"""
            <div{extra_class}{hidden_style}>
                <div style="background:var(--bg-primary);border:1px solid var(--border-color);border-radius:8px;padding:10px 14px;display:flex;align-items:center;gap:10px;">
                    <div style="flex-shrink:0;text-align:center;min-width:60px;">
                        <div style="font-size:12px;font-weight:700;color:var(--accent-light);">{evt["code"]}</div>
                        <div style="font-size:11px;color:var(--text-dim);">{evt["stock"]}</div>
                    </div>
                    <div style="display:flex;gap:4px;flex-shrink:0;">{evt_tags_html}</div>
                    <div style="flex:1;font-size:13px;color:var(--text-secondary);">{s_emoji} {title_html}</div>
                </div>
            </div>"""

        html += "</div></div>"

    # ====== 第一块：情绪仪表盘 ======
    score = overall.get('情绪指数', 50)
    total_news = overall.get('总新闻数', 0)
    pos_count = overall.get('正面', 0)
    neg_count = overall.get('负面', 0)
    neu_count = overall.get('中性', 0)
    # 仪表盘颜色
    if score >= 65:
        gauge_color = "#ef4444"
        gauge_label = "偏乐观"
    elif score <= 35:
        gauge_color = "#22c55e"
        gauge_label = "偏悲观"
    else:
        gauge_color = "#f59e0b"
        gauge_label = "中性偏谨慎"

    pos_pct = round(pos_count / max(total_news, 1) * 100)
    neg_pct = round(neg_count / max(total_news, 1) * 100)
    neu_pct = 100 - pos_pct - neg_pct

    html += f"""
    <div style="display:grid;grid-template-columns:200px 1fr;gap:24px;align-items:center;background:var(--bg-card);padding:24px;border-radius:var(--radius-md);margin:14px 0;border:1px solid var(--border-color);">
        <div style="text-align:center;">
            <div style="position:relative;width:140px;height:140px;margin:0 auto;">
                <svg viewBox="0 0 120 120" style="transform:rotate(-90deg)">
                    <circle cx="60" cy="60" r="50" fill="none" stroke="var(--bg-tertiary)" stroke-width="12"/>
                    <circle cx="60" cy="60" r="50" fill="none" stroke="{gauge_color}" stroke-width="12"
                        stroke-dasharray="{score * 3.14} 314" stroke-linecap="round"/>
                </svg>
                <div style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);text-align:center;">
                    <div style="font-size:32px;font-weight:800;color:{gauge_color}">{score}</div>
                    <div style="font-size:11px;color:var(--text-dim)">{gauge_label}</div>
                </div>
            </div>
        </div>
        <div>
            <div style="font-size:18px;font-weight:700;color:var(--text-primary);margin-bottom:12px;">{overall.get('情绪判断', '市场情绪中性')}</div>
            <div style="display:flex;gap:6px;margin-bottom:10px;height:14px;border-radius:7px;overflow:hidden;">
                <div style="width:{pos_pct}%;background:#ef4444;" title="正面 {pos_count}条"></div>
                <div style="width:{neu_pct}%;background:#64748b;" title="中性 {neu_count}条"></div>
                <div style="width:{neg_pct}%;background:#22c55e;" title="负面 {neg_count}条"></div>
            </div>
            <div style="display:flex;gap:16px;font-size:13px;color:var(--text-muted);">
                <span>📰 总 {total_news} 条</span>
                <span style="color:#ef4444">🔴 正面 {pos_count}</span>
                <span style="color:#22c55e">🟢 负面 {neg_count}</span>
                <span>⚪ 中性 {neu_count}</span>
            </div>
            {llm_badge}
        </div>
    </div>"""

    # ====== 第二块：Top5 利好 / Top5 利空 速报（按股票去重） ======
    positive_news = [n for n in all_news_flat if n.get("情绪") == "正面" or (n.get("llm_score") or 0) > 0]
    negative_news = [n for n in all_news_flat if n.get("情绪") == "负面" or (n.get("llm_score") or 0) < 0]

    # 按股票聚合：同一只股票只出现一次，多条新闻合并，记录热度
    def aggregate_by_stock(news_list, is_positive=True):
        """按股票去重聚合，返回 [(stock_name, count, best_news, all_titles)]"""
        stock_map = {}  # stock_name -> {count, best_score, best_news, titles}
        for n in news_list:
            stock = n.get("_stock_name", "") or n.get("_stock_code", "")
            if not stock:
                continue
            if stock not in stock_map:
                stock_map[stock] = {"count": 0, "best_score": 0, "best_news": n, "titles": []}
            stock_map[stock]["count"] += 1
            stock_map[stock]["titles"].append(n.get("标题", "")[:40])
            s = n.get("llm_score", 0) or 0
            if is_positive and s > stock_map[stock]["best_score"]:
                stock_map[stock]["best_score"] = s
                stock_map[stock]["best_news"] = n
            elif not is_positive and s < stock_map[stock]["best_score"]:
                stock_map[stock]["best_score"] = s
                stock_map[stock]["best_news"] = n
        # 排序：正面按 best_score 降序 + count 降序，负面反过来
        items = list(stock_map.items())
        if is_positive:
            items.sort(key=lambda x: (x[1]["best_score"], x[1]["count"]), reverse=True)
        else:
            items.sort(key=lambda x: (x[1]["best_score"], -x[1]["count"]))
        return items

    pos_grouped = aggregate_by_stock(positive_news, is_positive=True)
    neg_grouped = aggregate_by_stock(negative_news, is_positive=False)

    html += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin:16px 0;">'

    # Top5 利好（按股票去重）
    html += '<div style="background:var(--bg-card);border:1px solid var(--border-color);border-radius:var(--radius-md);padding:16px;">'
    html += '<div style="font-size:15px;font-weight:700;color:#ef4444;margin-bottom:12px;">🔥 最重要利好 Top5</div>'
    for stock_name, info in pos_grouped[:5]:
        count = info["count"]
        n = info["best_news"]
        title = n.get("标题", "")[:55]
        llm_s = n.get("llm_score")
        reason = n.get("llm_reason", "")
        link = n.get("链接", "")
        # 热度标记：消息越多火越多
        heat = "🔥" * min(count, 5)
        heat_label = f'<span style="font-size:11px;color:#f97316;margin-left:4px;">{heat} {count}条利好</span>' if count > 1 else ""
        title_el = f'<a href="{link}" target="_blank" style="color:var(--text-secondary);text-decoration:none;">{title}</a>' if link else title
        score_el = f'<span style="color:#ef4444;font-weight:700;font-size:11px;margin-left:4px;">[+{llm_s}]</span>' if llm_s else ""
        reason_el = f'<div style="font-size:11px;color:var(--text-dim);margin-top:2px;padding-left:2px;">{reason[:60]}</div>' if reason else ""
        # 多条时展示其他标题摘要
        extra_titles = ""
        if count > 1:
            others = [t for t in info["titles"] if t != n.get("标题", "")[:40]][:2]
            if others:
                extra_titles = '<div style="font-size:11px;color:var(--text-dimmer);margin-top:3px;padding-left:2px;">另有: ' + ' | '.join(others) + '</div>'
        html += f'<div style="padding:8px 0;border-bottom:1px solid var(--border-light);"><div style="font-size:13px;line-height:1.5;"><span style="color:#ef4444;font-weight:700;margin-right:6px;">{stock_name}</span>{heat_label}</div><div style="font-size:13px;margin-top:4px;">{title_el}{score_el}</div>{reason_el}{extra_titles}</div>'
    if not pos_grouped:
        html += '<div style="color:var(--text-dim);font-size:13px;">今日暂无明显利好</div>'
    html += '</div>'

    # Top5 利空（按股票去重）
    html += '<div style="background:var(--bg-card);border:1px solid var(--border-color);border-radius:var(--radius-md);padding:16px;">'
    html += '<div style="font-size:15px;font-weight:700;color:#22c55e;margin-bottom:12px;">❄️ 最重要利空 Top5</div>'
    for stock_name, info in neg_grouped[:5]:
        count = info["count"]
        n = info["best_news"]
        title = n.get("标题", "")[:55]
        llm_s = n.get("llm_score")
        reason = n.get("llm_reason", "")
        link = n.get("链接", "")
        # 寒冷标记
        cold = "❄️" * min(count, 5)
        cold_label = f'<span style="font-size:11px;color:#06b6d4;margin-left:4px;">{cold} {count}条利空</span>' if count > 1 else ""
        title_el = f'<a href="{link}" target="_blank" style="color:var(--text-secondary);text-decoration:none;">{title}</a>' if link else title
        score_el = f'<span style="color:#22c55e;font-weight:700;font-size:11px;margin-left:4px;">[{llm_s}]</span>' if llm_s else ""
        reason_el = f'<div style="font-size:11px;color:var(--text-dim);margin-top:2px;padding-left:2px;">{reason[:60]}</div>' if reason else ""
        extra_titles = ""
        if count > 1:
            others = [t for t in info["titles"] if t != n.get("标题", "")[:40]][:2]
            if others:
                extra_titles = '<div style="font-size:11px;color:var(--text-dimmer);margin-top:3px;padding-left:2px;">另有: ' + ' | '.join(others) + '</div>'
        html += f'<div style="padding:8px 0;border-bottom:1px solid var(--border-light);"><div style="font-size:13px;line-height:1.5;"><span style="color:#22c55e;font-weight:700;margin-right:6px;">{stock_name}</span>{cold_label}</div><div style="font-size:13px;margin-top:4px;">{title_el}{score_el}</div>{reason_el}{extra_titles}</div>'
    if not neg_grouped:
        html += '<div style="color:var(--text-dim);font-size:13px;">今日暂无明显利空</div>'
    html += '</div></div>'

    # ====== 第三块：筛选工具栏 ======
    html += """
    <div style="display:flex;gap:10px;align-items:center;margin:20px 0 12px;flex-wrap:wrap;">
        <input type="text" id="newsFilter" placeholder="🔍 搜索股票名称/关键词..." oninput="filterNews()" style="flex:1;min-width:200px;padding:10px 14px;border:1px solid var(--border-color);border-radius:var(--radius-sm);background:var(--bg-input);color:var(--text-primary);font-size:13px;outline:none;">
        <button class="news-filter-btn active" onclick="filterNewsBySentiment('all',this)">全部</button>
        <button class="news-filter-btn" onclick="filterNewsBySentiment('正面',this)" style="color:#ef4444">🔴 利好</button>
        <button class="news-filter-btn" onclick="filterNewsBySentiment('负面',this)" style="color:#22c55e">🟢 利空</button>
        <button class="news-filter-btn" onclick="filterNewsBySentiment('中性',this)">⚪ 中性</button>
        <button class="news-filter-btn" onclick="toggleAllNews()" id="toggleAllBtn">📂 全部展开</button>
    </div>
    <style>
    .news-filter-btn{padding:8px 14px;border:1px solid var(--border-color);background:var(--bg-secondary);color:var(--text-muted);border-radius:var(--radius-pill);cursor:pointer;font-size:12px;font-weight:500;transition:all 0.2s;}
    .news-filter-btn:hover{border-color:var(--accent-light);color:var(--accent-light);}
    .news-filter-btn.active{background:var(--accent);color:#fff;border-color:var(--accent);}
    .news-accordion{background:var(--bg-card);border:1px solid var(--border-color);border-radius:var(--radius-md);margin:8px 0;overflow:hidden;transition:all 0.2s;}
    .news-accordion:hover{border-color:var(--accent-light);}
    .news-accordion-header{display:flex;justify-content:space-between;align-items:center;padding:14px 18px;cursor:pointer;user-select:none;transition:background 0.2s;}
    .news-accordion-header:hover{background:var(--bg-hover);}
    .news-accordion-body{max-height:0;overflow:hidden;transition:max-height 0.4s ease;}
    .news-accordion.open .news-accordion-body{max-height:2000px;}
    .news-accordion .arrow{transition:transform 0.3s;font-size:12px;color:var(--text-dim);}
    .news-accordion.open .arrow{transform:rotate(90deg);}
    .sentiment-bar{display:flex;gap:2px;height:6px;border-radius:3px;overflow:hidden;width:80px;}
    </style>"""

    # ====== 第四块：个股新闻（折叠式） ======
    html += '<div id="newsAccordionContainer">'
    for code, data in stocks_news.items():
        news = data.get("新闻", [])
        if not news:
            continue
        stats = data.get("情绪统计", {})
        pos_n = stats.get('正面', 0)
        neg_n = stats.get('负面', 0)
        neu_n = stats.get('中性', 0)
        total_n = pos_n + neg_n + neu_n
        # 情绪条
        pos_w = round(pos_n / max(total_n, 1) * 100)
        neg_w = round(neg_n / max(total_n, 1) * 100)
        neu_w = 100 - pos_w - neg_w
        # 主情绪判断
        if pos_n > neg_n:
            main_emoji = "🔴"
            main_sentiment = "正面"
        elif neg_n > pos_n:
            main_emoji = "🟢"
            main_sentiment = "负面"
        else:
            main_emoji = "⚪"
            main_sentiment = "中性"

        html += f"""
    <div class="news-accordion" data-stock-name="{data['名称']}" data-sentiment="{main_sentiment}">
        <div class="news-accordion-header" onclick="this.parentElement.classList.toggle('open')">
            <div style="display:flex;align-items:center;gap:10px;">
                <span class="arrow">▶</span>
                <strong style="color:var(--text-primary);font-size:14px;">{main_emoji} {data['名称']}</strong>
                <span style="color:var(--text-dim);font-size:12px;">{code}</span>
                <div class="sentiment-bar">
                    <div style="width:{pos_w}%;background:#ef4444;"></div>
                    <div style="width:{neu_w}%;background:#64748b;"></div>
                    <div style="width:{neg_w}%;background:#22c55e;"></div>
                </div>
            </div>
            <div style="display:flex;align-items:center;gap:8px;font-size:12px;color:var(--text-dim);">
                <span>👍{pos_n}</span><span>👎{neg_n}</span><span>➖{neu_n}</span>
                <span style="font-size:11px;">共{total_n}条</span>
            </div>
        </div>
        <div class="news-accordion-body">
            <div style="padding:8px 18px 16px;">"""

        for n in news[:5]:
            emoji = {"正面": "🔴", "负面": "🟢", "中性": "⚪"}.get(n["情绪"], "⚪")
            tags = "".join(
                f'<span class="tag tag-sm">{t}</span>' for t in n.get("事件标签", [])
            )
            summary = n.get("摘要", "")
            source = n.get("来源", "")
            link = n.get("链接", "")
            title_html = (
                f'<a href="{link}" target="_blank" style="color:var(--text-secondary);text-decoration:none;">{n["标题"]}</a>'
                if link
                else n["标题"]
            )
            # 大模型点评
            llm_html = ""
            llm_score = n.get("llm_score")
            llm_reason = n.get("llm_reason", "")
            if llm_score is not None:
                if llm_score > 0:
                    llm_color = "#ef4444"
                    llm_label = "利好"
                    llm_emoji = "📈"
                elif llm_score < 0:
                    llm_color = "#22c55e"
                    llm_label = "利空"
                    llm_emoji = "📉"
                else:
                    llm_color = "#94a3b8"
                    llm_label = "中性"
                    llm_emoji = "➖"
                reason_text = f"：{llm_reason}" if llm_reason else ""
                llm_html = (
                    f'<div style="margin:6px 0 0 22px;font-size:12px;'
                    f'background:rgba(167,139,250,0.08);border-left:3px solid #a78bfa;'
                    f'padding:6px 10px;border-radius:4px;">'
                    f'<span style="color:#a78bfa;font-weight:600;">🤖</span> '
                    f'<span style="color:{llm_color};font-weight:600;">{llm_emoji} {llm_label}（{llm_score:+d}）</span>'
                    f'<span style="color:#cbd5e1;">{reason_text}</span>'
                    f'</div>'
                )
            html += f"""
                <div class="news-card">
                    <div class="news-card-header">
                        <span class="news-emoji">{emoji}</span>
                        <span class="news-card-title">{title_html}</span>
                        {tags}
                    </div>
                    <div class="news-card-summary">{summary}</div>
                    {llm_html}
                    <div class="news-card-footer">
                        <span class="news-source">{source}</span>
                        <span class="news-time">{n.get('时间', '')}</span>
                    </div>
                </div>"""

        html += "</div></div></div>"

    html += '</div>'  # end newsAccordionContainer

    # ====== JS：筛选和展开/折叠逻辑 ======
    html += """
    <script>
    function filterNews() {
        const keyword = document.getElementById('newsFilter').value.toLowerCase();
        document.querySelectorAll('.news-accordion').forEach(el => {
            const name = el.getAttribute('data-stock-name').toLowerCase();
            const content = el.textContent.toLowerCase();
            el.style.display = (name.includes(keyword) || content.includes(keyword)) ? '' : 'none';
        });
    }
    function filterNewsBySentiment(sentiment, btn) {
        // 更新按钮状态
        document.querySelectorAll('.news-filter-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        document.querySelectorAll('.news-accordion').forEach(el => {
            if (sentiment === 'all') {
                el.style.display = '';
            } else {
                el.style.display = el.getAttribute('data-sentiment') === sentiment ? '' : 'none';
            }
        });
    }
    function toggleAllNews() {
        const containers = document.querySelectorAll('.news-accordion');
        const allOpen = [...containers].every(el => el.classList.contains('open'));
        containers.forEach(el => {
            if (allOpen) el.classList.remove('open');
            else el.classList.add('open');
        });
        document.getElementById('toggleAllBtn').textContent = allOpen ? '📂 全部展开' : '📁 全部折叠';
    }
    </script>"""

    return html


def build_fundflow_html(analysis):
    """生成资金流向分析 HTML"""
    fund = analysis.get("资金流向", {})
    if not fund:
        return '<p style="color:#64748b">暂无资金流向数据（请运行完整工作流采集）</p>'

    html = ""

    # 板块资金汇总
    sector_fund = fund.get("板块资金", [])
    if sector_fund:
        html += "<h3>📊 板块资金流向汇总</h3>"
        html += '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:12px;margin:12px 0;">'
        for s in sector_fund:
            net = s.get("主力净流入(亿)", 0)
            color = "#ef4444" if net >= 0 else "#22c55e"
            bar_pct = min(abs(net) * 5, 100)
            bar_color = "#ef4444" if net >= 0 else "#22c55e"
            html += f"""
            <div class="sector-card" style="margin:0">
                <h3 style="font-size:14px">{s['板块']}</h3>
                <div style="display:flex;justify-content:space-between;margin:8px 0">
                    <span style="color:{color};font-size:20px;font-weight:bold">{net:+.2f}亿</span>
                    <span style="color:#94a3b8;font-size:12px">{s.get('个股数',0)} 只</span>
                </div>
                <div style="background:#0f172a;border-radius:4px;height:8px;overflow:hidden">
                    <div style="background:{bar_color};width:{bar_pct}%;height:100%;border-radius:4px"></div>
                </div>
                <div style="display:flex;justify-content:space-between;font-size:11px;color:#64748b;margin-top:4px">
                    <span>流入 {s.get('流入(亿)',0):.2f}亿</span>
                    <span>流出 {s.get('流出(亿)',0):.2f}亿</span>
                </div>
            </div>"""
        html += "</div>"

    # Top5 流入/流出
    html += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin:16px 0">'
    html += "<div><h3>🔥 主力净流入 Top5</h3>"
    for p in fund.get("主力流入Top5", []):
        net = p.get("净流入(亿)", 0)
        html += f"""<div class="stock-card" style="padding:10px;margin:6px 0">
            <div style="display:flex;justify-content:space-between;align-items:center">
                <div><strong>{p['名称']}</strong> <span style="color:#64748b;font-size:12px">{p['代码']}</span></div>
                <div style="text-align:right"><span style="color:#ef4444;font-weight:bold;font-size:16px">+{net}亿</span><br><span style="font-size:11px;color:#94a3b8">涨跌幅 {p.get('涨跌幅','-')}%</span></div>
            </div>
        </div>"""
    html += "</div>"

    html += "<div><h3>❄️ 主力净流出 Top5</h3>"
    for p in fund.get("主力流出Top5", []):
        net = p.get("净流入(亿)", 0)
        html += f"""<div class="stock-card" style="padding:10px;margin:6px 0">
            <div style="display:flex;justify-content:space-between;align-items:center">
                <div><strong>{p['名称']}</strong> <span style="color:#64748b;font-size:12px">{p['代码']}</span></div>
                <div style="text-align:right"><span style="color:#22c55e;font-weight:bold;font-size:16px">{net}亿</span><br><span style="font-size:11px;color:#94a3b8">涨跌幅 {p.get('涨跌幅','-')}%</span></div>
            </div>
        </div>"""
    html += "</div></div>"

    html += '<p style="color:#64748b;font-size:11px;margin-top:12px">💡 资金流向数据基于东方财富实时统计，超大单+大单合计为主力资金。红色表示净流入，绿色表示净流出。</p>'
    return html


def build_sector_finance_html(analysis):
    """生成板块财务对比 HTML"""
    sector_finance = analysis.get("板块财务", {})
    if not sector_finance:
        return '<p style="color:#64748b">暂无财务对比数据（请运行完整工作流采集）</p>'

    html = ""

    for sector_name, data in sector_finance.items():
        stocks = data.get("个股列表", [])
        if not stocks:
            continue

        avg_pe = data.get("平均市盈率", "-")
        avg_pb = data.get("平均市净率", "-")
        total_mv = data.get("总市值(亿)", "-")

        html += f"""
        <div class="sector-card" style="margin:16px 0">
            <h3 style="color:#60a5fa;margin-bottom:10px">{sector_name}</h3>
            <div style="display:flex;gap:16px;margin-bottom:12px;flex-wrap:wrap">
                <div class="card" style="padding:10px 16px;min-width:120px"><div class="label">平均PE</div><div class="number" style="font-size:18px">{avg_pe}</div></div>
                <div class="card" style="padding:10px 16px;min-width:120px"><div class="label">平均PB</div><div class="number" style="font-size:18px">{avg_pb}</div></div>
                <div class="card" style="padding:10px 16px;min-width:120px"><div class="label">板块总市值</div><div class="number" style="font-size:18px;color:#60a5fa">{total_mv}亿</div></div>
                <div class="card" style="padding:10px 16px;min-width:120px"><div class="label">个股数</div><div class="number" style="font-size:18px">{data.get('个股数',0)}</div></div>
            </div>
            <table>
                <thead>
                    <tr><th>代码</th><th>名称</th><th>最新价</th><th>涨跌幅</th><th>PE</th><th>PB</th><th>总市值(亿)</th><th>换手率</th></tr>
                </thead>
                <tbody>"""
        for s in stocks:
            change = s.get("涨跌幅", "-")
            change_color = (
                "#ef4444"
                if isinstance(change, (int, float)) and change >= 0
                else "#22c55e"
            )
            html += f"""
                    <tr>
                        <td>{s['代码']}</td>
                        <td><strong>{s['名称']}</strong></td>
                        <td>{s.get('最新价', '-')}</td>
                        <td style="color:{change_color};font-weight:bold">{change}%</td>
                        <td>{s.get('市盈率', '-')}</td>
                        <td>{s.get('市净率', '-')}</td>
                        <td>{s.get('总市值(亿)', '-')}</td>
                        <td>{s.get('换手率', '-')}%</td>
                    </tr>"""
        html += "</tbody></table></div>"

    html += '<p style="color:#64748b;font-size:11px;margin-top:12px">💡 财务数据基于东方财富实时快照，PE/PB为动态数据。总市值按最新价计算。</p>'
    return html


# ============ 主报告生成 ============


def generate_html_report(
    analysis, charts, news_data=None, us_data=None, pred_data=None, backtest_data=None
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

    # 获取全市场财务数据（PE/PB/市值）
    finance_map = {}
    try:
        import akshare as ak

        spot_df = ak.stock_zh_a_spot_em()
        for _, row in spot_df.iterrows():
            code = str(row["代码"]).zfill(6)
            pe = row.get("市盈率-动态", "-")
            pb = row.get("市净率", "-")
            mv = row.get("总市值", 0)
            if pd.notna(pe) and float(pe) > 0:
                pe_val = round(float(pe), 1)
            else:
                pe_val = "-"
            if pd.notna(pb) and float(pb) > 0:
                pb_val = round(float(pb), 1)
            else:
                pb_val = "-"
            finance_map[code] = {
                "pe": pe_val,
                "pb": pb_val,
                "total_mv": float(mv) if pd.notna(mv) else 0,
            }
    except Exception:
        pass

    html = f"""<!DOCTYPE html>
<html lang="zh-CN" data-theme="dark">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta http-equiv="refresh" content="300">
<title>AI/光通信板块日报 - {date_str}</title>
<!-- OpenGraph 社交分享 -->
<meta property="og:title" content="📊 AI/光通信板块深度日报 - {date_str}">
<meta property="og:description" content="AI算力·CPO·光模块·光通信·OCS·PCB 板块数据分析、机器学习预测、舆情追踪">
<meta property="og:type" content="website">
<meta name="description" content="每日自动更新的AI/光通信板块股票分析日报，涵盖行情、舆情、美股联动、AI预测">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>📊</text></svg>">
<style>
/* ===== CSS Variables for Theme ===== */
:root {{
    --bg-primary: #0f172a;
    --bg-secondary: #1e293b;
    --bg-tertiary: #334155;
    --bg-card: #1e293b;
    --bg-hover: #334155;
    --bg-input: #0f172a;
    --text-primary: #f8fafc;
    --text-secondary: #e2e8f0;
    --text-muted: #94a3b8;
    --text-dim: #64748b;
    --text-dimmer: #475569;
    --border-color: #334155;
    --border-light: #1e293b;
    --accent: #3b82f6;
    --accent-light: #60a5fa;
    --accent-glow: rgba(59,130,246,0.4);
    --up-color: #ef4444;
    --down-color: #22c55e;
    --shadow-sm: 0 2px 8px rgba(0,0,0,0.3);
    --shadow-md: 0 4px 20px rgba(0,0,0,0.4);
    --shadow-lg: 0 8px 30px rgba(0,0,0,0.5);
    --glass-bg: rgba(30,41,59,0.8);
    --glass-border: rgba(51,65,85,0.5);
    --radius-sm: 8px;
    --radius-md: 12px;
    --radius-lg: 16px;
    --radius-pill: 20px;
}}

[data-theme="light"] {{
    --bg-primary: #f8fafc;
    --bg-secondary: #ffffff;
    --bg-tertiary: #f1f5f9;
    --bg-card: #ffffff;
    --bg-hover: #f1f5f9;
    --bg-input: #f1f5f9;
    --text-primary: #0f172a;
    --text-secondary: #1e293b;
    --text-muted: #64748b;
    --text-dim: #94a3b8;
    --text-dimmer: #cbd5e1;
    --border-color: #e2e8f0;
    --border-light: #f1f5f9;
    --accent: #2563eb;
    --accent-light: #3b82f6;
    --accent-glow: rgba(37,99,235,0.2);
    --up-color: #dc2626;
    --down-color: #16a34a;
    --shadow-sm: 0 2px 8px rgba(0,0,0,0.06);
    --shadow-md: 0 4px 20px rgba(0,0,0,0.08);
    --shadow-lg: 0 8px 30px rgba(0,0,0,0.1);
    --glass-bg: rgba(255,255,255,0.85);
    --glass-border: rgba(226,232,240,0.8);
    --radius-sm: 8px;
    --radius-md: 12px;
    --radius-lg: 16px;
    --radius-pill: 20px;
}}

* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",sans-serif; background:var(--bg-primary); color:var(--text-secondary); padding:0; max-width:1400px; margin:0 auto; line-height:1.6; transition:background 0.3s ease, color 0.3s ease; }}

/* ===== Professional Header ===== */
.site-header {{ background:var(--glass-bg); backdrop-filter:blur(20px); -webkit-backdrop-filter:blur(20px); border-bottom:1px solid var(--glass-border); padding:16px 24px; position:sticky; top:0; z-index:200; transition:all 0.3s ease; }}
.header-inner {{ display:flex; justify-content:space-between; align-items:center; max-width:1400px; margin:0 auto; }}
.header-brand {{ display:flex; align-items:center; gap:12px; }}
.header-logo {{ font-size:28px; }}
.header-title {{ font-size:18px; font-weight:700; color:var(--text-primary); letter-spacing:-0.5px; }}
.header-subtitle {{ font-size:12px; color:var(--text-muted); margin-top:2px; }}
.header-actions {{ display:flex; align-items:center; gap:10px; }}
.header-status {{ display:flex; align-items:center; gap:6px; font-size:12px; color:var(--text-muted); background:var(--bg-tertiary); padding:6px 12px; border-radius:var(--radius-pill); }}
.header-status .dot {{ width:8px; height:8px; border-radius:50%; background:#22c55e; animation:pulse 2s infinite; }}
@keyframes pulse {{ 0%,100% {{ opacity:1; }} 50% {{ opacity:0.5; }} }}

/* Theme Toggle */
.theme-toggle {{ width:44px; height:44px; border-radius:50%; border:1px solid var(--border-color); background:var(--bg-secondary); cursor:pointer; display:flex; align-items:center; justify-content:center; font-size:20px; transition:all 0.3s ease; }}
.theme-toggle:hover {{ background:var(--bg-tertiary); transform:scale(1.1); box-shadow:var(--shadow-sm); }}

.main-content {{ padding:20px 24px; }}

h1 {{ color:var(--accent-light); text-align:center; margin:20px 0; font-size:28px; font-weight:800; letter-spacing:-1px; }}
h2 {{ color:var(--text-primary); margin:24px 0 15px; padding-bottom:10px; border-bottom:2px solid var(--border-color); font-size:20px; font-weight:700; }}
h3 {{ color:var(--text-muted); margin:20px 0 10px; font-size:16px; font-weight:600; }}
.subtitle {{ text-align:center; color:var(--text-dim); margin-bottom:20px; font-size:14px; }}

/* ===== Tab Navigation - Scrollable on Mobile ===== */
.main-tabs {{ display:flex; gap:0; background:var(--bg-secondary); border-radius:var(--radius-lg); padding:5px; margin:20px 0; position:sticky; top:76px; z-index:100; box-shadow:var(--shadow-md); border:1px solid var(--border-color); overflow-x:auto; -webkit-overflow-scrolling:touch; scrollbar-width:none; }}
.main-tabs::-webkit-scrollbar {{ display:none; }}
.main-tab {{ flex:0 0 auto; padding:12px 16px; text-align:center; border:none; background:transparent; color:var(--text-muted); font-size:13px; font-weight:600; cursor:pointer; border-radius:10px; transition:all 0.3s ease; white-space:nowrap; }}
.main-tab:hover {{ color:var(--text-primary); background:var(--bg-tertiary); }}
.main-tab.active {{ background:var(--accent); color:#ffffff; box-shadow:0 2px 8px var(--accent-glow); }}
.tab-panel {{ display:none; animation:fadeIn 0.4s ease; }}
.tab-panel.active {{ display:block; }}
@keyframes fadeIn {{ from {{ opacity:0; transform:translateY(10px); }} to {{ opacity:1; transform:translateY(0); }} }}

/* 子Tab */
.sub-tabs {{ display:flex; gap:8px; flex-wrap:wrap; margin:16px 0; }}
.sub-tab {{ padding:8px 18px; border:1px solid var(--border-color); background:var(--bg-secondary); color:var(--text-muted); border-radius:var(--radius-pill); cursor:pointer; font-size:13px; font-weight:500; transition:all 0.2s ease; }}
.sub-tab:hover {{ border-color:var(--accent-light); color:var(--accent-light); transform:translateY(-1px); }}
.sub-tab.active {{ background:var(--accent); color:#fff; border-color:var(--accent); box-shadow:0 2px 8px var(--accent-glow); }}

/* ===== Cards ===== */
.summary-cards {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(160px,1fr)); gap:14px; margin:20px 0; }}
.card {{ background:var(--bg-card); padding:20px; border-radius:var(--radius-md); text-align:center; border:1px solid var(--border-color); transition:all 0.3s ease; position:relative; overflow:hidden; }}
.card::before {{ content:''; position:absolute; top:0; left:0; right:0; height:3px; background:linear-gradient(90deg, var(--accent), var(--accent-light)); opacity:0; transition:opacity 0.3s; }}
.card:hover {{ transform:translateY(-2px); box-shadow:var(--shadow-md); border-color:var(--accent-light); }}
.card:hover::before {{ opacity:1; }}
.card .number {{ font-size:28px; font-weight:800; margin:8px 0; letter-spacing:-1px; }}
.card .label {{ color:var(--text-muted); font-size:12px; font-weight:500; text-transform:uppercase; letter-spacing:0.5px; }}
.up {{ color:var(--up-color); }}
.down {{ color:var(--down-color); }}

/* ===== Tables ===== */
table {{ width:100%; border-collapse:collapse; margin:12px 0; background:var(--bg-card); border-radius:var(--radius-md); overflow:hidden; border:1px solid var(--border-color); }}
th {{ background:var(--bg-tertiary); padding:12px 14px; text-align:left; font-size:11px; color:var(--text-muted); font-weight:600; text-transform:uppercase; letter-spacing:0.5px; }}
td {{ padding:10px 14px; border-bottom:1px solid var(--border-light); font-size:13px; }}
tr {{ transition:background 0.2s; }}
tr:hover {{ background:var(--bg-hover); }}
tr:last-child td {{ border-bottom:none; }}

/* Responsive table */
@media (max-width: 768px) {{
    table {{ display:block; overflow-x:auto; white-space:nowrap; }}
}}

.chart-container {{ background:var(--bg-card); padding:16px; border-radius:var(--radius-md); margin:14px 0; border:1px solid var(--border-color); }}
.section {{ margin-bottom:24px; }}

/* ===== Tags ===== */
.tag {{ display:inline-block; padding:4px 10px; border-radius:var(--radius-pill); font-size:11px; margin:2px; font-weight:500; }}
.tag-blue {{ background:rgba(96,165,250,0.15); color:#60a5fa; }}
.tag-green {{ background:rgba(134,239,172,0.15); color:#86efac; }}
.tag-red {{ background:rgba(252,165,165,0.15); color:#fca5a5; }}
.tag-yellow {{ background:rgba(253,224,71,0.15); color:#fde047; }}
.tag-purple {{ background:rgba(192,132,252,0.15); color:#c084fc; }}
.tag-sm {{ background:var(--bg-tertiary); color:var(--text-muted); font-size:10px; padding:2px 6px; }}

[data-theme="light"] .tag-blue {{ background:rgba(37,99,235,0.1); color:#2563eb; }}
[data-theme="light"] .tag-green {{ background:rgba(22,163,74,0.1); color:#16a34a; }}
[data-theme="light"] .tag-red {{ background:rgba(220,38,38,0.1); color:#dc2626; }}
[data-theme="light"] .tag-yellow {{ background:rgba(202,138,4,0.1); color:#ca8a04; }}
[data-theme="light"] .tag-purple {{ background:rgba(147,51,234,0.1); color:#9333ea; }}

/* ===== Sector Cards ===== */
.sector-card {{ background:var(--bg-card); border:1px solid var(--border-color); border-radius:var(--radius-md); padding:18px; margin:14px 0; transition:all 0.3s ease; }}
.sector-card:hover {{ box-shadow:var(--shadow-sm); border-color:var(--accent-light); }}
.sector-card h3 {{ color:var(--accent-light); margin:0 0 10px; font-size:16px; }}
.sector-card .desc {{ color:var(--text-muted); font-size:13px; line-height:1.7; margin-bottom:12px; }}
.chain-row {{ display:flex; align-items:center; gap:12px; margin:12px 0; flex-wrap:wrap; }}
.chain-box {{ background:var(--bg-primary); border-radius:var(--radius-sm); padding:12px; flex:1; min-width:200px; border:1px solid var(--border-color); }}
.chain-label {{ font-size:12px; color:var(--text-dim); margin-bottom:6px; font-weight:600; }}
.chain-arrow {{ color:var(--accent-light); font-weight:bold; font-size:13px; white-space:nowrap; }}
.meta-row {{ margin:8px 0; }}

/* ===== Stock Cards ===== */
.stock-card {{ background:var(--bg-card); border:1px solid var(--border-color); border-radius:var(--radius-md); padding:16px; margin:12px 0; transition:all 0.3s ease; }}
.stock-card:hover {{ box-shadow:var(--shadow-sm); border-color:var(--accent-light); transform:translateY(-1px); }}
.stock-header {{ display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; }}
.stock-name {{ font-size:16px; font-weight:bold; color:var(--text-primary); }}
.stock-code {{ color:var(--text-dim); font-size:13px; margin:0 8px; }}
.stock-price {{ text-align:right; }}
.price {{ font-size:22px; font-weight:800; color:var(--accent-light); margin-right:8px; letter-spacing:-0.5px; }}
.stock-body {{ margin-top:12px; display:flex; gap:20px; flex-wrap:wrap; }}
.stock-info {{ flex:3; min-width:300px; font-size:13px; line-height:1.9; color:var(--text-muted); }}
.stock-metrics {{ flex:1; min-width:130px; display:flex; flex-direction:column; gap:6px; }}
.metric {{ display:flex; justify-content:space-between; background:var(--bg-primary); padding:7px 12px; border-radius:var(--radius-sm); font-size:12px; border:1px solid var(--border-color); }}
.metric-label {{ color:var(--text-dim); font-weight:500; }}
.risk-line {{ margin-top:6px; padding:8px 10px; background:rgba(127,29,29,0.1); border:1px solid rgba(127,29,29,0.3); border-radius:var(--radius-sm); }}

[data-theme="light"] .risk-line {{ background:rgba(254,202,202,0.3); border-color:rgba(220,38,38,0.2); }}

/* ===== Sentiment & News ===== */
.sentiment-overview {{ display:flex; align-items:center; gap:24px; background:var(--bg-card); padding:24px; border-radius:var(--radius-md); margin:14px 0; border:1px solid var(--border-color); }}
.sentiment-score {{ text-align:center; }}
.score-number {{ font-size:40px; font-weight:800; color:var(--accent-light); letter-spacing:-1px; }}
.score-label {{ color:var(--text-dim); font-size:12px; font-weight:500; }}
.sentiment-detail {{ font-size:16px; font-weight:600; color:var(--text-primary); }}
.events-list {{ margin:12px 0; }}
.event-stock {{ color:var(--accent-light); font-weight:bold; min-width:60px; }}
.event-meta {{ color:var(--text-dim); font-size:12px; white-space:nowrap; }}
.stock-news-section {{ background:var(--bg-card); border-radius:var(--radius-md); padding:14px; margin:10px 0; border:1px solid var(--border-color); }}
.stock-news-header {{ border-bottom:1px solid var(--border-color); padding-bottom:8px; margin-bottom:8px; font-weight:600; }}
.news-emoji {{ flex-shrink:0; }}
.news-time {{ color:var(--text-dimmer); font-size:11px; white-space:nowrap; }}
.event-card {{ background:var(--bg-card); border:1px solid var(--border-color); border-radius:var(--radius-md); padding:14px 18px; margin:10px 0; transition:all 0.2s ease; }}
.event-card:hover {{ border-color:var(--accent-light); }}
.event-card-header {{ display:flex; align-items:center; gap:8px; flex-wrap:wrap; margin-bottom:8px; }}
.event-card-title {{ font-size:14px; font-weight:bold; color:var(--text-primary); margin-bottom:4px; }}
.event-card-summary {{ font-size:13px; color:var(--text-muted); line-height:1.7; margin-bottom:8px; padding:6px 0; }}
.event-card-source {{ font-size:11px; color:var(--text-dimmer); }}
.news-card {{ background:var(--bg-primary); border:1px solid var(--border-color); border-radius:var(--radius-sm); padding:12px 14px; margin:8px 0; transition:all 0.2s ease; }}
.news-card:hover {{ border-color:var(--accent-light); }}
.news-card-header {{ display:flex; align-items:center; gap:6px; flex-wrap:wrap; }}
.news-card-title {{ font-size:13px; font-weight:600; color:var(--text-secondary); flex:1; }}
.news-card-title a:hover {{ color:var(--accent-light) !important; text-decoration:underline !important; }}
.news-card-summary {{ font-size:12px; color:var(--text-muted); line-height:1.7; margin:6px 0; padding-left:22px; }}
.news-card-footer {{ display:flex; justify-content:space-between; padding-left:22px; }}
.news-source {{ font-size:11px; color:var(--text-dimmer); }}

/* ===== US Stock Cards ===== */
.us-stock-card {{ background:var(--bg-card); border:1px solid var(--border-color); border-radius:var(--radius-md); padding:18px; margin:14px 0; transition:all 0.3s ease; }}
.us-stock-card:hover {{ box-shadow:var(--shadow-sm); border-color:var(--accent-light); }}
.us-stock-header {{ display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; margin-bottom:10px; }}
.us-ticker {{ font-size:22px; font-weight:800; color:var(--accent-light); margin-right:10px; letter-spacing:-0.5px; }}
.us-name {{ font-size:14px; color:var(--text-muted); }}
.us-price-area {{ text-align:right; }}
.us-price {{ font-size:24px; font-weight:800; color:var(--text-primary); margin-right:10px; letter-spacing:-0.5px; }}
.us-intro {{ font-size:13px; color:var(--text-muted); line-height:1.7; margin-bottom:12px; padding:10px 0; border-bottom:1px solid var(--border-color); }}
.us-metrics {{ display:flex; gap:16px; font-size:12px; color:var(--text-dim); margin-bottom:12px; flex-wrap:wrap; }}
.us-related {{ background:var(--bg-primary); border-radius:var(--radius-sm); padding:14px; border:1px solid var(--border-color); }}
.us-related-title {{ font-size:13px; font-weight:bold; color:#f59e0b; margin-bottom:8px; }}
.us-related-item {{ font-size:12px; color:var(--text-muted); padding:4px 0; line-height:1.7; }}

/* ===== Footer ===== */
.footer {{ text-align:center; color:var(--text-dimmer); margin-top:60px; padding:30px 20px; border-top:1px solid var(--border-color); font-size:13px; }}
.footer-brand {{ font-size:16px; font-weight:700; color:var(--text-muted); margin-bottom:8px; }}
.footer-links {{ margin:12px 0; display:flex; justify-content:center; gap:20px; flex-wrap:wrap; }}
.footer-links a {{ color:var(--accent-light); text-decoration:none; font-size:13px; transition:color 0.2s; }}
.footer-links a:hover {{ color:var(--accent); text-decoration:underline; }}

/* ===== Refresh Controls ===== */
.refresh-bar {{ display:flex; justify-content:flex-end; align-items:center; gap:10px; margin-bottom:10px; flex-wrap:wrap; }}
.refresh-btn {{ padding:10px 20px; border:none; border-radius:var(--radius-sm); font-size:13px; font-weight:600; cursor:pointer; transition:all 0.3s ease; display:flex; align-items:center; gap:6px; }}
.refresh-btn.quick {{ background:linear-gradient(135deg,#3b82f6,#2563eb); color:#fff; }}
.refresh-btn.quick:hover {{ background:linear-gradient(135deg,#60a5fa,#3b82f6); transform:translateY(-2px); box-shadow:0 4px 16px rgba(59,130,246,0.4); }}
.refresh-btn.full {{ background:linear-gradient(135deg,#f59e0b,#d97706); color:#fff; }}
.refresh-btn.full:hover {{ background:linear-gradient(135deg,#fbbf24,#f59e0b); transform:translateY(-2px); box-shadow:0 4px 16px rgba(245,158,11,0.4); }}
.refresh-btn:disabled {{ opacity:0.6; cursor:not-allowed; transform:none !important; }}
.refresh-btn .spin {{ animation:spin 1s linear infinite; }}
@keyframes spin {{ from {{ transform:rotate(0deg); }} to {{ transform:rotate(360deg); }} }}
.refresh-toast {{ position:fixed; top:80px; right:20px; padding:16px 24px; border-radius:var(--radius-md); font-size:14px; font-weight:600; z-index:9999; transition:all 0.4s ease; opacity:0; transform:translateY(-20px); pointer-events:none; max-width:400px; box-shadow:var(--shadow-lg); backdrop-filter:blur(10px); }}
.refresh-toast.show {{ opacity:1; transform:translateY(0); pointer-events:auto; }}
.refresh-toast.info {{ background:rgba(30,58,95,0.95); color:#60a5fa; border:1px solid #3b82f6; }}
.refresh-toast.success {{ background:rgba(20,83,45,0.95); color:#86efac; border:1px solid #22c55e; }}
.refresh-toast.error {{ background:rgba(127,29,29,0.95); color:#fca5a5; border:1px solid #ef4444; }}
.refresh-progress {{ margin-top:8px; background:var(--bg-primary); border-radius:4px; height:6px; overflow:hidden; }}
.refresh-progress-bar {{ height:100%; background:linear-gradient(90deg,#3b82f6,#60a5fa); border-radius:4px; transition:width 0.5s ease; }}
.refresh-time {{ color:var(--text-dimmer); font-size:11px; }}

/* ===== Scroll to Top Button ===== */
.scroll-top {{ position:fixed; bottom:30px; right:30px; width:48px; height:48px; border-radius:50%; background:var(--accent); color:#fff; border:none; cursor:pointer; font-size:20px; display:flex; align-items:center; justify-content:center; box-shadow:0 4px 16px var(--accent-glow); opacity:0; transform:translateY(20px); transition:all 0.3s ease; z-index:1000; }}
.scroll-top.visible {{ opacity:1; transform:translateY(0); }}
.scroll-top:hover {{ transform:translateY(-3px) scale(1.1); box-shadow:0 6px 24px var(--accent-glow); }}

/* Event filter buttons */
.evt-filter-btn{{padding:6px 12px;border:1px solid var(--border-color);background:var(--bg-secondary);color:var(--text-muted);border-radius:var(--radius-pill);cursor:pointer;font-size:12px;font-weight:500;transition:all 0.2s;}}
.evt-filter-btn:hover{{border-color:var(--btn-color,var(--accent-light));color:var(--btn-color,var(--accent-light));}}
.evt-filter-btn.active{{background:var(--btn-color,var(--accent));color:#fff;border-color:var(--btn-color,var(--accent));}}

/* ===== Mobile Responsive ===== */
@media (max-width: 768px) {{
    .site-header {{ padding:12px 16px; }}
    .header-title {{ font-size:15px; }}
    .header-subtitle {{ display:none; }}
    .main-content {{ padding:12px 16px; }}
    .main-tabs {{ top:60px; padding:4px; gap:0; }}
    .main-tab {{ padding:10px 12px; font-size:12px; }}
    h1 {{ font-size:22px; }}
    h2 {{ font-size:18px; }}
    .summary-cards {{ grid-template-columns:repeat(2,1fr); gap:10px; }}
    .card .number {{ font-size:22px; }}
    .stock-body {{ flex-direction:column; }}
    .stock-info {{ min-width:100%; }}
    .stock-metrics {{ flex-direction:row; flex-wrap:wrap; }}
    .metric {{ min-width:calc(50% - 4px); }}
    .chain-row {{ flex-direction:column; }}
    .chain-arrow {{ text-align:center; }}
    .sentiment-overview {{ flex-direction:column; text-align:center; }}
    .us-metrics {{ flex-wrap:wrap; }}
    .footer-links {{ flex-direction:column; gap:10px; }}
    .scroll-top {{ bottom:20px; right:20px; width:42px; height:42px; font-size:18px; }}
    .refresh-bar {{ justify-content:center; }}
}}

@media (max-width: 480px) {{
    .summary-cards {{ grid-template-columns:1fr 1fr; }}
    .header-actions {{ gap:6px; }}
    .header-status {{ display:none; }}
}}
</style>
</head>
<body>

<!-- ===== Professional Sticky Header ===== -->
<header class="site-header">
    <div class="header-inner">
        <div class="header-brand">
            <span class="header-logo">📊</span>
            <div>
                <div class="header-title">AI / 光通信板块深度日报</div>
                <div class="header-subtitle">{date_str} | AI算力 · CPO · 光模块 · 光通信 · OCS · PCB</div>
            </div>
        </div>
        <div class="header-actions">
            <div class="header-status">
                <span class="dot"></span>
                <span id="headerRefreshTime">实时更新中</span>
            </div>
            <button class="theme-toggle" id="themeToggle" onclick="toggleTheme()" title="切换亮色/暗色主题">🌙</button>
        </div>
    </div>
</header>

<div class="main-content">

<div class="refresh-bar">
    <span class="refresh-time" id="refreshTime"></span>
    <button class="refresh-btn quick" id="btnQuick" onclick="doRefresh('quick')">⚡ 快速刷新</button>
    <button class="refresh-btn full" id="btnFull" onclick="doRefresh('full')">🔄 完整刷新</button>
</div>
<div class="refresh-toast" id="toast"></div>

<!-- ========== 顶部Tab导航 ========== -->
<div class="main-tabs" id="mainTabs">
    <button class="main-tab active" onclick="switchTab('tab-overview')">🎯 今日概览</button>
    <button class="main-tab" onclick="switchTab('tab-sector')">🔗 板块分析</button>
    <button class="main-tab" onclick="switchTab('tab-stocks')">📋 个股档案</button>
    <button class="main-tab" onclick="switchTab('tab-trend')">📈 趋势分析</button>
    <button class="main-tab" onclick="switchTab('tab-fund')">💰 资金流向</button>
    <button class="main-tab" onclick="switchTab('tab-news')">📰 舆情监测</button>
    <button class="main-tab" onclick="switchTab('tab-us')">🇺🇸 美股关联</button>
    <button class="main-tab" onclick="switchTab('tab-ai')">🤖 AI预测</button>
    <button class="main-tab" onclick="switchTab('tab-search')">🔍 搜索</button>
    <button class="main-tab" onclick="window.open('starmap.html','_blank')" style="background:linear-gradient(135deg,#60a5fa,#a78bfa);color:#fff;">🌌 星空图</button>
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
<h2 style="margin-top:24px;">📈 板块走势对比（近15日累计涨跌幅）</h2>
<div class="chart-container">{img_html(charts.get('sector_trend'))}</div>
{build_sector_intro_html()}
<h2 style="margin-top:24px;">📊 板块财务对比（PE / PB / 市值）</h2>
{build_sector_finance_html(analysis)}
</div>

<!-- ========== TAB 3: 个股档案 ========== -->
<div id="tab-stocks" class="tab-panel">
<h2>📋 个股详细档案（按板块分类）</h2>
{build_stock_profiles_html(analysis, finance_map)}
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

<!-- ========== TAB 5: 资金流向 ========== -->
<div id="tab-fund" class="tab-panel">
<h2>💰 资金流向分析</h2>
<p style="color:#94a3b8;margin-bottom:12px;">基于东方财富实时统计数据，展示超大单+大单（主力资金）净流入/流出情况</p>
{build_fundflow_html(analysis)}
</div>

<!-- ========== TAB 6: 舆情监测 ========== -->
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
<h2>🤖 多因子AI评分（非收益预测）</h2>
<p style="color:#94a3b8;margin-bottom:12px;">基于动量、相对强弱、量价、位置、舆情、资金六大因子的百分位综合评分（0-100）。评分越高代表当前技术面与资金面相对越强，不代表未来涨跌预测。</p>
{build_predictions_html(pred_data, backtest_data)}
<h3>📈 AI评分历史走势（强势 vs 弱势 Top5）</h3>
<div class="chart-container">{img_html(charts.get('score_history'))}</div>
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

</div><!-- end main-content -->

<!-- Scroll to Top Button -->
<button class="scroll-top" id="scrollTop" onclick="window.scrollTo({{top:0,behavior:'smooth'}})">↑</button>

<div class="footer">
    <div class="footer-brand">📊 AI / 光通信板块数据工作流</div>
    <div class="footer-links">
        <a href="https://github.com/weichenli0909-crypto/stock-report" target="_blank">GitHub 源码</a>
        <a href="starmap.html" target="_blank">3D 星空图</a>
    </div>
    <p style="margin-top:12px;">自动生成 | 数据来源：新浪财经 & 东方财富</p>
    <p style="margin-top:6px;">⚠️ 以上数据仅供学习参考，不构成投资建议</p>
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
    // 检测是否从 file:// 打开（直接双击 HTML 文件）
    if (location.protocol === 'file:') {{
        showToast('⚠️ 请通过 http://localhost:8899 打开页面才能刷新。正在为您打开...', 'info', 6000);
        setTimeout(() => {{
            window.open('http://localhost:8899/', '_blank');
        }}, 1000);
        return;
    }}
    // 检测是否是 GitHub Pages 静态托管
    if (location.hostname.endsWith('github.io') || location.hostname.endsWith('pages.dev')) {{
        showToast('ℹ️ 线上版本只读，请在本地运行 python3 web_server.py 后使用刷新', 'info', 6000);
        return;
    }}

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
            showToast('❌ 无法连接服务器。请在终端运行：cd data_workflow && python3 web_server.py', 'error', 8000);
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
    if (!code) {{
        resultDiv.innerHTML = '<p style="color:#fca5a5;">❌ 请输入股票代码或名称</p>';
        return;
    }}
    let known = document.querySelector('[data-stock-code="' + code + '"]');
    if (!known) {{
        known = document.querySelector('[data-stock-name="' + code + '"]');
    }}
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
        fetch('/api/search?code=' + encodeURIComponent(code))
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

/* ====== Theme Toggle ====== */
function toggleTheme() {{
    const html = document.documentElement;
    const current = html.getAttribute('data-theme');
    const next = current === 'dark' ? 'light' : 'dark';
    html.setAttribute('data-theme', next);
    document.getElementById('themeToggle').textContent = next === 'dark' ? '🌙' : '☀️';
    localStorage.setItem('stock-report-theme', next);
}}
// Restore saved theme
(function() {{
    const saved = localStorage.getItem('stock-report-theme');
    if (saved) {{
        document.documentElement.setAttribute('data-theme', saved);
        const btn = document.getElementById('themeToggle');
        if (btn) btn.textContent = saved === 'dark' ? '🌙' : '☀️';
    }}
}})();

/* ====== Event Panel Toggle & Filter ====== */
function toggleEventPanel(btn, className) {{
    const items = document.querySelectorAll('.' + className);
    const allHidden = items.length > 0 && items[0].style.display === 'none';
    items.forEach(el => {{ el.style.display = allHidden ? '' : 'none'; }});
    btn.textContent = allHidden ? '收起 ▲' : '展开全部 ▼';
}}
function filterEventByType(type, btn, containerId) {{
    // 更新按钮状态
    btn.parentElement.querySelectorAll('.evt-filter-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    // 筛选事件项
    const container = document.getElementById(containerId);
    if (!container) return;
    container.querySelectorAll(':scope > div').forEach(el => {{
        if (type === 'all') {{
            el.style.display = '';
        }} else {{
            const text = el.textContent || '';
            el.style.display = text.includes(type) ? '' : 'none';
        }}
    }});
}}

/* ====== Scroll to Top Button ====== */
const scrollTopBtn = document.getElementById('scrollTop');
window.addEventListener('scroll', function() {{
    if (window.scrollY > 400) {{
        scrollTopBtn.classList.add('visible');
    }} else {{
        scrollTopBtn.classList.remove('visible');
    }}
    // Update header status with time
    const now = new Date().toLocaleTimeString();
    const hrt = document.getElementById('headerRefreshTime');
    if (hrt && window.scrollY > 200) hrt.textContent = now;
}});
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

    def find_latest_file(pattern):
        files = sorted(glob.glob(os.path.join(DATA_DIR, pattern)))
        return files[-1] if files else None

    # 加载分析结果
    analysis_path = os.path.join(DATA_DIR, f"analysis_{today}.json")
    if not os.path.exists(analysis_path):
        analysis_path = find_latest_file("analysis_*.json")
    if not analysis_path or not os.path.exists(analysis_path):
        print(f"  ❌ 未找到任何分析结果")
        return None
    with open(analysis_path, "r", encoding="utf-8") as f:
        analysis = json.load(f)
    print(f"  📂 加载分析结果: {os.path.basename(analysis_path)}")

    # 加载舆情数据（可选）
    news_data = None
    news_path = os.path.join(DATA_DIR, f"news_{today}.json")
    if not os.path.exists(news_path):
        news_path = find_latest_file("news_*.json")
    if news_path and os.path.exists(news_path):
        with open(news_path, "r", encoding="utf-8") as f:
            news_data = json.load(f)
        print(f"  📂 加载舆情数据: {os.path.basename(news_path)}")
    else:
        print(f"  ⚠️ 未找到舆情数据（跳过）")

    # 生成图表（不依赖预测数据的）
    print("\n🎨 生成图表...")
    charts = {
        "sector": chart_sector_performance(analysis),
        "stock_rank": chart_stock_heatmap(analysis),
        "history": chart_history_trend(analysis),
        "volume_pie": chart_volume_pie(analysis),
        "sentiment": chart_sentiment(news_data),
        "sector_trend": chart_sector_trend_line(analysis),
    }

    # 加载美股数据（可选）
    us_data = None
    us_path = os.path.join(DATA_DIR, f"us_stocks_{today}.json")
    if not os.path.exists(us_path):
        us_path = find_latest_file("us_stocks_*.json")
    if us_path and os.path.exists(us_path):
        with open(us_path, "r", encoding="utf-8") as f:
            us_data = json.load(f)
        print(f"  📂 加载美股数据: {os.path.basename(us_path)}")
    else:
        print(f"  ⚠️ 未找到美股数据（跳过）")

    # 加载预测数据（可选）
    pred_data = None
    pred_path = os.path.join(DATA_DIR, f"predictions_{today}.json")
    if not os.path.exists(pred_path):
        pred_path = find_latest_file("predictions_*.json")
    if pred_path and os.path.exists(pred_path):
        with open(pred_path, "r", encoding="utf-8") as f:
            pred_data = json.load(f)
        print(f"  📂 加载AI评分数据: {os.path.basename(pred_path)}")
    else:
        print(f"  ⚠️ 未找到AI评分数据（跳过）")

    # 🆕 生成AI评分历史走势图（依赖 pred_data）
    if pred_data:
        charts["score_history"] = chart_score_history(pred_data)

    # 加载回测数据（可选）
    backtest_data = None
    bt_path = os.path.join(DATA_DIR, f"backtest_summary_{today}.json")
    if not os.path.exists(bt_path):
        bt_path = find_latest_file("backtest_summary_*.json")
    if bt_path and os.path.exists(bt_path):
        with open(bt_path, "r", encoding="utf-8") as f:
            backtest_data = json.load(f)
        print(f"  📂 加载回测数据: {os.path.basename(bt_path)}")
    else:
        print(f"  ⚠️ 未找到回测数据（跳过）")

    # 生成报告
    print("\n📝 生成 HTML 报告...")
    report_path = generate_html_report(
        analysis, charts, news_data, us_data, pred_data, backtest_data
    )

    print(f"\n✅ 报告生成完成！")
    print(f"  📄 打开报告: open {report_path}")
    return report_path


if __name__ == "__main__":
    run_report()
