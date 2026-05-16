#!/usr/bin/env bash
# install.sh — 一键入口。在新机器跑:
#   curl -fsSL https://raw.githubusercontent.com/leoredrum/claude-workflow-bootstrap/main/install.sh | bash
#
# 干的事:
#   1. 前置检查 (macOS / brew / git)
#   2. clone repo 到 ~/claude-workflow-bootstrap (已存在则 git pull)
#   3. 跑 bootstrap.sh (装 gh / 复制 templates / 复制 script + symlink / haha 桥接)
#   4. 提示用户跑 gh auth login + 可选 memory 同步

set -euo pipefail

REPO_URL="https://github.com/leoredrum/claude-workflow-bootstrap.git"
REPO_DIR="$HOME/claude-workflow-bootstrap"

echo "==> claude-workflow-bootstrap installer"
echo

# 1. 系统前置
case "$(uname)" in
    Darwin) ;;  # mac OK
    Linux) echo "⚠ Linux 未充分测试, 继续 (brew install gh 不可用时手动装 gh)" ;;
    *) echo "❌ 不支持的系统: $(uname)"; exit 1 ;;
esac

if ! command -v git >/dev/null 2>&1; then
    echo "❌ 需要 git。macOS: 跑 'xcode-select --install' 装 Xcode CLT"
    exit 1
fi

if ! command -v brew >/dev/null 2>&1 && [[ "$(uname)" == "Darwin" ]]; then
    echo "❌ 需要 Homebrew。先去 https://brew.sh 装好再跑这个"
    exit 1
fi

# 2. clone or pull
if [[ -d "$REPO_DIR/.git" ]]; then
    echo "==> 已有 $REPO_DIR, git pull"
    (cd "$REPO_DIR" && git pull --ff-only)
else
    echo "==> git clone → $REPO_DIR"
    git clone --depth 1 "$REPO_URL" "$REPO_DIR"
fi

# 3. bootstrap
echo
echo "==> 跑 bootstrap.sh"
echo
cd "$REPO_DIR"
bash bootstrap.sh

# 4. Install bootstrap-verify
echo "==> Installing bootstrap-verify..."
INSTALL_DIR="$HOME/AI/local-coder"
mkdir -p "$INSTALL_DIR/bin"
install -m 755 "$REPO_DIR/files/bin/bootstrap_self_test.py" "$INSTALL_DIR/bin/"
install -m 755 "$REPO_DIR/files/bin/bootstrap-verify" "$HOME/bin/"

# 5. 下一步
cat <<'EOF'

═════════════════════════════════════════════════════════════
✅ Install 完成. 还差 1 步:

  gh auth login

  交互选: GitHub.com → SSH → Skip → Login with a web browser
  → 看到 device code, 浏览器去 https://github.com/login/device 粘贴授权

完了验证:
  gh auth status                    # 返 ✓ Logged in as <你>
  bootstrap-verify                  # 验证安装完整性
  ai-project-init                   # 返用法说明
  claude-plan                       # 返用法说明 (规划工具)
  local-coder                       # 返用法说明 (本地编码工具)
  get-secret                        # 返用法说明 (密钥管理工具)

命令说明:
  • claude      → 主命令 (日常交互、编程)
  • claude-plan → 规划工具 (项目规划、架构设计、任务分解)

验证安装:
  bootstrap-verify                  # 运行完整验证
  bootstrap-verify --doctor         # 诊断模式

可选: 从老机器 scp memory (Claude 私人偏好):
  scp -r <老机器>:~/.claude/projects/-Users-<你>/memory/ \
        ~/.claude/projects/-Users-$(whoami)//

═════════════════════════════════════════════════════════════
EOF
