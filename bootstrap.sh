#!/usr/bin/env bash
# bootstrap.sh — 在新机器上复刻 leo 的 Claude 跨 AI 接棒工作流。
#
# 跑这个脚本会:
#   1. 装 gh CLI (如未装) — Homebrew 必须存在
#   2. 复制 templates/ → ~/.claude/ai-project-templates/
#   3. 复制 bin/ai-project-init.sh → ~/bin/, symlink 到 /usr/local/bin/ai-project-init
#   4. 如果有 ~/.claude-haha/ 也桥接 (templates 共用 + memory 共用)
#   5. 提示用户跑 `gh auth login` (一次性, 走浏览器授权)
#
# 不做的事:
#   - 不动你 memory (~/.claude/projects/-Users-leo/memory/) — 这是私人偏好,
#     需要的话用 scp/rsync 手动从老机器同步
#   - 不动 ~/.zshrc — 假设 ~/bin 已在 PATH (大部分 zsh 默认), 否则 symlink 兜底
#   - 不重写已有文件 — 模板 / 脚本如果你已有, 跳过

set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
echo "→ bootstrap from: $REPO_DIR"

# 1. gh CLI
if ! command -v gh >/dev/null 2>&1; then
    if ! command -v brew >/dev/null 2>&1; then
        echo "❌ 需要 Homebrew (https://brew.sh) 先装好" >&2
        exit 1
    fi
    echo "→ brew install gh"
    brew install gh
else
    echo "→ gh 已装: $(gh --version | head -1)"
fi

# 2. templates
TEMPLATE_DST="$HOME/.claude/ai-project-templates"
mkdir -p "$TEMPLATE_DST"
for f in templates/*; do
    name="$(basename "$f")"
    if [[ -e "$TEMPLATE_DST/$name" ]]; then
        echo "→ 跳过已存在: $TEMPLATE_DST/$name"
    else
        cp "$f" "$TEMPLATE_DST/$name"
        echo "→ 装好 $TEMPLATE_DST/$name"
    fi
done

# 3. bin script + symlink
mkdir -p "$HOME/bin"
if [[ ! -e "$HOME/bin/ai-project-init.sh" ]]; then
    cp bin/ai-project-init.sh "$HOME/bin/ai-project-init.sh"
    chmod +x "$HOME/bin/ai-project-init.sh"
    echo "→ 装好 ~/bin/ai-project-init.sh"
fi

if [[ ! -e /usr/local/bin/ai-project-init ]]; then
    if [[ -w /usr/local/bin ]]; then
        ln -s "$HOME/bin/ai-project-init.sh" /usr/local/bin/ai-project-init
        echo "→ symlinked /usr/local/bin/ai-project-init"
    else
        echo "⚠ /usr/local/bin 不可写, 跳过 symlink. 用绝对路径 ~/bin/ai-project-init.sh 调"
    fi
fi

# 4. claude-haha 桥接 (如装了)
if [[ -d "$HOME/.claude-haha" ]]; then
    if [[ ! -e "$HOME/.claude-haha/ai-project-templates" ]]; then
        ln -s "$HOME/.claude/ai-project-templates" "$HOME/.claude-haha/ai-project-templates"
        echo "→ haha templates 桥接"
    fi
    mkdir -p "$HOME/.claude-haha/projects/-Users-$(whoami)"
    if [[ ! -e "$HOME/.claude-haha/projects/-Users-$(whoami)/memory" ]] \
        && [[ -d "$HOME/.claude/projects/-Users-$(whoami)/memory" ]]; then
        ln -s "$HOME/.claude/projects/-Users-$(whoami)/memory" \
              "$HOME/.claude-haha/projects/-Users-$(whoami)/memory"
        echo "→ haha memory 桥接"
    fi
fi

# 5. 验证
echo
echo "✅ bootstrap 装好"
echo

echo "下一步 (一次性):"
echo "  ! gh auth login    # 浏览器走一次, 登 GitHub"
echo
echo "完成后验证:"
echo "  gh auth status"
echo "  ai-project-init    # 没参数会显示用法说明"
echo
echo "Memory (你的私人偏好) 不在本仓库, 想从老机器拿:"
echo "  scp -r <老机器>:~/.claude/projects/-Users-<你>/memory/ ~/.claude/projects/-Users-$(whoami)/"
