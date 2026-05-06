# 📊 AI / 光通信板块 — 股票日报自动化工具

> **完全不懂电脑也能用！** 每天自动生成 AI / CPO / 光模块 / 光通信 板块深度日报。

[![在线 Demo](https://img.shields.io/badge/🌐_在线_Demo-点我查看-blue?style=for-the-badge)](https://weichenli0909-crypto.github.io/stock-report/)
[![难度](https://img.shields.io/badge/🎓_难度-零基础友好-green?style=for-the-badge)]()
[![免费](https://img.shields.io/badge/💰_费用-完全免费-orange?style=for-the-badge)]()

---

## 👋 这个软件能帮你做什么？

每天自动为你生成一份**精美的股票分析报告**，包含：

- 📈 **今日行情** — AI、光通信板块所有个股的涨跌情况
- 📰 **舆情分析** — 自动抓新闻，AI 判断利好还是利空
- 🇺🇸 **美股联动** — 英伟达、博通等美股最新行情
- 🤖 **AI 预测** — 机器学习模型预测明日强弱势股票
- 💰 **资金流向** — 主力资金流入/流出哪些股票
- 🌌 **3D 星空图** — 个股关联关系可视化

**报告效果可以先看在线 Demo 👉 [点这里](https://weichenli0909-crypto.github.io/stock-report/)**

---

## 🚀 两种使用方式 — 你可以选

|   | 方式一：☁️ 云端全自动 | 方式二：💻 在自己电脑上跑 |
|---|---|---|
| **难度** | ⭐ 极简，点点鼠标 | ⭐⭐ 稍难，需装 Python |
| **需要电脑开机？** | ❌ 不需要 | ✅ 需要 |
| **每天自动更新？** | ✅ 周一~周五 15:35 | ❌ 手动双击刷新 |
| **实时刷新按钮？** | ❌ 只读 | ✅ 可点按钮即时刷新 |
| **推荐给** | **完全不懂技术的人** | 想自己折腾的人 |

> 💡 **推荐方式一！** 完全不需要技术知识，全程只要点鼠标即可。

---

# 🎯 方式一：☁️ 云端全自动（推荐）

> **5 分钟搞定，从此每天自动更新**
> 原理：把代码**免费**托管到 GitHub，让 GitHub 的服务器**每天自动**帮你跑。你什么都不用装、不用管，每天打开网页就能看到最新报告。

## 第 1 步：注册 GitHub 账号（3 分钟）

1. 打开浏览器，访问 👉 https://github.com
2. 点击右上角 **Sign up**（注册）
3. 填写邮箱、密码、用户名（取一个英文名，比如 `zhangsan123`）
4. 去邮箱点验证链接
5. ✅ 完成

> 如果你已有 GitHub 账号，直接跳到第 2 步。

---

## 第 2 步：把项目"复制"到你的账号（1 分钟）

1. 打开项目主页 👉 **https://github.com/weichenli0909-crypto/stock-report**
2. 登录你的 GitHub 账号
3. 点击右上角 **Fork** 按钮
4. 在弹出页面点 **Create fork**（绿色按钮）
5. ✅ 等几秒，页面跳转到你自己账号下的副本

> 💡 **Fork 就是"复制一份到我自己的账号"**。复制完后，这个项目就是你的了，网址变成 `https://github.com/你的用户名/stock-report`。

---

## 第 3 步：开启自动运行（30 秒）

1. 在你的项目页面，点击上方 **Actions** 标签
2. 看到黄色提示？点绿色按钮 **I understand my workflows, go ahead and enable them**
3. 点击左侧列表里的 **📊 自动更新股票报告**
4. 点击右侧 **Enable workflow**（启用工作流）
5. ✅ 完成

**从现在起**，每个工作日下午 **15:35**（A 股收盘后 5 分钟），GitHub 的服务器会自动：
- 采集当天所有股票数据
- 分析行情、跑 AI 模型
- 生成最新报告
- 更新你的报告网页

---

## 第 4 步：开启网页访问（30 秒）

1. 在你的项目页面，点击上方 **Settings** 标签
2. 在左侧菜单找到 **Pages**，点进去
3. 在 "Build and deployment" 下：
   - **Source** 选 `Deploy from a branch`
   - **Branch** 选 `gh-pages`，旁边的文件夹选 `/ (root)`
4. 点 **Save**
5. ✅ 等 2-3 分钟即可

---

## 第 5 步：手动运行第一次（等不及？）

不想等到下午 15:35？可以手动立即跑一次：

1. 点 **Actions** 标签
2. 点左侧 **📊 自动更新股票报告**
3. 点右侧 **Run workflow** → 再点绿色的 **Run workflow** 按钮
4. 等 2-3 分钟，看到绿色 ✅ 就是成功
5. 打开你的报告网页：`https://你的用户名.github.io/stock-report/`

---

## 🎉 完成！收藏下面这个网址：

```
https://你的用户名.github.io/stock-report/
```

- 📱 **手机也能看**，直接在手机浏览器打开
- 🔗 **分享给朋友**，把链接发给任何人都能看
- 🌏 **每天自动更新**，你什么都不用做
- 💸 **永久免费**，GitHub 全部免费承担服务器费用

---

## 🔄 以后怎么同步最新功能？

当原作者（我）更新了新功能：

1. 打开你的项目页面
2. 如果页面上方显示 "This branch is X commits behind..."
3. 点 **Sync fork** → 点 **Update branch**
4. ✅ 完成，下次自动运行就会用新代码了

---

---

# 💻 方式二：在自己电脑上运行

> 适合想本地实时刷新、不依赖网络的人。

## 🍎 Mac 用户教程

### 第 1 步：下载项目代码

**方法 A：直接下载 ZIP（最简单，不需要 Git）**

1. 打开 👉 **https://github.com/weichenli0909-crypto/stock-report**
2. 点击绿色 **Code** 按钮 → **Download ZIP**
3. 下载完双击解压，把文件夹**移到桌面**

**方法 B：用 Git 克隆（推荐，方便更新）**

```bash
cd ~/Desktop
git clone https://github.com/weichenli0909-crypto/stock-report.git
```

### 第 2 步：一键安装

1. 打开解压后的文件夹
2. **右键**点击 `一键安装-Mac.command` → 选择 **打开**
   （第一次可能提示"无法验证开发者"，所以要用右键打开）
3. 在弹出的终端窗口里按 **Enter** 开始安装
4. 等待 3-5 分钟，看到 "🎉 安装完成！" 即可

> 💡 脚本会自动安装：Homebrew、Python 3、所有依赖库。**完全不用你操心**。

### 第 3 步：一键启动

1. 双击 `启动股票报告-Mac.command`
2. 询问是否更新数据时，输入 `1` 按 Enter（第一次建议选 1）
3. 等待 1-2 分钟，浏览器会**自动打开**报告页面
4. ✅ 完成！报告就在 http://localhost:8899

**以后每次**只需要双击 `启动股票报告-Mac.command` 就行了！

---

## 🪟 Windows 用户教程

### 第 1 步：下载项目代码

1. 打开 👉 **https://github.com/weichenli0909-crypto/stock-report**
2. 点击绿色 **Code** 按钮 → **Download ZIP**
3. 右键下载的 zip 文件 → **全部解压缩**
4. 把文件夹放到**桌面**

### 第 2 步：一键安装

1. 打开解压后的文件夹
2. 双击 `一键安装-Windows.bat`
3. 如果没装 Python，脚本会打开下载页面：
   - 点黄色 **Download Python** 按钮下载
   - 双击安装包
   - ⚠️⚠️⚠️ **务必勾选底部的 "Add Python to PATH"**（这一步非常重要！忘了勾选必须重装）
   - 点 **Install Now**
   - 装完**重新双击** `一键安装-Windows.bat`
4. 等待 3-5 分钟，看到 "🎉 安装完成！" 即可

### 第 3 步：一键启动

1. 双击 `启动股票报告-Windows.bat`
2. 询问是否更新数据时，输入 `1` 按 Enter
3. 等待 1-2 分钟，浏览器会**自动打开**报告页面
4. ✅ 完成！

**以后每次**只需要双击 `启动股票报告-Windows.bat` 就行了！

---

## 🔄 本地版本如何更新到最新？

### 方式 A：如果你是用 ZIP 下载的
1. 重新下载最新 ZIP（https://github.com/weichenli0909-crypto/stock-report）
2. 覆盖旧的文件夹（记得先备份你的 `data/` 和 `output/` 文件夹）
3. 双击启动脚本即可

### 方式 B：如果你是用 Git 克隆的（推荐）
在终端里进入项目文件夹，输入：
```bash
git pull
```
一秒搞定，最为优雅。

---

---

# 💡 进阶：自定义关注的股票

不想只看我配置的股票？可以**自己改**！

1. 打开 `config.py` 文件（用记事本、TextEdit、VS Code 都行）
2. 找到 `STOCK_GROUPS` 部分：
   ```python
   STOCK_GROUPS = {
       "AI算力": {
           "002230": "科大讯飞",
           "300059": "东方财富",
           # 你想加的股票：
           "你的股票代码": "股票名称",
       },
       # ...
   }
   ```
3. 保存
4. 重新运行一次即可

> 💡 股票代码就是炒股软件里看到的 6 位数字（比如 `000001` 是平安银行）

---

# ❓ 常见问题

<details>
<summary><b>Q：GitHub 要付费吗？</b></summary>
完全免费。方式一全程免费，包括：
- GitHub 账号
- GitHub Actions（免费服务器每月 2000 分钟，本项目每月只用 ~66 分钟）
- GitHub Pages（免费网页托管）
</details>

<details>
<summary><b>Q：我没有 Git/编程基础，能用吗？</b></summary>
能！方式一全程点鼠标，不需要写一行代码。方式二的一键脚本也会自动帮你装好环境。
</details>

<details>
<summary><b>Q：报告什么时候更新？</b></summary>
方式一：每个交易日（周一~周五）下午 15:35 自动更新。
方式二：双击启动脚本时手动更新。
</details>

<details>
<summary><b>Q：Mac 提示"无法验证开发者"怎么办？</b></summary>
不要双击，改用**右键** → **打开** → 再次确认打开。之后就可以双击了。
</details>

<details>
<summary><b>Q：Windows 双击 .bat 一闪就关？</b></summary>
说明 Python 没装好。重新运行 `一键安装-Windows.bat`，按提示装 Python（记得勾 "Add Python to PATH"）。
</details>

<details>
<summary><b>Q：端口 8899 被占用怎么办？</b></summary>
启动脚本会自动关闭占用 8899 端口的旧进程，无需手动处理。如果还是不行，重启电脑即可。
</details>

<details>
<summary><b>Q：我还有其他问题/想提建议</b></summary>
去 GitHub 项目的 **Issues** 页面提问即可：
https://github.com/weichenli0909-crypto/stock-report/issues/new
</details>

---

# ⚠️ 免责声明

本项目仅供**学习和研究**使用。所有数据来源于公开接口，**不构成任何投资建议**。投资有风险，入市需谨慎，盈亏自负。

---

# 📂 文件速查表

| 文件 | 用途 |
|---|---|
| `一键安装-Mac.command` | Mac 用户首次双击安装环境 |
| `启动股票报告-Mac.command` | Mac 用户每次双击启动 |
| `一键安装-Windows.bat` | Windows 用户首次双击安装 |
| `启动股票报告-Windows.bat` | Windows 用户每次双击启动 |
| `requirements.txt` | Python 依赖清单（不用管） |
| `config.py` | 关注的股票列表（可以改） |
| `run_workflow.py` | 主程序（不用管） |
| `.github/workflows/update-report.yml` | GitHub 自动运行配置（不用管） |

---

<p align="center">
  Made with ❤️ | 让每个人都能享受数据驱动的投资研究
</p>
