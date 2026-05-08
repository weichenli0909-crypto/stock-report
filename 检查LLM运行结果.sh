#!/bin/bash
# 🧠 检查最近一次 GitHub Actions 中 LLM 舆情模块的运行结果
# 用法：bash 检查LLM运行结果.sh

REPO="weichenli0909-crypto/stock-report"

echo "=============================="
echo "🧠 LLM 舆情运行结果检查工具"
echo "=============================="
echo ""

# 最新 run ID
RUN_ID=$(gh run list --repo "$REPO" --workflow=update-report.yml --limit 1 --json databaseId,status,conclusion -q '.[0].databaseId')
STATUS=$(gh run list --repo "$REPO" --workflow=update-report.yml --limit 1 --json status -q '.[0].status')
CONCLUSION=$(gh run list --repo "$REPO" --workflow=update-report.yml --limit 1 --json conclusion -q '.[0].conclusion')

echo "📌 最新 run: $RUN_ID ($STATUS/$CONCLUSION)"

if [[ "$STATUS" != "completed" ]]; then
  echo ""
  echo "⏳ 还在运行中，请 3-5 分钟后重试"
  echo "   在线查看: https://github.com/$REPO/actions/runs/$RUN_ID"
  exit 0
fi

echo ""
echo "=============================="
echo "📋 LLM 相关日志片段"
echo "=============================="
gh run view "$RUN_ID" --repo "$REPO" --log 2>&1 | \
  grep -E "(STEP 2\.5|🧠|LLM|DeepSeek|DEEPSEEK|OPENAI|最利好|最利空|预估成本|缓存命中|LLM 调用)" | \
  head -40 | sed 's/^.*| //'

echo ""
echo "=============================="
echo "💰 成本 & 效果摘要"
echo "=============================="
gh run view "$RUN_ID" --repo "$REPO" --log 2>&1 | \
  grep -E "(LLM 调用|预估成本|处理股票|缓存累计)" | \
  head -10 | sed 's/^.*| //'

echo ""
echo "📖 完整日志：https://github.com/$REPO/actions/runs/$RUN_ID"
echo "📄 最新报告：https://weichenli0909-crypto.github.io/stock-report/"
