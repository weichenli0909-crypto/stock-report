"""
🌌 第四步：3D 股票星空图生成
将股票数据转化为交互式 3D 星空可视化 —— 每只股票是一颗星星
"""

import os
import json
import math
import csv
import glob
from datetime import datetime

# 尝试从 config 导入，失败则用内置映射
try:
    from config import STOCK_GROUPS, STOCK_PROFILES, SECTOR_INFO, DATA_DIR, OUTPUT_DIR
except ImportError:
    DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
    OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
    STOCK_GROUPS = {}
    STOCK_PROFILES = {}
    SECTOR_INFO = {}


# ============ 数据读取 ============


def find_latest_file(pattern):
    """查找最新的数据文件"""
    files = sorted(glob.glob(os.path.join(DATA_DIR, pattern)))
    return files[-1] if files else None


def read_realtime_csv(filepath):
    """读取实时行情 CSV"""
    stocks = {}
    with open(filepath, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            code = row.get("代码", "").strip()
            if not code:
                continue
            stocks[code] = {
                "code": code,
                "name": row.get("名称", ""),
                "price": float(row.get("最新价", 0) or 0),
                "open": float(row.get("今开", 0) or 0),
                "prev_close": float(row.get("昨收", 0) or 0),
                "high": float(row.get("最高", 0) or 0),
                "low": float(row.get("最低", 0) or 0),
                "volume": float(row.get("成交量", 0) or 0),
                "amount": float(row.get("成交额", 0) or 0),
                "change_pct": float(row.get("涨跌幅", 0) or 0),
                "change_amt": float(row.get("涨跌额", 0) or 0),
                "amplitude": float(row.get("振幅", 0) or 0),
            }
    return stocks


def read_predictions(filepath):
    """读取预测数据"""
    if not filepath or not os.path.exists(filepath):
        return {}
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    preds = {}
    for code, info in data.get("个股预测", {}).items():
        preds[code] = {
            "ai_score": info.get("AI综合评分", 50),
            "up_prob": info.get("上涨概率", 50),
            "pred_return": info.get("预测收益率", 0),
            "signal": info.get("信号", ""),
        }
    return preds


def read_analysis(filepath):
    """读取分析数据"""
    if not filepath or not os.path.exists(filepath):
        return {}
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def build_stock_sector_map():
    """构建股票→板块映射"""
    mapping = {}
    for sector, stocks in STOCK_GROUPS.items():
        for code in stocks:
            if code not in mapping:
                mapping[code] = []
            mapping[code].append(sector)
    return mapping


# ============ 3D 布局计算 ============

SECTOR_COLORS = {
    "AI算力": "#ff6b6b",
    "CPO(共封装光学)": "#ffd93d",
    "光模块": "#6bcb77",
    "光通信": "#4d96ff",
    "OCS(光电路交换)": "#9b59b6",
    "PCB": "#ff8c42",
    "液冷": "#00d2ff",
}


def compute_layout(stocks_data, sector_map, predictions):
    """计算每只股票的 3D 位置和视觉属性"""
    # 按板块分组
    sector_stocks = {}
    for code, data in stocks_data.items():
        sectors = sector_map.get(code, ["其他"])
        primary_sector = sectors[0]
        if primary_sector not in sector_stocks:
            sector_stocks[primary_sector] = []
        sector_stocks[primary_sector].append(data)

    # 板块中心点 —— 排列成球面上的点
    sector_names = list(sector_stocks.keys())
    n_sectors = len(sector_names)
    sector_centers = {}
    radius = 40

    for i, name in enumerate(sector_names):
        angle = (2 * math.pi * i) / n_sectors
        # 使用螺旋分布让板块在 3D 空间中更立体
        y_offset = 10 * math.sin(angle * 0.7)
        sector_centers[name] = {
            "x": radius * math.cos(angle),
            "y": y_offset,
            "z": radius * math.sin(angle),
        }

    # 计算成交额范围（用于归一化星星大小）
    all_amounts = [s["amount"] for s in stocks_data.values() if s["amount"] > 0]
    if all_amounts:
        min_amt = math.log10(min(all_amounts) + 1)
        max_amt = math.log10(max(all_amounts) + 1)
        amt_range = max_amt - min_amt if max_amt > min_amt else 1
    else:
        min_amt, amt_range = 0, 1

    # 为每只股票计算 3D 属性
    stars = []
    import random

    random.seed(42)  # 固定种子保证每次布局一致

    for sector_name, stock_list in sector_stocks.items():
        center = sector_centers[sector_name]
        n_stocks = len(stock_list)
        color = SECTOR_COLORS.get(sector_name, "#ffffff")

        for j, stock in enumerate(stock_list):
            # 在板块中心附近随机分布
            spread = min(12, 4 + n_stocks * 0.3)
            angle_local = (2 * math.pi * j) / max(n_stocks, 1)
            r_local = random.uniform(2, spread)
            y_local = random.uniform(-spread * 0.5, spread * 0.5)

            x = center["x"] + r_local * math.cos(angle_local) + random.uniform(-2, 2)
            y = center["y"] + y_local
            z = center["z"] + r_local * math.sin(angle_local) + random.uniform(-2, 2)

            # 星星大小 = log(成交额) 归一化
            if stock["amount"] > 0:
                size_norm = (math.log10(stock["amount"] + 1) - min_amt) / amt_range
            else:
                size_norm = 0.1
            star_size = 0.4 + size_norm * 2.0  # 0.4 ~ 2.4

            # 颜色基于涨跌幅
            change = stock["change_pct"]

            # AI 预测数据
            pred = predictions.get(stock["code"], {})
            ai_score = pred.get("ai_score", 50)
            up_prob = pred.get("up_prob", 50)
            signal = pred.get("signal", "")

            # 光芒强度 = 振幅 + AI 评分偏离度
            glow = (
                0.3 + (stock["amplitude"] / 15) * 0.4 + abs(ai_score - 50) / 100 * 0.3
            )

            profile = STOCK_PROFILES.get(stock["code"], {})

            stars.append(
                {
                    "code": stock["code"],
                    "name": stock["name"],
                    "sector": sector_name,
                    "sectorColor": color,
                    "x": round(x, 2),
                    "y": round(y, 2),
                    "z": round(z, 2),
                    "size": round(star_size, 2),
                    "change": round(change, 2),
                    "price": stock["price"],
                    "amount": round(stock["amount"] / 1e8, 2),  # 亿
                    "volume": stock["volume"],
                    "amplitude": stock["amplitude"],
                    "high": stock["high"],
                    "low": stock["low"],
                    "glow": round(min(glow, 1.0), 2),
                    "aiScore": ai_score,
                    "upProb": up_prob,
                    "signal": signal,
                    "mainBiz": profile.get("主营", ""),
                    "highlight": profile.get("亮点", ""),
                }
            )

    # 板块元数据
    sectors_meta = []
    for name in sector_names:
        center = sector_centers[name]
        color = SECTOR_COLORS.get(name, "#ffffff")
        count = len(sector_stocks.get(name, []))
        info = SECTOR_INFO.get(name, {})
        sectors_meta.append(
            {
                "name": name,
                "color": color,
                "x": round(center["x"], 2),
                "y": round(center["y"] + 15, 2),  # 标签在上方
                "z": round(center["z"], 2),
                "count": count,
                "desc": info.get("描述", ""),
                "driver": info.get("核心驱动", ""),
            }
        )

    return stars, sectors_meta


# ============ HTML 生成 ============


def generate_starmap_html(stars, sectors, date_str, stats):
    """生成完整的 3D 星空 HTML"""

    stars_json = json.dumps(stars, ensure_ascii=False)
    sectors_json = json.dumps(sectors, ensure_ascii=False)

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>🌌 AI/光通信 股票星空图 - {date_str}</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ background: #000; overflow: hidden; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; color: #e2e8f0; }}
canvas {{ display: block; }}

/* ===== 标题栏 ===== */
.header {{
    position: fixed; top: 0; left: 0; right: 0; z-index: 100;
    padding: 16px 24px;
    background: linear-gradient(180deg, rgba(0,0,0,0.85) 0%, rgba(0,0,0,0) 100%);
    pointer-events: none;
}}
.header h1 {{
    font-size: 22px; font-weight: 700;
    background: linear-gradient(135deg, #60a5fa, #a78bfa, #f472b6);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    pointer-events: auto;
}}
.header .subtitle {{ color: #64748b; font-size: 12px; margin-top: 4px; }}

/* ===== 板块筛选 ===== */
.sector-panel {{
    position: fixed; left: 16px; top: 50%; transform: translateY(-50%);
    z-index: 100; display: flex; flex-direction: column; gap: 6px;
}}
.sector-btn {{
    padding: 8px 14px; border: 1px solid rgba(255,255,255,0.15);
    background: rgba(15,23,42,0.8); backdrop-filter: blur(12px);
    color: #94a3b8; font-size: 12px; font-weight: 600;
    border-radius: 20px; cursor: pointer; transition: all 0.3s;
    white-space: nowrap; text-align: left;
}}
.sector-btn:hover {{ border-color: rgba(255,255,255,0.4); color: #e2e8f0; transform: translateX(4px); }}
.sector-btn.active {{ color: #fff; border-color: currentColor; box-shadow: 0 0 12px currentColor; }}
.sector-btn .dot {{
    display: inline-block; width: 8px; height: 8px;
    border-radius: 50%; margin-right: 6px; vertical-align: middle;
}}
.sector-btn .count {{
    font-size: 10px; color: #64748b; margin-left: 4px;
}}

/* ===== 统计栏 ===== */
.stats-bar {{
    position: fixed; bottom: 0; left: 0; right: 0; z-index: 100;
    padding: 12px 24px;
    background: linear-gradient(0deg, rgba(0,0,0,0.9) 0%, rgba(0,0,0,0) 100%);
    display: flex; justify-content: center; gap: 32px;
    pointer-events: none;
}}
.stat-item {{ text-align: center; }}
.stat-value {{ font-size: 20px; font-weight: 700; }}
.stat-label {{ font-size: 10px; color: #64748b; margin-top: 2px; }}
.stat-up {{ color: #ef4444; }}
.stat-down {{ color: #22c55e; }}
.stat-blue {{ color: #60a5fa; }}

/* ===== Tooltip ===== */
.tooltip {{
    position: fixed; z-index: 200; pointer-events: none;
    padding: 12px 16px; min-width: 220px;
    background: rgba(15,23,42,0.95); backdrop-filter: blur(20px);
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 12px; box-shadow: 0 8px 32px rgba(0,0,0,0.6);
    opacity: 0; transition: opacity 0.2s;
    font-size: 12px; line-height: 1.6;
}}
.tooltip.visible {{ opacity: 1; }}
.tooltip .tt-name {{ font-size: 15px; font-weight: 700; color: #f8fafc; }}
.tooltip .tt-code {{ color: #64748b; font-size: 11px; margin-left: 6px; }}
.tooltip .tt-sector {{ display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 10px; margin-top: 4px; }}
.tooltip .tt-row {{ display: flex; justify-content: space-between; margin-top: 6px; }}
.tooltip .tt-label {{ color: #64748b; }}
.tooltip .tt-val {{ font-weight: 600; }}

/* ===== 详情面板 ===== */
.detail-panel {{
    position: fixed; right: -380px; top: 50%; transform: translateY(-50%);
    z-index: 150; width: 340px; max-height: 80vh;
    background: rgba(15,23,42,0.95); backdrop-filter: blur(20px);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 16px; padding: 24px;
    box-shadow: 0 12px 48px rgba(0,0,0,0.6);
    transition: right 0.4s cubic-bezier(0.16, 1, 0.3, 1);
    overflow-y: auto;
}}
.detail-panel.open {{ right: 16px; }}
.detail-panel .dp-close {{
    position: absolute; top: 12px; right: 12px;
    width: 28px; height: 28px; border-radius: 50%;
    background: rgba(255,255,255,0.1); border: none;
    color: #94a3b8; font-size: 16px; cursor: pointer;
    display: flex; align-items: center; justify-content: center;
    transition: all 0.2s;
}}
.detail-panel .dp-close:hover {{ background: rgba(255,255,255,0.2); color: #fff; }}
.detail-panel .dp-name {{ font-size: 22px; font-weight: 700; }}
.detail-panel .dp-code {{ color: #64748b; font-size: 13px; }}
.detail-panel .dp-change {{
    font-size: 36px; font-weight: 800; margin: 12px 0 4px;
}}
.detail-panel .dp-price {{ color: #94a3b8; font-size: 14px; }}
.detail-panel .dp-grid {{
    display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin: 16px 0;
}}
.detail-panel .dp-cell {{
    background: rgba(255,255,255,0.05); border-radius: 8px; padding: 8px 10px;
}}
.detail-panel .dp-cell-label {{ font-size: 10px; color: #64748b; }}
.detail-panel .dp-cell-val {{ font-size: 14px; font-weight: 600; margin-top: 2px; }}
.detail-panel .dp-section {{ margin-top: 16px; }}
.detail-panel .dp-section-title {{ font-size: 12px; color: #64748b; margin-bottom: 6px; font-weight: 600; }}
.detail-panel .dp-biz {{ font-size: 13px; color: #cbd5e1; line-height: 1.6; }}
.detail-panel .dp-ai {{
    display: flex; align-items: center; gap: 12px; margin-top: 12px;
    padding: 12px; background: rgba(96,165,250,0.1); border-radius: 10px;
}}
.detail-panel .dp-ai-score {{ font-size: 28px; font-weight: 800; }}
.detail-panel .dp-ai-label {{ font-size: 11px; color: #64748b; }}
.detail-panel .dp-ai-bar {{
    flex: 1; height: 6px; background: rgba(255,255,255,0.1); border-radius: 3px; overflow: hidden;
}}
.detail-panel .dp-ai-fill {{ height: 100%; border-radius: 3px; transition: width 0.5s; }}

/* ===== 搜索框 ===== */
.search-wrap {{
    position: fixed; top: 16px; right: 16px; z-index: 100;
}}
.search-input {{
    width: 200px; padding: 8px 14px; border-radius: 20px;
    background: rgba(15,23,42,0.8); backdrop-filter: blur(12px);
    border: 1px solid rgba(255,255,255,0.15);
    color: #e2e8f0; font-size: 13px; outline: none;
    transition: all 0.3s;
}}
.search-input:focus {{ border-color: #60a5fa; width: 280px; box-shadow: 0 0 20px rgba(96,165,250,0.2); }}
.search-input::placeholder {{ color: #475569; }}
.search-results {{
    margin-top: 6px; max-height: 300px; overflow-y: auto;
    border-radius: 12px; background: rgba(15,23,42,0.95);
    border: 1px solid rgba(255,255,255,0.1);
    display: none;
}}
.search-results.visible {{ display: block; }}
.search-item {{
    padding: 8px 14px; cursor: pointer; font-size: 13px;
    border-bottom: 1px solid rgba(255,255,255,0.05);
    transition: background 0.2s;
}}
.search-item:hover {{ background: rgba(96,165,250,0.15); }}
.search-item .si-name {{ font-weight: 600; }}
.search-item .si-code {{ color: #64748b; font-size: 11px; margin-left: 6px; }}
.search-item .si-change {{ float: right; font-weight: 600; }}

/* ===== 操作提示 ===== */
.hint {{
    position: fixed; bottom: 60px; left: 50%; transform: translateX(-50%);
    z-index: 50; padding: 8px 20px; border-radius: 20px;
    background: rgba(15,23,42,0.7); color: #64748b; font-size: 11px;
    backdrop-filter: blur(8px); pointer-events: none;
    animation: hintFade 4s ease-in-out forwards;
}}
@keyframes hintFade {{ 0%,70% {{ opacity: 1; }} 100% {{ opacity: 0; }} }}

/* ===== 加载动画 ===== */
.loading {{
    position: fixed; inset: 0; z-index: 999;
    background: #000; display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    transition: opacity 0.8s;
}}
.loading.done {{ opacity: 0; pointer-events: none; }}
.loading-text {{
    font-size: 18px; font-weight: 600; margin-top: 20px;
    background: linear-gradient(135deg, #60a5fa, #a78bfa);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}}
.loading-ring {{
    width: 50px; height: 50px; border: 3px solid rgba(255,255,255,0.1);
    border-top-color: #60a5fa; border-radius: 50%;
    animation: spin 1s linear infinite;
}}
@keyframes spin {{ to {{ transform: rotate(360deg); }} }}

/* ===== 返回按钮 ===== */
.back-btn {{
    position: fixed; bottom: 60px; right: 16px; z-index: 100;
    padding: 8px 16px; border-radius: 20px;
    background: rgba(15,23,42,0.8); backdrop-filter: blur(12px);
    border: 1px solid rgba(255,255,255,0.15);
    color: #94a3b8; font-size: 12px; cursor: pointer;
    text-decoration: none; transition: all 0.3s;
}}
.back-btn:hover {{ border-color: #60a5fa; color: #60a5fa; }}
</style>
</head>
<body>

<div class="loading" id="loading">
    <div class="loading-ring"></div>
    <div class="loading-text">正在构建股票星空…</div>
</div>

<div class="header">
    <h1>🌌 AI / 光通信板块 · 股票星空图</h1>
    <div class="subtitle">{date_str} · 拖拽旋转 · 滚轮缩放 · 点击查看详情</div>
</div>

<div class="sector-panel" id="sectorPanel"></div>

<div class="search-wrap">
    <input type="text" class="search-input" id="searchInput" placeholder="🔍 搜索股票名称或代码…">
    <div class="search-results" id="searchResults"></div>
</div>

<div class="stats-bar" id="statsBar"></div>

<div class="tooltip" id="tooltip"></div>

<div class="detail-panel" id="detailPanel">
    <button class="dp-close" id="dpClose">✕</button>
    <div id="dpContent"></div>
</div>

<div class="hint">💡 拖拽旋转星空 · 滚轮缩放 · 悬停查看 · 点击查看详情 · 左侧筛选板块</div>

<a class="back-btn" href="report.html">← 返回日报</a>

<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
<script>
// ===== 数据 =====
const STARS = {stars_json};
const SECTORS = {sectors_json};

// ===== Three.js 初始化 =====
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 1000);
const renderer = new THREE.WebGLRenderer({{ antialias: true, alpha: true }});
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
document.body.appendChild(renderer.domElement);

// 相机初始位置
camera.position.set(0, 30, 80);
camera.lookAt(0, 0, 0);

// ===== 轨道控制 =====
// 简易 OrbitControls（内联实现，不依赖额外文件）
const controls = {{
    target: new THREE.Vector3(0, 0, 0),
    spherical: {{ radius: 80, phi: Math.PI / 3, theta: 0 }},
    isDragging: false,
    prevMouse: {{ x: 0, y: 0 }},
    autoRotate: true,
    autoRotateSpeed: 0.002,
    dampingFactor: 0.05,
    velocityTheta: 0,
    velocityPhi: 0,

    update() {{
        if (this.autoRotate && !this.isDragging) {{
            this.spherical.theta += this.autoRotateSpeed;
        }}
        // 阻尼
        this.spherical.theta += this.velocityTheta;
        this.spherical.phi += this.velocityPhi;
        this.velocityTheta *= (1 - this.dampingFactor);
        this.velocityPhi *= (1 - this.dampingFactor);

        // 限制 phi
        this.spherical.phi = Math.max(0.2, Math.min(Math.PI - 0.2, this.spherical.phi));

        const r = this.spherical.radius;
        const phi = this.spherical.phi;
        const theta = this.spherical.theta;
        camera.position.set(
            this.target.x + r * Math.sin(phi) * Math.cos(theta),
            this.target.y + r * Math.cos(phi),
            this.target.z + r * Math.sin(phi) * Math.sin(theta)
        );
        camera.lookAt(this.target);
    }}
}};

// 鼠标交互
renderer.domElement.addEventListener('mousedown', (e) => {{
    controls.isDragging = true;
    controls.prevMouse = {{ x: e.clientX, y: e.clientY }};
    controls.autoRotate = false;
}});
window.addEventListener('mousemove', (e) => {{
    if (controls.isDragging) {{
        const dx = e.clientX - controls.prevMouse.x;
        const dy = e.clientY - controls.prevMouse.y;
        controls.velocityTheta = -dx * 0.005;
        controls.velocityPhi = dy * 0.005;
        controls.prevMouse = {{ x: e.clientX, y: e.clientY }};
    }}
}});
window.addEventListener('mouseup', () => {{
    controls.isDragging = false;
    // 5秒后恢复自动旋转
    clearTimeout(controls._autoTimer);
    controls._autoTimer = setTimeout(() => {{ controls.autoRotate = true; }}, 5000);
}});
renderer.domElement.addEventListener('wheel', (e) => {{
    controls.spherical.radius = Math.max(20, Math.min(200, controls.spherical.radius + e.deltaY * 0.05));
}});
// 触摸支持
renderer.domElement.addEventListener('touchstart', (e) => {{
    if (e.touches.length === 1) {{
        controls.isDragging = true;
        controls.prevMouse = {{ x: e.touches[0].clientX, y: e.touches[0].clientY }};
        controls.autoRotate = false;
    }}
}});
renderer.domElement.addEventListener('touchmove', (e) => {{
    if (e.touches.length === 1 && controls.isDragging) {{
        const dx = e.touches[0].clientX - controls.prevMouse.x;
        const dy = e.touches[0].clientY - controls.prevMouse.y;
        controls.velocityTheta = -dx * 0.005;
        controls.velocityPhi = dy * 0.005;
        controls.prevMouse = {{ x: e.touches[0].clientX, y: e.touches[0].clientY }};
    }}
}});
renderer.domElement.addEventListener('touchend', () => {{
    controls.isDragging = false;
    clearTimeout(controls._autoTimer);
    controls._autoTimer = setTimeout(() => {{ controls.autoRotate = true; }}, 5000);
}});

// ===== 背景星空 =====
function createBackground() {{
    const count = 3000;
    const positions = new Float32Array(count * 3);
    const sizes = new Float32Array(count);
    for (let i = 0; i < count; i++) {{
        positions[i * 3] = (Math.random() - 0.5) * 500;
        positions[i * 3 + 1] = (Math.random() - 0.5) * 500;
        positions[i * 3 + 2] = (Math.random() - 0.5) * 500;
        sizes[i] = Math.random() * 1.5;
    }}
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    geo.setAttribute('size', new THREE.BufferAttribute(sizes, 1));
    const mat = new THREE.PointsMaterial({{
        color: 0x334155,
        size: 0.5,
        transparent: true,
        opacity: 0.6,
        sizeAttenuation: true
    }});
    scene.add(new THREE.Points(geo, mat));
}}

// ===== 创建星星纹理 =====
function createStarTexture() {{
    const canvas = document.createElement('canvas');
    canvas.width = 128;
    canvas.height = 128;
    const ctx = canvas.getContext('2d');
    const gradient = ctx.createRadialGradient(64, 64, 0, 64, 64, 64);
    gradient.addColorStop(0, 'rgba(255,255,255,1)');
    gradient.addColorStop(0.15, 'rgba(255,255,255,0.8)');
    gradient.addColorStop(0.4, 'rgba(255,255,255,0.3)');
    gradient.addColorStop(0.7, 'rgba(255,255,255,0.05)');
    gradient.addColorStop(1, 'rgba(255,255,255,0)');
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, 128, 128);
    return new THREE.CanvasTexture(canvas);
}}

// ===== 涨跌幅转颜色（深浅表示幅度大小）=====
function changeToColor(change) {{
    if (change > 0) {{
        // 涨：微涨偏粉，大涨深红/亮红
        const t = Math.min(change / 10, 1);  // 0~1
        const r = Math.round(180 + t * 75);  // 180→255
        const g = Math.round(140 - t * 120); // 140→20
        const b = Math.round(140 - t * 120); // 140→20
        return new THREE.Color(`rgb(${{r}},${{g}},${{b}})`);
    }} else if (change < 0) {{
        // 跌：微跌偏浅绿，大跌深绿/亮绿
        const t = Math.min(Math.abs(change) / 10, 1);
        const r = Math.round(140 - t * 120); // 140→20
        const g = Math.round(180 + t * 75);  // 180→255
        const b = Math.round(140 - t * 120); // 140→20
        return new THREE.Color(`rgb(${{r}},${{g}},${{b}})`);
    }}
    return new THREE.Color(0x888888);  // 平盘灰色
}}

// ===== 创建股票星星 =====
const starMeshes = [];
const starTexture = createStarTexture();
let activeSector = null;

function createStars() {{
    STARS.forEach((star, i) => {{
        // 核心球体
        const geo = new THREE.SphereGeometry(star.size * 0.3, 16, 16);
        const color = changeToColor(star.change);
        const mat = new THREE.MeshBasicMaterial({{ color }});
        const mesh = new THREE.Mesh(geo, mat);
        mesh.position.set(star.x, star.y, star.z);
        mesh.userData = {{ ...star, index: i }};
        scene.add(mesh);

        // 光晕 sprite
        const spriteMat = new THREE.SpriteMaterial({{
            map: starTexture,
            color: color,
            transparent: true,
            opacity: 0.3 + star.glow * 0.5,
            blending: THREE.AdditiveBlending
        }});
        const sprite = new THREE.Sprite(spriteMat);
        sprite.scale.set(star.size * 2.5, star.size * 2.5, 1);
        sprite.position.copy(mesh.position);
        sprite.userData = {{ parentIdx: i }};
        scene.add(sprite);

        starMeshes.push({{ mesh, sprite, data: star }});
    }});
}}

// ===== 板块连接线 =====
function createConstellationLines() {{
    const sectorGroups = {{}};
    STARS.forEach((s, i) => {{
        if (!sectorGroups[s.sector]) sectorGroups[s.sector] = [];
        sectorGroups[s.sector].push(i);
    }});

    Object.entries(sectorGroups).forEach(([sector, indices]) => {{
        if (indices.length < 2) return;
        const color = new THREE.Color(SECTORS.find(s => s.name === sector)?.color || '#334155');

        // 用最近邻连接（简化版）
        const connected = new Set();
        const points = [];

        for (let i = 0; i < Math.min(indices.length, 30); i++) {{
            const a = STARS[indices[i]];
            let bestDist = Infinity, bestJ = -1;
            for (let j = i + 1; j < indices.length; j++) {{
                const b = STARS[indices[j]];
                const d = Math.sqrt((a.x-b.x)**2 + (a.y-b.y)**2 + (a.z-b.z)**2);
                if (d < bestDist && d < 15) {{
                    bestDist = d; bestJ = j;
                }}
            }}
            if (bestJ >= 0) {{
                const b = STARS[indices[bestJ]];
                points.push(new THREE.Vector3(a.x, a.y, a.z));
                points.push(new THREE.Vector3(b.x, b.y, b.z));
            }}
        }}

        if (points.length > 0) {{
            const geo = new THREE.BufferGeometry().setFromPoints(points);
            const mat = new THREE.LineBasicMaterial({{
                color, transparent: true, opacity: 0.12, linewidth: 1
            }});
            const lines = new THREE.LineSegments(geo, mat);
            lines.userData.sector = sector;
            scene.add(lines);
        }}
    }});
}}

// ===== 板块标签 =====
function createSectorLabels() {{
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');

    SECTORS.forEach(sector => {{
        canvas.width = 512;
        canvas.height = 128;
        ctx.clearRect(0, 0, 512, 128);
        ctx.font = 'bold 36px -apple-system, BlinkMacSystemFont, sans-serif';
        ctx.fillStyle = sector.color;
        ctx.textAlign = 'center';
        ctx.fillText(sector.name, 256, 50);
        ctx.font = '20px sans-serif';
        ctx.fillStyle = '#64748b';
        ctx.fillText(`${{sector.count}} 只`, 256, 85);

        const texture = new THREE.CanvasTexture(canvas.cloneNode(true).getContext('2d').canvas);
        // 需要重新绘制到新 canvas
        const c2 = document.createElement('canvas');
        c2.width = 512; c2.height = 128;
        const ctx2 = c2.getContext('2d');
        ctx2.drawImage(canvas, 0, 0);
        const tex = new THREE.CanvasTexture(c2);

        const spriteMat = new THREE.SpriteMaterial({{
            map: tex, transparent: true, opacity: 0.8
        }});
        const sprite = new THREE.Sprite(spriteMat);
        sprite.position.set(sector.x, sector.y, sector.z);
        sprite.scale.set(20, 5, 1);
        sprite.userData.sectorLabel = sector.name;
        scene.add(sprite);
    }});
}}

// ===== 雷射检测（悬停/点击）=====
const raycaster = new THREE.Raycaster();
raycaster.params.Points = {{ threshold: 2 }};
const mouse = new THREE.Vector2();
let hoveredStar = null;
const tooltip = document.getElementById('tooltip');

function formatAmount(val) {{
    if (val >= 10000) return (val / 10000).toFixed(1) + '万亿';
    if (val >= 1) return val.toFixed(1) + '亿';
    return (val * 10000).toFixed(0) + '万';
}}

renderer.domElement.addEventListener('mousemove', (e) => {{
    mouse.x = (e.clientX / window.innerWidth) * 2 - 1;
    mouse.y = -(e.clientY / window.innerHeight) * 2 + 1;

    raycaster.setFromCamera(mouse, camera);
    const meshes = starMeshes.map(s => s.mesh);
    const intersects = raycaster.intersectObjects(meshes);

    if (intersects.length > 0) {{
        const star = intersects[0].object.userData;
        hoveredStar = star;
        renderer.domElement.style.cursor = 'pointer';

        const changeColor = star.change >= 0 ? '#ef4444' : '#22c55e';
        const changeSign = star.change >= 0 ? '+' : '';

        tooltip.innerHTML = `
            <div class="tt-name">${{star.name}}<span class="tt-code">${{star.code}}</span></div>
            <div class="tt-sector" style="background:${{star.sectorColor}}22;color:${{star.sectorColor}}">${{star.sector}}</div>
            <div class="tt-row"><span class="tt-label">最新价</span><span class="tt-val">¥${{star.price}}</span></div>
            <div class="tt-row"><span class="tt-label">涨跌幅</span><span class="tt-val" style="color:${{changeColor}}">${{changeSign}}${{star.change}}%</span></div>
            <div class="tt-row"><span class="tt-label">成交额</span><span class="tt-val">${{formatAmount(star.amount)}}</span></div>
            <div class="tt-row"><span class="tt-label">AI评分</span><span class="tt-val" style="color:${{star.aiScore>=60?'#ef4444':star.aiScore<=40?'#22c55e':'#94a3b8'}}">${{star.aiScore}}</span></div>
        `;
        tooltip.style.left = Math.min(e.clientX + 16, window.innerWidth - 250) + 'px';
        tooltip.style.top = Math.min(e.clientY + 16, window.innerHeight - 200) + 'px';
        tooltip.classList.add('visible');

        // 高亮星星
        const idx = star.index;
        starMeshes[idx].sprite.material.opacity = 1;
        starMeshes[idx].sprite.scale.set(star.size * 4, star.size * 4, 1);
    }} else {{
        if (hoveredStar) {{
            const idx = hoveredStar.index;
            if (starMeshes[idx]) {{
                const s = starMeshes[idx].data;
                starMeshes[idx].sprite.material.opacity = 0.3 + s.glow * 0.5;
                starMeshes[idx].sprite.scale.set(s.size * 2.5, s.size * 2.5, 1);
            }}
        }}
        hoveredStar = null;
        tooltip.classList.remove('visible');
        renderer.domElement.style.cursor = 'grab';
    }}
}});

// ===== 点击详情 =====
const detailPanel = document.getElementById('detailPanel');
const dpContent = document.getElementById('dpContent');
let selectedStar = null;

renderer.domElement.addEventListener('click', (e) => {{
    if (controls.isDragging) return;
    if (!hoveredStar) {{
        detailPanel.classList.remove('open');
        selectedStar = null;
        return;
    }}
    const star = hoveredStar;
    selectedStar = star;

    const changeColor = star.change >= 0 ? '#ef4444' : '#22c55e';
    const changeSign = star.change >= 0 ? '+' : '';
    const aiColor = star.aiScore >= 60 ? '#ef4444' : star.aiScore <= 40 ? '#22c55e' : '#60a5fa';
    const aiBarColor = star.aiScore >= 60 ? 'linear-gradient(90deg,#60a5fa,#ef4444)' : star.aiScore <= 40 ? 'linear-gradient(90deg,#60a5fa,#22c55e)' : 'linear-gradient(90deg,#3b82f6,#60a5fa)';

    dpContent.innerHTML = `
        <div class="dp-name">${{star.name}} <span class="dp-code">${{star.code}}</span></div>
        <div style="margin-top:4px"><span style="padding:3px 10px;border-radius:10px;font-size:11px;background:${{star.sectorColor}}22;color:${{star.sectorColor}}">${{star.sector}}</span></div>
        <div class="dp-change" style="color:${{changeColor}}">${{changeSign}}${{star.change}}%</div>
        <div class="dp-price">¥${{star.price}} · 振幅 ${{star.amplitude}}%</div>

        <div class="dp-grid">
            <div class="dp-cell"><div class="dp-cell-label">成交额</div><div class="dp-cell-val" style="color:#60a5fa">${{formatAmount(star.amount)}}</div></div>
            <div class="dp-cell"><div class="dp-cell-label">最高/最低</div><div class="dp-cell-val">¥${{star.high}} / ¥${{star.low}}</div></div>
            <div class="dp-cell"><div class="dp-cell-label">上涨概率</div><div class="dp-cell-val" style="color:${{star.upProb>55?'#ef4444':star.upProb<45?'#22c55e':'#94a3b8'}}">${{star.upProb}}%</div></div>
            <div class="dp-cell"><div class="dp-cell-label">AI信号</div><div class="dp-cell-val">${{star.signal || '—'}}</div></div>
        </div>

        <div class="dp-ai">
            <div>
                <div class="dp-ai-score" style="color:${{aiColor}}">${{star.aiScore}}</div>
                <div class="dp-ai-label">AI综合评分</div>
            </div>
            <div style="flex:1">
                <div class="dp-ai-bar"><div class="dp-ai-fill" style="width:${{star.aiScore}}%;background:${{aiBarColor}}"></div></div>
                <div style="display:flex;justify-content:space-between;font-size:10px;color:#475569;margin-top:2px"><span>偏空</span><span>偏多</span></div>
            </div>
        </div>

        ${{star.mainBiz ? `<div class="dp-section"><div class="dp-section-title">主营业务</div><div class="dp-biz">${{star.mainBiz}}</div></div>` : ''}}
        ${{star.highlight ? `<div class="dp-section"><div class="dp-section-title">核心亮点</div><div class="dp-biz" style="color:#fde047">${{star.highlight}}</div></div>` : ''}}
    `;
    detailPanel.classList.add('open');

    // 相机飞向星星
    const targetPos = new THREE.Vector3(star.x, star.y, star.z);
    animateCameraTo(targetPos, 30);
}});

document.getElementById('dpClose').addEventListener('click', () => {{
    detailPanel.classList.remove('open');
    selectedStar = null;
}});

// ===== 相机动画 =====
let cameraAnimation = null;

function animateCameraTo(target, distance) {{
    const start = {{
        tx: controls.target.x, ty: controls.target.y, tz: controls.target.z,
        radius: controls.spherical.radius
    }};
    const end = {{ tx: target.x, ty: target.y, tz: target.z, radius: distance }};
    const duration = 1000;
    const startTime = Date.now();

    cameraAnimation = () => {{
        const elapsed = Date.now() - startTime;
        const t = Math.min(elapsed / duration, 1);
        const ease = t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;

        controls.target.x = start.tx + (end.tx - start.tx) * ease;
        controls.target.y = start.ty + (end.ty - start.ty) * ease;
        controls.target.z = start.tz + (end.tz - start.tz) * ease;
        controls.spherical.radius = start.radius + (end.radius - start.radius) * ease;

        if (t >= 1) cameraAnimation = null;
    }};
}}

// ===== 板块筛选 UI =====
function buildSectorPanel() {{
    const panel = document.getElementById('sectorPanel');
    let html = `<button class="sector-btn active" onclick="filterSector(null, this)">
        <span class="dot" style="background:#fff"></span>全部<span class="count">${{STARS.length}}</span>
    </button>`;
    SECTORS.forEach(s => {{
        html += `<button class="sector-btn" onclick="filterSector('${{s.name}}', this)">
            <span class="dot" style="background:${{s.color}}"></span>${{s.name}}<span class="count">${{s.count}}</span>
        </button>`;
    }});
    panel.innerHTML = html;
}}

window.filterSector = function(sector, btn) {{
    document.querySelectorAll('.sector-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    activeSector = sector;

    starMeshes.forEach(s => {{
        const visible = !sector || s.data.sector === sector;
        s.mesh.visible = visible;
        s.sprite.visible = visible;
        if (visible && sector) {{
            s.sprite.material.opacity = 0.5 + s.data.glow * 0.5;
        }} else if (visible) {{
            s.sprite.material.opacity = 0.3 + s.data.glow * 0.5;
        }}
    }});

    // 连接线
    scene.children.forEach(child => {{
        if (child.userData?.sector) {{
            child.visible = !sector || child.userData.sector === sector;
            if (child.visible && sector) child.material.opacity = 0.25;
            else child.material.opacity = 0.12;
        }}
        if (child.userData?.sectorLabel) {{
            child.visible = !sector || child.userData.sectorLabel === sector;
        }}
    }});

    // 飞到板块中心
    if (sector) {{
        const s = SECTORS.find(s => s.name === sector);
        if (s) animateCameraTo(new THREE.Vector3(s.x, s.y - 15, s.z), 40);
    }} else {{
        animateCameraTo(new THREE.Vector3(0, 0, 0), 80);
    }}
}};

// ===== 统计栏 =====
function buildStatsBar() {{
    const upCount = STARS.filter(s => s.change > 0).length;
    const downCount = STARS.filter(s => s.change < 0).length;
    const flatCount = STARS.length - upCount - downCount;
    const totalAmount = STARS.reduce((sum, s) => sum + s.amount, 0);
    const avgChange = (STARS.reduce((sum, s) => sum + s.change, 0) / STARS.length).toFixed(2);
    const avgChangeColor = avgChange >= 0 ? 'stat-up' : 'stat-down';

    document.getElementById('statsBar').innerHTML = `
        <div class="stat-item"><div class="stat-value stat-up">${{upCount}}</div><div class="stat-label">上涨</div></div>
        <div class="stat-item"><div class="stat-value stat-down">${{downCount}}</div><div class="stat-label">下跌</div></div>
        <div class="stat-item"><div class="stat-value" style="color:#94a3b8">${{flatCount}}</div><div class="stat-label">平盘</div></div>
        <div class="stat-item"><div class="stat-value ${{avgChangeColor}}">${{avgChange >= 0 ? '+' : ''}}${{avgChange}}%</div><div class="stat-label">平均涨跌</div></div>
        <div class="stat-item"><div class="stat-value stat-blue">${{formatAmount(totalAmount)}}</div><div class="stat-label">总成交额</div></div>
        <div class="stat-item"><div class="stat-value" style="color:#a78bfa">${{STARS.length}}</div><div class="stat-label">星星总数</div></div>
    `;
}}

// ===== 搜索功能 =====
const searchInput = document.getElementById('searchInput');
const searchResults = document.getElementById('searchResults');

searchInput.addEventListener('input', (e) => {{
    const q = e.target.value.trim().toLowerCase();
    if (!q) {{ searchResults.classList.remove('visible'); return; }}

    const matches = STARS.filter(s =>
        s.name.toLowerCase().includes(q) || s.code.includes(q)
    ).slice(0, 8);

    if (matches.length === 0) {{ searchResults.classList.remove('visible'); return; }}

    searchResults.innerHTML = matches.map(s => {{
        const changeColor = s.change >= 0 ? '#ef4444' : '#22c55e';
        const sign = s.change >= 0 ? '+' : '';
        return `<div class="search-item" data-code="${{s.code}}">
            <span class="si-name">${{s.name}}</span><span class="si-code">${{s.code}}</span>
            <span class="si-change" style="color:${{changeColor}}">${{sign}}${{s.change}}%</span>
        </div>`;
    }}).join('');
    searchResults.classList.add('visible');

    searchResults.querySelectorAll('.search-item').forEach(item => {{
        item.addEventListener('click', () => {{
            const code = item.dataset.code;
            const star = STARS.find(s => s.code === code);
            if (star) {{
                hoveredStar = star;
                renderer.domElement.dispatchEvent(new MouseEvent('click'));
                searchResults.classList.remove('visible');
                searchInput.value = '';
            }}
        }});
    }});
}});

searchInput.addEventListener('blur', () => {{
    setTimeout(() => searchResults.classList.remove('visible'), 200);
}});

// ===== 动画脉冲 =====
let time = 0;

function animate() {{
    requestAnimationFrame(animate);
    time += 0.01;

    if (cameraAnimation) cameraAnimation();
    controls.update();

    // 星星呼吸脉冲
    starMeshes.forEach((s, i) => {{
        const pulse = 1 + Math.sin(time * 2 + i * 0.5) * 0.08;
        s.sprite.scale.set(
            s.data.size * 2.5 * pulse,
            s.data.size * 2.5 * pulse,
            1
        );
    }});

    renderer.render(scene, camera);
}}

// ===== 窗口大小适配 =====
window.addEventListener('resize', () => {{
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
}});

// ===== 初始化 =====
function init() {{
    createBackground();
    createStars();
    createConstellationLines();
    createSectorLabels();
    buildSectorPanel();
    buildStatsBar();

    // 开场动画：从远处飞入
    controls.spherical.radius = 200;
    setTimeout(() => {{
        const startR = 200;
        const endR = 80;
        const duration = 2000;
        const startTime = Date.now();
        function zoomIn() {{
            const t = Math.min((Date.now() - startTime) / duration, 1);
            const ease = 1 - Math.pow(1 - t, 3);
            controls.spherical.radius = startR + (endR - startR) * ease;
            if (t < 1) requestAnimationFrame(zoomIn);
        }}
        zoomIn();
    }}, 300);

    // 隐藏加载动画
    setTimeout(() => {{
        document.getElementById('loading').classList.add('done');
    }}, 800);

    animate();
}}

init();
</script>
</body>
</html>"""
    return html


# ============ 主入口 ============


def run():
    print("🌌 Step 4: 生成 3D 股票星空图")
    print("=" * 50)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 1. 读取数据
    realtime_file = find_latest_file("realtime_*.csv")
    if not realtime_file:
        print("  ❌ 未找到实时行情数据，请先运行 step1_collect.py")
        return

    print(f"  📂 实时行情: {os.path.basename(realtime_file)}")
    stocks_data = read_realtime_csv(realtime_file)
    print(f"  📊 读取到 {len(stocks_data)} 只股票")

    # 2. 预测数据
    pred_file = find_latest_file("predictions_*.json")
    predictions = read_predictions(pred_file)
    if predictions:
        print(f"  🤖 预测数据: {os.path.basename(pred_file)} ({len(predictions)} 只)")
    else:
        print("  ⚠️ 无预测数据，将使用默认值")

    # 3. 分析数据
    analysis_file = find_latest_file("analysis_*.json")
    analysis = read_analysis(analysis_file)
    date_str = analysis.get("分析日期", datetime.now().strftime("%Y-%m-%d %H:%M"))

    # 4. 股票-板块映射
    sector_map = build_stock_sector_map()
    print(f"  🏷️ 板块映射: {len(sector_map)} 只股票, {len(STOCK_GROUPS)} 个板块")

    # 5. 计算布局
    stars, sectors = compute_layout(stocks_data, sector_map, predictions)
    print(f"  ⭐ 生成 {len(stars)} 颗星星, {len(sectors)} 个板块")

    # 6. 统计信息
    stats = {
        "total": len(stars),
        "up": sum(1 for s in stars if s["change"] > 0),
        "down": sum(1 for s in stars if s["change"] < 0),
    }

    # 7. 生成 HTML
    html = generate_starmap_html(stars, sectors, date_str, stats)
    output_path = os.path.join(OUTPUT_DIR, "starmap.html")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"\n  ✅ 星空图已生成: {output_path}")
    print(f"  🌌 {stats['total']} 颗星星 | ↑{stats['up']} ↓{stats['down']}")
    print(f"  🌐 用浏览器打开 starmap.html 体验 3D 交互！")

    return output_path


if __name__ == "__main__":
    run()
