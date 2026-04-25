# claude-workflow-bootstrap

一套跨 AI / 跨设备的 Claude (及任何 AI 编程工具) 工作流复刻包。**目的**: 让我在任何新电脑上花 5 分钟就能复刻同样的"提计划→GitHub 自动建 repo→任何 AI 接棒"工作流。

## 含什么

```
claude-workflow-bootstrap/
├── PROMPT.md              # ⭐ 给新机器 AI 的提示词 (主入口)
├── bootstrap.sh           # 一键 setup 脚本
├── README.md              # 本文件
├── templates/             # 项目 scaffold 模板 (AGENTS.md / spec.md / handoff.md / README.md / gitignore)
└── bin/
    └── ai-project-init.sh # `ai-project-init <repo> "<目标>"` scaffold 命令
```

## 在新机器复刻

**有 AI 帮忙 (推荐)**: 把 [`PROMPT.md`](PROMPT.md) 整段贴给新机器的 AI, 让它跑 setup。

**手动**: 

```bash
brew install gh    # 需要 Homebrew (https://brew.sh)
git clone git@github.com:leoredrum/claude-workflow-bootstrap.git ~/claude-workflow-bootstrap
cd ~/claude-workflow-bootstrap && bash bootstrap.sh
gh auth login      # 走一次浏览器
```

## 设计取舍

- **Memory 不放 repo**: `~/.claude/projects/-Users-<你>/memory/` 是 Claude 私人偏好, 跨机器同步靠 `scp/rsync` 手动一次性, 不进 git (避免敏感信息泄漏 + 多机不同 Claude session 互相覆盖)
- **gh 用 SSH protocol**: 已有 GitHub SSH key 的机器零成本; 没 key 的临时切 HTTPS + PAT, 一次后转 SSH
- **bootstrap.sh 幂等**: 已存在文件不覆盖, 重复跑无副作用
- **不动 ~/.zshrc**: 假设 `~/bin` 在 PATH, 不行就靠 `/usr/local/bin/` symlink 兜底

## 升级

修了 templates 或 bin/ 之后:
```
git add -A && git commit -m "feat: <改动描述>" && git push
```

新机器拉新 setup:
```
cd ~/claude-workflow-bootstrap && git pull && bash bootstrap.sh
```

bootstrap.sh 不会覆盖已存在文件 — 想强刷模板, 删掉 `~/.claude/ai-project-templates/` 再跑一遍。
