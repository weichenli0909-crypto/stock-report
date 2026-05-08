# 🧠 LLM 舆情分析接入指南（3 分钟搞定）

## 📖 这是什么

把股票新闻标题交给大模型（DeepSeek / GPT / 通义千问）打分，替代老的"数关键词"方案。

### 对比示例

| 新闻标题 | 旧方案（关键词） | 新方案（LLM）|
|---|---|---|
| "Q3 业绩同比增长 180%" | 0（中性，无关键词）| +2（重大利好）|
| "收到政府补贴 5000 万元" | +1（"补贴"）| +1（偏利好）|
| "CFO 辞职" | 0（中性）| -1（偏利空，人事不稳）|
| "突破关键技术"（其实是技术债务突破天花板）| +1（"突破"误判）| 0（LLM 能看懂是吐槽）|

---

## 🚀 接入步骤（推荐用 DeepSeek，最便宜）

### Step 1：注册 DeepSeek 账号

1. 打开 https://platform.deepseek.com/
2. 注册账号（手机号即可）
3. 左侧菜单 → **API Keys** → 点 **创建 API Key**
4. 复制 key（形如 `sk-xxxxxxxxxxxxxxxx`，只显示一次，务必保存）
5. 充值：账号里充 **¥10 就够用 1 年以上**（每天跑一次 ≈ ¥0.05）

### Step 2：配置到 GitHub Secrets（让线上 Actions 自动跑）

1. 打开你的仓库：https://github.com/weichenli0909-crypto/stock-report
2. 点 **Settings** → 左侧 **Secrets and variables** → **Actions**
3. 点 **New repository secret**
4. Name 填：`DEEPSEEK_API_KEY`
5. Secret 粘贴刚才的 `sk-xxx`
6. 点 **Add secret**

✅ **完成**！下一次 Actions 跑时会自动用 LLM 分析舆情。

### Step 3：（可选）本地测试

```bash
cd /Users/ruby/Desktop/python/data_workflow
export DEEPSEEK_API_KEY="sk-你的key"
python3 step1b_llm_sentiment.py --test    # 小样本测试 3 只股票
```

---

## 💰 成本估算

| 平台 | 单次调用 | 每天 30 只股票 | 每月 |
|---|---|---|---|
| 🥇 **DeepSeek**（推荐）| ¥0.001 | ¥0.03 | **¥0.9** |
| 🥈 通义 Qwen-turbo | ¥0.0003 | ¥0.01 | **¥0.3** |
| 🥉 OpenAI gpt-4o-mini | ¥0.01 | ¥0.3 | ¥9 |

此外还有**本地缓存**：同一条新闻标题只问 LLM 一次，实际成本 < 上表 30%。

---

## 🛡️ 安全机制（自动保护你）

1. **没 API key 静默降级**：不影响主流程，会 fallback 到关键词法
2. **LLM 请求失败自动重试**：最多 3 次
3. **结果异常自动丢弃**：保持老的情绪分
4. **本地缓存去重**：不会对同一条新闻重复收费
5. **每只股票限 5 条新闻**：不会超支

---

## 🔄 切换 LLM 提供商

**用通义千问（阿里）**：
- Secret Name: `DASHSCOPE_API_KEY`
- 注册: https://dashscope.aliyun.com/

**用 OpenAI**：
- Secret Name: `OPENAI_API_KEY`
- 如果在国内需要代理，可以改 `step1b_llm_sentiment.py` 里的 `endpoint`

优先级：`DEEPSEEK → OPENAI → DASHSCOPE`（按配置的顺序）

---

## 📊 效果验证

配置好后，等 Actions 跑完，打开：
- 报告页面会看到"🔥 LLM 最利好 Top 5"和"❄️ LLM 最利空 Top 5"
- `data/news_YYYYMMDD.json` 里每条新闻会多出 `llm_score` 和 `llm_reason` 字段
- 预测日志里会打印 `🧠 使用 LLM 舆情分析 (deepseek/deepseek-chat)`

---

## 🤔 常见问题

**Q：为什么推荐 DeepSeek？**
A：国内可直连无需代理、最便宜、中文新闻理解能力和 GPT-4 接近。

**Q：什么时候值得升级到 GPT-4o？**
A：如果 DeepSeek 出现明显误判（比如把中性新闻判为利好），且你不在乎每月 ¥10 左右的成本差异。

**Q：能否用本地模型（Ollama + qwen2）？**
A：可以，但 GitHub Actions 没 GPU 跑不动；如果你本地跑，可以在 `step1b_llm_sentiment.py` 里加一个 `ollama` provider。

**Q：缓存会无限增长吗？**
A：现在不会清理。估计 1 年后会累积 ~10000 条，JSON 文件 ~2MB，可以接受。后期可以加个"超过 30 天未命中则清理"。
