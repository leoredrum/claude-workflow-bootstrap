#!/usr/bin/env bash
# ai-project-init.sh — Bootstrap a new AI-agnostic project repo.
#
# 用法:
#   ai-project-init.sh <repo-name> "<一句话目标>"
#   ai-project-init.sh <repo-name> "<一句话目标>" [--public]
#
# 作用:
#   1. 当前目录 (或 ./<repo-name>) 初始化 git
#   2. 从 ~/.claude/ai-project-templates/ 拷 README.md / AGENTS.md /
#      docs/spec.md / docs/handoff.md / .gitignore, 填 {{占位符}}
#   3. gh repo create <repo-name> --private (或 --public) 建 GitHub repo
#   4. 加 origin + 首个 commit + push
#
# 前置:
#   - gh CLI 已装 + `gh auth login` 完成
#   - ~/.claude/ai-project-templates/ 存在
#
# 环境变量:
#   AI_PROJECT_TEMPLATES  模板目录 (默认 ~/.claude/ai-project-templates)
#   AI_PROJECT_GH_USER    GitHub 用户名 (默认 从 gh api user 查)

set -euo pipefail

if [[ $# -lt 2 ]]; then
    cat <<EOF >&2
用法: $(basename "$0") <repo-name> "<一句话目标>" [--public]

示例:
  $(basename "$0") kxo-bot "Komga 连载漫画自动同步 bot"
  $(basename "$0") my-scraper "抓某站每日更新" --public
EOF
    exit 1
fi

REPO_NAME="$1"
GOAL="$2"
VISIBILITY="--private"
if [[ "${3:-}" == "--public" ]]; then
    VISIBILITY="--public"
fi

TEMPLATES="${AI_PROJECT_TEMPLATES:-$HOME/.claude/ai-project-templates}"
if [[ ! -d "$TEMPLATES" ]]; then
    echo "❌ 模板目录不存在: $TEMPLATES" >&2
    exit 1
fi

if ! command -v gh >/dev/null 2>&1; then
    echo "❌ 需要 gh CLI: brew install gh && gh auth login" >&2
    exit 1
fi

if ! gh auth status >/dev/null 2>&1; then
    echo "❌ gh 未登录: gh auth login" >&2
    exit 1
fi

GH_USER="${AI_PROJECT_GH_USER:-$(gh api user --jq .login)}"
if [[ -z "$GH_USER" ]]; then
    echo "❌ 查不到 GitHub 用户名" >&2
    exit 1
fi

# 判断目标目录: 当前目录是否已经是 repo-name, 否则新建
CWD_NAME="$(basename "$PWD")"
if [[ "$CWD_NAME" == "$REPO_NAME" ]]; then
    TARGET="$PWD"
    echo "→ 在当前目录 $TARGET 初始化"
else
    TARGET="$PWD/$REPO_NAME"
    if [[ -e "$TARGET" ]]; then
        echo "❌ $TARGET 已存在, 换个名字或进去跑" >&2
        exit 1
    fi
    mkdir -p "$TARGET"
    echo "→ 新建目录 $TARGET"
fi

cd "$TARGET"

# 1. git init (若未 init)
if [[ ! -d .git ]]; then
    git init -q -b main
    echo "→ git init (main branch)"
fi

# 2. 拷模板 + 填占位符
INIT_DATE="$(date +%Y-%m-%d)"

render() {
    local src="$1" dst="$2"
    sed -e "s|{{PROJECT_NAME}}|${REPO_NAME}|g" \
        -e "s|{{ONE_LINE_GOAL}}|${GOAL}|g" \
        -e "s|{{INIT_DATE}}|${INIT_DATE}|g" \
        -e "s|{{USER}}|${GH_USER}|g" \
        "$src" > "$dst"
}

mkdir -p docs
[[ -f README.md ]]       || render "$TEMPLATES/README.md"  README.md
[[ -f AGENTS.md ]]       || cp "$TEMPLATES/AGENTS.md" AGENTS.md
[[ -f docs/spec.md ]]    || render "$TEMPLATES/spec.md"    docs/spec.md
[[ -f docs/handoff.md ]] || render "$TEMPLATES/handoff.md" docs/handoff.md
[[ -f .gitignore ]]      || cp "$TEMPLATES/gitignore" .gitignore

echo "→ 填好模板: README / AGENTS / docs/spec / docs/handoff / .gitignore"

# 3. gh repo create (若 github 上不存在)
if gh repo view "$GH_USER/$REPO_NAME" >/dev/null 2>&1; then
    echo "→ GitHub 上 $GH_USER/$REPO_NAME 已存在, 跳过创建"
else
    gh repo create "$REPO_NAME" $VISIBILITY \
        --description "$GOAL" \
        --disable-wiki \
        >/dev/null
    echo "→ 建好 GitHub repo: $GH_USER/$REPO_NAME ($VISIBILITY)"
fi

# 4. 加 remote (幂等) + commit + push
if ! git remote get-url origin >/dev/null 2>&1; then
    git remote add origin "git@github.com:$GH_USER/$REPO_NAME.git"
    echo "→ 加 origin remote"
fi

git add -A
if git diff --cached --quiet; then
    echo "→ 无新增文件, 跳过 commit"
else
    git commit -q -m "chore: 项目初始化 (ai-project-init)

- scaffold: README / AGENTS / docs/{spec,handoff} / .gitignore
- 目标: $GOAL"
    echo "→ 首个 commit 建好"
fi

# 推, 幂等: 远端已有 commit 时用 fetch + rebase 再 push
git fetch origin main 2>/dev/null || true
if git rev-parse --verify origin/main >/dev/null 2>&1; then
    git pull --rebase origin main >/dev/null 2>&1 || true
fi
git push -u origin main 2>&1 | tail -3

echo
echo "✅ $REPO_NAME 建好了"
echo "   本地: $TARGET"
echo "   远端: https://github.com/$GH_USER/$REPO_NAME"
echo
echo "下一步: 和 AI 讨论填完 docs/spec.md 的 TBD, 然后开干"
