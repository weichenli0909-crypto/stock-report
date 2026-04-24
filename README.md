# 📊 AI / 光通信板块 — 股票数据工作流

> 每日自动采集 **AI算力 · CPO · 光模块 · 光通信 · OCS · PCB** 板块的 A 股 + 美股关联标的数据，进行多维度分析、机器学习预测，并生成精美的可视化暗色主题日报。

![Python](https://img.shields.io/badge/Python-3.8+-blue?logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)
![Status](https://img.shields.io/badge/Status-Active-brightgreen)

---

## ✨ 功能亮点

- 🔄 **一键运行** — 一条命令完成 数据采集 → 舆情分析 → 美股联动 → 数据分析 → ML预测 → 报告生成
- 📰 **舆情追踪** — 自动采集板块新闻，分析市场情绪（利好/利空/中性）
- 🇺🇸 **美股联动** — 追踪英伟达、博通、微软等 10 只美股，映射 A 股关联个股
- 🤖 **机器学习预测** — 随机森林 + 梯度提升模型预测次日涨跌概率
- 📊 **精美报告** — 暗色主题 HTML 报告，包含图表、产业链分析、个股档案
- ⏰ **定时监控** — 盘中自动刷新，实时跟踪行情变化
- 🌐 **一键分享** — 支持局域网、GitHub Pages 分享给他人
- 🧩 **模块化设计** — 每一步都可以独立运行，方便调试和学习

---

## 📁 项目结构

```
data_workflow/
│
├── 🚀 核心脚本
│   ├── run_workflow.py      # 主入口 — 一键运行完整6步工作流
│   ├── config.py            # 配置文件 — 板块/个股/产业链/美股定义
│   ├── step1_collect.py     # Step 1 — A股实时行情 + 历史数据 + 板块资金流向
│   ├── step1b_news.py       # Step 2 — 舆情新闻采集 + 情绪分析
│   ├── step1c_us_stocks.py  # Step 3 — 美股关联标的行情采集
│   ├── step2_analyze.py     # Step 4 — 多维数据分析（涨跌/板块/趋势/波动率）
│   ├── step2b_predict.py    # Step 5 — 机器学习预测（随机森林/梯度提升）
│   └── step3_report.py      # Step 6 — 生成 HTML 可视化报告
│
├── 🔧 辅助工具
│   ├── scheduler.py         # 定时调度器 — 盘中自动刷新
│   ├── web_server.py        # Web服务器 — 局域网分享报告
│   └── deploy_pages.py      # 部署脚本 — 一键发布到 GitHub Pages
│
├── 📁 data/                 # 数据目录（自动生成）
│   ├── realtime_YYYYMMDD.csv       # A股实时行情
│   ├── history_YYYYMMDD.csv        # 30天历史日线
│   ├── sector_funds_YYYYMMDD.csv   # 板块资金流向
│   ├── news_YYYYMMDD.json          # 舆情新闻数据
│   ├── us_stocks_YYYYMMDD.json     # 美股行情数据
│   ├── analysis_YYYYMMDD.json      # 分析结果
│   └── predictions_YYYYMMDD.json   # ML预测结果
│
└── 📁 output/               # 报告输出目录（自动生成）
    ├── report.html                 # ✨ 最终 HTML 日报（浏览器打开）
    ├── sector_performance.png      # 板块涨跌幅图
    ├── stock_top_bottom.png        # 涨跌排行图
    ├── history_trend.png           # 近期趋势图
    ├── sentiment_pie.png           # 舆情情绪分布图
    └── volume_pie.png              # 成交额占比图
```

---

## 🚀 快速开始

### 1️⃣ 安装依赖

```bash
pip install akshare pandas matplotlib numpy scikit-learn
```

> 💡 推荐使用 Python 3.8+，建议在虚拟环境中安装

### 2️⃣ 一键运行完整工作流

```bash
cd data_workflow
python3 run_workflow.py
```

运行后会自动：
1. 📥 采集 A 股实时行情和历史数据
2. 📰 采集板块新闻和舆情
3. 🇺🇸 采集美股关联标的行情
4. 🔍 进行多维度数据分析
5. 🤖 运行 ML 模型预测涨跌
6. 📊 生成 HTML 可视化报告并自动打开浏览器

### 3️⃣ 查看报告

工作流运行完成后，会自动在浏览器中打开报告。你也可以手动打开：

```bash
open output/report.html        # macOS
# 或
start output/report.html       # Windows
```

---

## 📖 详细用法

### 🔹 单独运行某一步

如果你只想运行工作流的某个步骤：

```bash
python3 run_workflow.py 1    # 只运行 Step 1: A股行情采集
python3 run_workflow.py 2    # 只运行 Step 2: 舆情新闻采集
python3 run_workflow.py 3    # 只运行 Step 3: 美股行情采集
python3 run_workflow.py 4    # 只运行 Step 4: 数据分析
python3 run_workflow.py 5    # 只运行 Step 5: ML预测
python3 run_workflow.py 6    # 只运行 Step 6: 生成报告
```

### 🔹 定时自动刷新（盘中实时监控）

```bash
python3 scheduler.py              # 默认每5分钟刷新一次
python3 scheduler.py 3            # 每3分钟刷新
python3 scheduler.py 10 --full    # 每10分钟，含舆情+美股完整刷新
```

调度器特性：
- 📅 自动识别交易日（周末跳过）
- ⏰ 仅在交易时段（9:15-15:05）执行刷新
- ⚡ 盘中使用快速模式（行情+分析+报告），非盘中时跑完整流程
- 🛑 按 `Ctrl+C` 优雅退出

### 🔹 局域网分享报告

让同一 Wi-Fi 下的手机/电脑也能看到报告：

```bash
python3 web_server.py              # 启动Web服务器（默认端口8899）
python3 web_server.py 9000         # 自定义端口
```

启动后会显示局域网访问地址，如 `http://192.168.1.xxx:8899`，把这个链接发给同事即可。

### 🔹 部署到 GitHub Pages（公网永久链接）

让任何人通过固定链接随时查看最新报告：

```bash
python3 deploy_pages.py
```

首次使用需要配置 GitHub 仓库（脚本会引导你），之后每次运行都会自动推送更新。

---

## 📋 关注的板块与个股

### A 股（6大板块，37只个股）

| 板块 | 个股数 | 代表个股 |
|------|--------|----------|
| **AI算力** | 8 | 海康威视、中科曙光、寒武纪、浪潮信息、科大讯飞 |
| **CPO(共封装光学)** | 8 | 中际旭创、新易盛、源杰科技、长光华芯、仕佳光子 |
| **光模块** | 9 | 中际旭创、新易盛、天孚通信、剑桥科技、博创科技 |
| **光通信** | 8 | 烽火通信、长飞光纤、亨通光电、中天科技 |
| **OCS(光电路交换)** | 6 | 中际旭创、新易盛、天孚通信、德科立 |
| **PCB** | 9 | 沪电股份、深南电路、生益科技、胜宏科技 |

### 美股关联标的（10只）

| 美股 | 关联逻辑 |
|------|----------|
| **英伟达 NVDA** | AI算力霸主，GPU/CUDA生态，GB200服务器 |
| **博通 AVGO** | 数据中心交换芯片，定制AI芯片(TPU) |
| **相干 COHR** | 全球Top3光模块，800G光模块标杆 |
| **Lumentum LITE** | 光器件龙头，ROADM/WSS |
| **Arista ANET** | 数据中心高端交换机，AI集群网络 |
| **微软 MSFT** | Azure云计算，OpenAI最大投资方 |
| **谷歌 GOOGL** | GCP云计算，TPU芯片，OCS架构推动者 |
| **Meta META** | AI资本开支大增，数据中心光模块需求 |
| **亚马逊 AMZN** | AWS全球第一，Trainium自研AI芯片 |
| **思科 CSCO** | 网络设备龙头，光模块大买家 |

> 💡 所有股票列表都可以在 `config.py` 中自由修改

---

## 📊 工作流六步详解

```
┌──────────┐    ┌──────────┐    ┌──────────┐
│  Step 1   │    │  Step 2   │    │  Step 3   │
│  📥 行情   │───▶│  📰 舆情   │───▶│  🇺🇸 美股  │
│  采集     │    │  采集     │    │  采集     │
└──────────┘    └──────────┘    └──────────┘
      │                                │
      ▼                                ▼
┌──────────┐    ┌──────────┐    ┌──────────┐
│  Step 4   │    │  Step 5   │    │  Step 6   │
│  🔍 数据   │───▶│  🤖 ML    │───▶│  📊 报告   │
│  分析     │    │  预测     │    │  生成     │
└──────────┘    └──────────┘    └──────────┘
```

| 步骤 | 文件 | 做什么 | 输出 |
|------|------|--------|------|
| **Step 1** | `step1_collect.py` | 采集37只A股实时行情、30天历史数据、板块资金流向 | CSV 数据文件 |
| **Step 2** | `step1b_news.py` | 采集板块新闻动态，分析情绪（利好/利空/中性） | JSON 舆情数据 |
| **Step 3** | `step1c_us_stocks.py` | 采集10只美股行情，映射A股关联个股 | JSON 美股数据 |
| **Step 4** | `step2_analyze.py` | 涨跌排行、板块对比、趋势分析、波动率计算 | JSON 分析结果 |
| **Step 5** | `step2b_predict.py` | 随机森林+梯度提升模型预测次日涨跌概率 | JSON 预测结果 |
| **Step 6** | `step3_report.py` | 生成图表 + 产业链分析 + 个股档案 → HTML报告 | HTML + PNG |

---

## 🛠️ 自定义配置

### 添加新股票

编辑 `config.py`，在 `STOCK_GROUPS` 中添加：

```python
STOCK_GROUPS = {
    "AI算力": {
        "002415": "海康威视",
        "600000": "你想添加的股票",  # ← 加在这里
    },
    # ...
}
```

### 添加新板块

```python
STOCK_GROUPS = {
    # ... 已有板块 ...
    "新板块名称": {
        "股票代码1": "股票名称1",
        "股票代码2": "股票名称2",
    },
}
```

同时可以在 `SECTOR_INFO` 和 `STOCK_PROFILES` 中添加板块介绍和个股档案。

---

## 🎓 学习要点

通过这个项目你可以学到：

| 技能 | 涉及内容 |
|------|----------|
| 🐍 **Python 模块化设计** | 将大任务拆分为6个独立步骤，通过主入口编排 |
| 📡 **API 数据采集** | 使用 akshare 获取 A 股/美股金融数据 |
| 🧹 **数据清洗处理** | pandas DataFrame 操作、数据合并、去重、缺失值处理 |
| 📊 **数据可视化** | matplotlib 图表绑定（柱状图、饼图、折线图） |
| 🤖 **机器学习实战** | scikit-learn 随机森林 + 梯度提升分类器 |
| 📰 **NLP 情感分析** | 基于关键词的新闻情绪判断 |
| 📄 **自动报告生成** | HTML + CSS 暗色主题报告模板 |
| 🔗 **工作流编排** | 步骤间的数据传递与依赖管理 |
| ⏰ **定时任务** | Python 调度器，交易时间判断 |
| 🌐 **Web 服务** | HTTP 服务器搭建、局域网/公网分享 |

---

## ❓ 常见问题

<details>
<summary><b>Q: 运行时报错 ModuleNotFoundError</b></summary>

安装缺失的依赖：
```bash
pip install akshare pandas matplotlib numpy scikit-learn
```
</details>

<details>
<summary><b>Q: 非交易时间运行，数据是空的？</b></summary>

非交易时间（晚上/周末）也可以运行！数据会采集到最近一个交易日的收盘数据。实时行情数据在盘中更有意义。
</details>

<details>
<summary><b>Q: 如何让报告自动每天更新？</b></summary>

使用定时调度器：
```bash
python3 scheduler.py 5    # 盘中每5分钟自动刷新
```

或使用系统的 crontab 定时任务：
```bash
# 每个交易日 9:30 自动运行（macOS/Linux）
30 9 * * 1-5 cd /path/to/data_workflow && python3 run_workflow.py
```
</details>

<details>
<summary><b>Q: 如何把报告分享给不在同一网络的人？</b></summary>

方法1：部署到 GitHub Pages（推荐）
```bash
python3 deploy_pages.py
```

方法2：直接把 `output/report.html` 文件通过微信/邮件发给对方
</details>

<details>
<summary><b>Q: 如何修改关注的股票？</b></summary>

编辑 `config.py` 文件中的 `STOCK_GROUPS` 字典，添加或删除股票代码即可。修改后重新运行 `python3 run_workflow.py`。
</details>

---

## ⚠️ 免责声明

本项目仅供学习 Python 编程使用，所有数据来源于公开接口，**不构成任何投资建议**。投资有风险，入市需谨慎。

---

## 📝 更新日志

- **v3.0** — 新增舆情分析、美股联动、ML预测、产业链图谱、GitHub Pages 部署
- **v2.0** — 新增定时调度器、Web 分享服务器、个股档案
- **v1.0** — 基础版：行情采集 + 数据分析 + HTML 报告

---

<p align="center">
  Made with ❤️ by Python | 数据驱动投资研究
</p>
