# 📊 AI / 光通信板块 — 股票日报自动化工具

## 🎯 这是什么？

这是一个**全自动**的股票分析工具，每天自动帮你：

- 📥 采集 AI算力、CPO、光模块、光通信、OCS、PCB 板块的股票数据
- 🇺🇸 追踪英伟达、博通、微软等美股的关联影响
- 📰 采集板块新闻，判断是利好还是利空
- 🤖 用机器学习模型预测次日涨跌
- 📊 生成一份精美的可视化日报网页

**最终效果：** 你会得到一个**永久网页链接**，每天自动更新，打开就能看到最新的股票分析报告。

---

## 🌟 两种使用方式（选一种即可）

| 方式 | 难度 | 适合人群 | 需要电脑？ | 自动更新？ |
|------|------|----------|-----------|-----------|
| **方式一：云端自动运行** | ⭐ 极简 | 完全不懂技术的人 | ❌ 不需要 | ✅ 每天自动 |
| **方式二：本地电脑运行** | ⭐⭐ 稍难 | 想在自己电脑上跑的人 | ✅ 需要 | 手动点一下 |

---

# 📖 方式一：云端自动运行（推荐！最简单！）

> 💡 **原理说明：** GitHub 是一个免费的代码平台，它提供免费的服务器帮你每天自动运行程序，然后生成一个网页供你随时查看。全程免费，不需要你的电脑开机。

## 第一步：注册 GitHub 账号（5分钟）

1. 打开浏览器，访问 👉 **https://github.com**
2. 点击右上角 **Sign up**（注册）
3. 填写：
   - **Email**：你的邮箱地址
   - **Password**：设一个密码（至少8位，要包含数字和字母）
   - **Username**：取一个英文用户名（比如 `zhangsan123`）
4. 完成人机验证，点 **Create account**
5. 去邮箱收验证邮件，点击验证链接
6. ✅ 注册完成！

> ⚠️ 如果你已经有 GitHub 账号，跳过这一步。

---

## 第二步：复制项目到你的账号（2分钟）

> 💡 "Fork" 就是把别人的项目复制一份到你自己的账号下，你可以随意使用和修改。

1. 确保你已经登录 GitHub
2. 打开这个项目页面 👉 **https://github.com/weichenli0909-crypto/stock-report**
3. 点击页面右上角的 **Fork** 按钮（一个分叉的图标）

   ![Fork按钮位置](https://docs.github.com/assets/cb-40742/mw-1440/images/help/repository/fork-button.webp)

4. 在弹出的页面中，直接点 **Create fork**（创建复制）
5. 等几秒钟，页面会跳转到你自己账号下的项目副本
6. ✅ 复制完成！

> 🎉 现在这个项目已经在你自己的账号下了！网址变成了 `https://github.com/你的用户名/stock-report`

---

## 第三步：开启自动运行（3分钟）

> 💡 GitHub Actions 是 GitHub 免费提供的"自动执行器"，可以定时帮你运行程序。

1. 在你 Fork 后的项目页面，点击上方的 **Actions**（动作）标签

   > 如果看到一个黄色提示说 "Workflows aren't being run on this forked repository"，点击绿色按钮 **I understand my workflows, go ahead and enable them**

2. 点击左侧的 **📊 自动更新股票报告**
3. 点击右侧的 **Enable workflow**（启用工作流）
4. ✅ 自动运行已开启！

**现在会发生什么？**
- 每个工作日（周一到周五）北京时间 **15:35**（收盘后），系统会自动运行程序
- 自动采集当天的股票数据、分析、生成报告
- 自动更新你的报告网页

---

## 第四步：开启网页展示（3分钟）

> 💡 GitHub Pages 是 GitHub 免费提供的网页托管服务，让你的报告可以通过网页链接访问。

1. 在你的项目页面，点击上方的 **Settings**（设置）标签
2. 在左侧菜单找到 **Pages**，点击它
3. 在 "Build and deployment" 下方：
   - **Source** 选择 **Deploy from a branch**
   - **Branch** 选择 **gh-pages**，文件夹选 **/ (root)**
4. 点击 **Save**（保存）
5. ✅ 网页开启成功！

**等待约2-3分钟后**，你的报告网页就可以访问了：

```
https://你的用户名.github.io/stock-report/
```

> 📱 把这个链接收藏到手机/电脑书签，以后每天打开就能看到最新报告！

---

## 第五步：手动触发第一次运行（1分钟）

> 💡 因为自动运行是每天15:35，你可能不想等到那个时候。我们可以手动触发一次。

1. 在项目页面点击 **Actions** 标签
2. 点击左侧 **📊 自动更新股票报告**
3. 点击右侧 **Run workflow** 按钮
4. 在弹出的下拉菜单中，直接点 **Run workflow**（绿色按钮）
5. 等待 2-3 分钟，看到绿色 ✅ 表示运行成功
6. 刷新你的报告网页，就能看到最新报告了！

---

## 🎉 恭喜！设置完成！

从现在开始：
- 📅 **每个工作日** 15:35 自动更新（你什么都不用做）
- 📱 **随时查看** 打开 `https://你的用户名.github.io/stock-report/` 就行
- 🔄 **想立即更新** 去 Actions 页面点 Run workflow
- 💻 **不需要电脑开机** GitHub 的服务器帮你跑

---

## 🔄 以后如何同步最新版本？

当原作者更新了代码（比如增加了新功能），你可以这样获取最新版：

1. 打开你的项目页面 `https://github.com/你的用户名/stock-report`
2. 如果有更新，页面上方会显示 **"This branch is X commits behind..."**
3. 点击 **Sync fork** 按钮
4. 点击 **Update branch**
5. ✅ 代码已更新到最新版！

> 💡 更新代码后，下一次自动运行就会使用最新版本。你也可以手动去 Actions 触发一次。

---

---

# 🖥️ 方式二：在自己电脑上运行

> 适合想在本地看实时数据、或者想自己折腾的朋友。

## 准备工作

### 📋 你需要：
- 一台 Mac 电脑（Windows 也可以，见下方说明）
- 网络连接

---

## Mac 电脑教程

### 第一步：下载项目代码

**方法A：直接下载 ZIP（最简单）**

1. 打开 👉 **https://github.com/weichenli0909-crypto/stock-report**
2. 点击绿色 **Code** 按钮
3. 选择 **Download ZIP**
4. 找到下载的 zip 文件，双击解压
5. 把解压后的文件夹移到桌面（方便找到）

**方法B：用 Git 克隆（更专业）**

如果你安装了 Git，打开终端（Terminal）输入：
```bash
cd ~/Desktop
git clone https://github.com/weichenli0909-crypto/stock-report.git
```

---

### 第二步：安装 Python 环境

1. 按 `Command + 空格`，搜索 **"终端"**（或 "Terminal"），打开它

2. 检查是否已有 Python，输入：
   ```bash
   python3 --version
   ```
   - 如果显示 `Python 3.x.x`（3.8以上），说明已安装，跳到第三步
   - 如果提示 "command not found" 或弹出安装 Xcode 的提示，继续往下

3. 安装 Python：

   **方法一：通过弹窗安装（最简单）**

   输入 `python3` 后如果弹出提示安装命令行工具，点击 **安装** 即可。

   **方法二：官网下载安装**

   - 打开 👉 https://www.python.org/downloads/
   - 点击黄色的 **Download Python 3.x** 按钮
   - 下载完成后双击安装包，一路点 **继续** → **安装**
   - 安装完成后，重新打开终端，输入 `python3 --version` 验证

---

### 第三步：安装依赖库

在终端中输入以下命令（可以一次性复制粘贴）：

```bash
pip3 install akshare pandas matplotlib numpy scikit-learn
```

等待安装完成（可能需要1-3分钟，取决于网速）。

> ⚠️ 如果提示 `pip3: command not found`，试试：
> ```bash
> python3 -m pip install akshare pandas matplotlib numpy scikit-learn
> ```

---

### 第四步：运行程序

1. 在终端中进入项目目录：
   ```bash
   cd ~/Desktop/stock-report
   ```
   > 如果你的文件夹名字不同，把 `stock-report` 改成实际的文件夹名

2. 运行程序：
   ```bash
   python3 run_workflow.py
   ```

3. 等待约1-2分钟，程序会自动：
   - 采集股票数据
   - 分析数据
   - 生成报告
   - 自动在浏览器中打开报告！

---

### 🎯 创建一键运行快捷方式（推荐！）

为了以后不用每次都打开终端输命令，我们创建一个**双击即可运行**的快捷方式：

1. 在桌面右键 → **新建文稿**（或打开"文本编辑"应用）

2. 粘贴以下内容（把路径改成你的实际路径）：
   ```bash
   #!/bin/bash
   cd ~/Desktop/stock-report
   echo "📊 正在更新股票报告..."
   python3 run_workflow.py
   echo ""
   echo "✅ 完成！报告已在浏览器中打开"
   echo "按任意键关闭..."
   read -n 1
   ```

3. 保存为 `一键更新股票报告.command`（注意后缀是 `.command`）
   - 在文本编辑中：格式 → 制作纯文本 → 保存
   - 文件名填 `一键更新股票报告.command`

4. 给它执行权限，在终端输入：
   ```bash
   chmod +x ~/Desktop/一键更新股票报告.command
   ```

5. 以后每次想更新报告，**双击这个文件就行**！

---

## Windows 电脑教程

### 第一步：下载项目代码

1. 打开 👉 **https://github.com/weichenli0909-crypto/stock-report**
2. 点击绿色 **Code** 按钮 → **Download ZIP**
3. 右键下载的文件 → **全部解压缩**
4. 把文件夹放到桌面

---

### 第二步：安装 Python

1. 打开 👉 **https://www.python.org/downloads/**
2. 点击黄色的 **Download Python 3.x** 按钮下载
3. 双击安装包
4. ⚠️ **重要：勾选底部的 "Add Python to PATH"**（把Python添加到系统路径）
5. 点击 **Install Now**（立即安装）
6. 等待安装完成

验证安装：
- 按 `Win + R`，输入 `cmd`，回车打开命令提示符
- 输入 `python --version`，应该显示版本号

---

### 第三步：安装依赖库

打开命令提示符（`Win + R` → 输入 `cmd` → 回车），输入：

```bash
pip install akshare pandas matplotlib numpy scikit-learn
```

等待安装完成。

---

### 第四步：运行程序

在命令提示符中：

```bash
cd %USERPROFILE%\Desktop\stock-report
python run_workflow.py
```

---

### 🎯 创建一键运行快捷方式（Windows）

1. 在桌面右键 → **新建** → **文本文档**
2. 粘贴以下内容：
   ```bat
   @echo off
   cd /d "%USERPROFILE%\Desktop\stock-report"
   echo 📊 正在更新股票报告...
   python run_workflow.py
   echo.
   echo ✅ 完成！
   pause
   ```
3. 文件 → 另存为 → 文件名填 `一键更新股票报告.bat` → 保存类型选"所有文件"
4. 以后双击这个 `.bat` 文件就能运行了！

---

---

# ❓ 常见问题（FAQ）

## 基础问题

<details>
<summary><b>Q: GitHub 是什么？需要付费吗？</b></summary>

GitHub 是全球最大的代码托管平台，类似于"代码版百度网盘"。注册和使用完全**免费**。我们用它的两个免费功能：
- **GitHub Actions**：免费的自动执行器，帮你定时运行程序
- **GitHub Pages**：免费的网页托管，让你的报告可以通过链接访问

</details>

<details>
<summary><b>Q: Fork 是什么意思？</b></summary>

"Fork"（分叉）就是**复制**的意思。你把别人的项目 Fork 一下，就等于复制了一份到你自己的账号下。你对你的副本的任何修改，都不会影响原项目。

</details>

<details>
<summary><b>Q: 我需要会编程吗？</b></summary>

**完全不需要！** 方式一（云端自动运行）全程只需要点鼠标，不需要写任何代码。

</details>

<details>
<summary><b>Q: 这个报告多久更新一次？</b></summary>

设置好后，每个**工作日（周一到周五）** 下午 **15:35**（A股收盘后5分钟）自动更新。周末和节假日不会运行。

你也可以随时手动触发更新（去 Actions 页面点 Run workflow）。

</details>

<details>
<summary><b>Q: 报告里有哪些内容？</b></summary>

- 📈 AI算力、CPO、光模块、光通信、OCS、PCB 六大板块的涨跌排行
- 📊 近30天趋势图、成交量分布、板块资金流向
- 📰 最新板块新闻和市场情绪分析
- 🇺🇸 英伟达、博通等美股行情及对A股的关联影响
- 🤖 机器学习模型预测次日涨跌概率
- 📋 个股详细档案（主营、亮点、风险）

</details>

---

## 使用问题

<details>
<summary><b>Q: Actions 运行失败了怎么办？</b></summary>

1. 点击失败的运行记录（红色 ❌ 的那个）
2. 看看错误信息是什么
3. 常见原因：
   - **网络问题**：数据源偶尔不稳定，等几小时再手动触发一次就好
   - **依赖更新**：点 Sync fork 同步最新代码，通常能解决

如果持续失败，可以在 Issues 页面提问。

</details>

<details>
<summary><b>Q: 报告网页打不开？</b></summary>

1. 确认你已经在 Settings → Pages 中正确设置了 gh-pages 分支
2. 确认至少成功运行了一次 Actions（需要生成报告文件）
3. GitHub Pages 部署需要 2-5 分钟，稍等一会再刷新
4. 确认网址格式正确：`https://你的用户名.github.io/stock-report/`

</details>

<details>
<summary><b>Q: 怎么修改关注的股票？</b></summary>

1. 在你的项目页面，点击 `config.py` 文件
2. 点击右上角的 ✏️ 编辑按钮（铅笔图标）
3. 找到 `STOCK_GROUPS`，按格式添加或删除股票：
   ```python
   "新板块名": {
       "股票代码": "股票名称",
   },
   ```
4. 修改完后，拉到底部点 **Commit changes**（提交修改）
5. 下一次运行就会使用新的股票列表了

> 💡 股票代码就是你在炒股软件里看到的6位数字代码（比如 000001 是平安银行）

</details>

<details>
<summary><b>Q: 怎么手动更新到最新版本？</b></summary>

当原作者发布了新功能：
1. 打开你的项目页面
2. 如果显示 "This branch is X commits behind..."，点击 **Sync fork** → **Update branch**
3. ✅ 完成！新功能就会在下次运行时生效

</details>

<details>
<summary><b>Q: 本地运行时报错 ModuleNotFoundError</b></summary>

说明有依赖没装好，重新运行：
```bash
pip3 install akshare pandas matplotlib numpy scikit-learn
```

如果还报错，试试加 `--upgrade`：
```bash
pip3 install --upgrade akshare pandas matplotlib numpy scikit-learn
```

</details>

<details>
<summary><b>Q: 本地运行时数据是空的？</b></summary>

- 如果是**交易日的交易时间**（9:30-15:00）运行，会获取到实时数据
- 如果是**非交易时间**（晚上/周末），也可以运行！会获取最近一个交易日的收盘数据
- 数据来源是公开的金融接口，偶尔会不稳定，等一会再试即可

</details>

<details>
<summary><b>Q: Mac 上双击 .command 文件提示"无法验证开发者"？</b></summary>

1. 不要双击打开
2. 右键（或 Control + 点击）该文件
3. 选择 **打开**
4. 在弹窗中点 **打开**
5. 之后就可以正常双击运行了

</details>

---

## 进阶问题

<details>
<summary><b>Q: 如何在手机上查看报告？</b></summary>

直接在手机浏览器中打开你的报告链接就行：
```
https://你的用户名.github.io/stock-report/
```
可以添加到手机主屏幕，像 App 一样使用。

</details>

<details>
<summary><b>Q: 可以分享给朋友看吗？</b></summary>

当然可以！直接把你的报告链接发给朋友就行。任何人打开这个链接都能看到最新报告，不需要注册任何东西。

</details>

<details>
<summary><b>Q: GitHub Actions 免费额度够用吗？</b></summary>

完全够用。GitHub 免费账号每月有 **2000 分钟** 的 Actions 运行时间。这个程序每次运行大约 2-3 分钟，每月（约22个工作日）只用不到 **66 分钟**，远远不会超限。

</details>

<details>
<summary><b>Q: 这个会泄露我的隐私吗？</b></summary>

不会。这个项目：
- 不收集任何个人信息
- 不需要你的股票账户
- 只是采集公开的市场数据进行分析
- 报告网页是公开的（任何人都能看到），但只有股票分析内容

</details>

---

# 📋 完整配置流程（一图看懂）

```
┌─────────────────────────────────────────────────────┐
│                                                       │
│   第一步：注册 GitHub                                  │
│   github.com → Sign up → 填邮箱/密码/用户名            │
│                     ↓                                 │
│   第二步：Fork 项目                                    │
│   打开项目页 → 点 Fork → Create fork                   │
│                     ↓                                 │
│   第三步：开启 Actions                                 │
│   Actions 标签 → Enable workflow                       │
│                     ↓                                 │
│   第四步：开启 Pages                                   │
│   Settings → Pages → Branch: gh-pages → Save          │
│                     ↓                                 │
│   第五步：手动运行一次                                  │
│   Actions → Run workflow → 等待完成                     │
│                     ↓                                 │
│   🎉 大功告成！访问：                                   │
│   https://你的用户名.github.io/stock-report/            │
│                                                       │
│   之后每天自动更新，你什么都不用做！                       │
│                                                       │
└─────────────────────────────────────────────────────┘
```

---

# ⚠️ 免责声明

本项目仅供学习 Python 编程使用，所有数据来源于公开接口，**不构成任何投资建议**。投资有风险，入市需谨慎。

---

# 💬 遇到问题？

1. 先看看上面的 [常见问题](#-常见问题faq)
2. 如果还是解决不了，去项目的 **Issues** 页面提问：
   - 打开你的项目页面
   - 点击 **Issues** 标签
   - 点 **New issue**
   - 描述你遇到的问题（附上截图更好）

---

<p align="center">
  Made with ❤️ | 让每个人都能享受数据驱动的投资研究
</p>
