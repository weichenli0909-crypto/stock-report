#!/bin/bash
# 用 Weichen Li 个人 Chrome Profile (Default) 打开 URL
# 用法：bash 个人号打开.sh https://github.com/...
URL="${1:-https://github.com/weichenli0909-crypto/stock-report/actions}"
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --profile-directory="Default" "$URL" > /dev/null 2>&1 &
echo "✅ 已用 Weichen Li 个人 Chrome 打开：$URL"
