"""
🚀 一键部署报告到 GitHub Pages
对方通过固定链接随时查看最新报告，每次运行工作流后执行此脚本即可更新
"""

import os
import sys
import subprocess
import shutil

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output")
DEPLOY_DIR = os.path.join(SCRIPT_DIR, "gh-pages")
REPORT_FILE = os.path.join(OUTPUT_DIR, "report.html")


def run_cmd(cmd, cwd=None):
    """执行命令并返回输出"""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def deploy():
    print()
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║                                                              ║")
    print("║   🚀  一键部署报告到 GitHub Pages                            ║")
    print("║                                                              ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()

    # 1. 检查报告是否存在
    if not os.path.exists(REPORT_FILE):
        print("  ❌ 未找到报告！请先运行: python3 run_workflow.py")
        return

    # 2. 检查 git
    code, _, _ = run_cmd("git --version")
    if code != 0:
        print("  ❌ 未安装 git")
        return

    # 3. 检查是否已有 gh-pages 目录
    repo_name = "stock-report"
    if os.path.exists(DEPLOY_DIR):
        print("  📂 使用已有的部署目录")
    else:
        # 检查是否有远程仓库
        print("  📦 初始化部署目录...")
        os.makedirs(DEPLOY_DIR, exist_ok=True)
        run_cmd("git init", cwd=DEPLOY_DIR)
        run_cmd("git checkout -b gh-pages", cwd=DEPLOY_DIR)

    # 4. 复制报告文件
    print("  📋 复制报告文件...")
    # 复制 report.html 为 index.html（GitHub Pages 默认入口）
    shutil.copy2(REPORT_FILE, os.path.join(DEPLOY_DIR, "index.html"))
    # 同时保留 report.html
    shutil.copy2(REPORT_FILE, os.path.join(DEPLOY_DIR, "report.html"))
    # 复制图表图片
    for f in os.listdir(OUTPUT_DIR):
        if f.endswith(".png"):
            shutil.copy2(os.path.join(OUTPUT_DIR, f), os.path.join(DEPLOY_DIR, f))

    # 5. Git 提交
    print("  📝 提交更新...")
    run_cmd("git add -A", cwd=DEPLOY_DIR)
    from datetime import datetime

    msg = f"📊 更新报告 {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    run_cmd(f'git commit -m "{msg}" --allow-empty', cwd=DEPLOY_DIR)

    # 6. 检查是否已配置远程仓库
    code, remote, _ = run_cmd("git remote get-url origin", cwd=DEPLOY_DIR)
    if code != 0:
        print()
        print("  ⚠️ 还需要一步：创建 GitHub 仓库并关联")
        print()
        print("  📖 操作步骤（只需做一次）：")
        print("  ─────────────────────────────────────────")
        print("  1️⃣  打开 https://github.com/new")
        print(f"  2️⃣  仓库名填: {repo_name}")
        print("  3️⃣  选择 Public（公开），点击 Create repository")
        print("  4️⃣  回到这里，运行以下命令：")
        print()
        print(f"     cd {DEPLOY_DIR}")
        print(
            f"     git remote add origin https://github.com/你的用户名/{repo_name}.git"
        )
        print(f"     git push -u origin gh-pages")
        print()
        print("  5️⃣  打开仓库 Settings → Pages → Branch 选择 gh-pages → Save")
        print()
        print(f"  ✅ 之后你的报告链接就是:")
        print(f"     https://你的用户名.github.io/{repo_name}/")
        print()
        print("  📱 把这个链接发给任何人，对方随时打开都是最新报告！")
        print("  💡 以后每次更新只需运行: python3 deploy_pages.py")
    else:
        # 已配置远程，直接推送
        print("  🚀 推送到 GitHub...")
        code, out, err = run_cmd("git push origin gh-pages", cwd=DEPLOY_DIR)
        if code == 0:
            # 解析仓库 URL
            repo_url = remote.replace(".git", "").replace("https://github.com/", "")
            pages_url = (
                f"https://{repo_url.split('/')[0]}.github.io/{repo_url.split('/')[1]}/"
            )
            print()
            print("  ✅ 部署成功！")
            print()
            print(f"  🔗 分享链接: {pages_url}")
            print(f"     把这个链接发给任何人即可查看最新报告！")
        else:
            print(f"  ❌ 推送失败: {err}")
            print("  💡 请检查 GitHub 认证是否配置正确")

    print()


if __name__ == "__main__":
    deploy()
