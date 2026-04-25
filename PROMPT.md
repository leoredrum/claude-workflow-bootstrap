# 新机器对齐提示词

> 把整段复制粘贴给新机器上的 Claude / Kimi / 智谱 / Codex / 任何能跑 shell 的 AI。它会替你跑完所有 setup。

---

## 提示词 (复制下面整段)

```
我要在这台新机器上复刻一套跨 AI 接棒工作流, 让我换 AI / 换设备都能从 GitHub repo 直接接上进度。请帮我做完整 setup。

目标产物:
- ~/.claude/ai-project-templates/ 含 AGENTS.md / README.md / spec.md / handoff.md / gitignore 5 个模板
- ~/bin/ai-project-init.sh 脚本 (chmod +x), symlink 到 /usr/local/bin/ai-project-init 让全 shell 全局调
- gh CLI 装好且 `gh auth status` 显示已登录 GitHub
- 如果本机有 ~/.claude-haha/, 把 templates 和 memory 桥接 symlink 过去

跑这套脚本一键完成 1-3 项:
  1. cd ~
  2. git clone https://github.com/leoredrum/claude-workflow-bootstrap.git
     (如果是 private repo 用 SSH: git clone git@github.com:leoredrum/claude-workflow-bootstrap.git, 但你要先有这台机器 SSH key 加到 GitHub。
      没 key 的话临时改用 HTTPS + Personal Access Token, 或者让我手动从老机器 scp 整个仓库过来。)
  3. cd claude-workflow-bootstrap && bash bootstrap.sh

完成后:
  4. 跟我说"我已经跑完 bootstrap.sh 没报错"
  5. 我手动跑 `! gh auth login` (走浏览器授权), 在 prompt 选: GitHub.com / SSH / Skip / Login with a web browser. 你看到 device code 后让我去 https://github.com/login/device 手动粘贴授权
  6. 验证 `gh auth status` 返 ✓ Logged in as leoredrum
  7. 验证 `ai-project-init` 返用法说明 (没参数报错)

Memory (我的 Claude 私人偏好) 不在 repo 里, 是我私人的。如果我要从老机器同步:
  scp -r <老机器>:~/.claude/projects/-Users-leo/memory/ ~/.claude/projects/-Users-leo/

memory 同步好后, 你下次启动会自动读到, 你就懂我所有偏好和已建立的工作流。

完成所有这些后给我一份核对清单 (每项 ✅ / ❌), 我对一遍。
```

---

## 备选 (无 AI 时手动跑)

```
brew install gh   # 假设有 Homebrew
mkdir -p ~/.claude/ai-project-templates ~/bin
# clone repo (改 https/ssh 看你 GitHub key 状态)
git clone git@github.com:leoredrum/claude-workflow-bootstrap.git ~/claude-workflow-bootstrap
cd ~/claude-workflow-bootstrap
bash bootstrap.sh
gh auth login   # 走浏览器授权一次
# (可选) 同步 memory
scp -r <老机器>:~/.claude/projects/-Users-leo/memory/ ~/.claude/projects/-Users-leo/
```

---

## 验证清单

- [ ] `gh --version` 返版本号
- [ ] `gh auth status` 显示 `Logged in to github.com account leoredrum`
- [ ] `ls ~/.claude/ai-project-templates/` 列出 5 个模板文件
- [ ] `which ai-project-init` 返 `/usr/local/bin/ai-project-init` (或 `~/bin/ai-project-init.sh`)
- [ ] `ai-project-init` 不带参数返用法说明
- [ ] `ls ~/.claude-haha/ai-project-templates` (如装了 haha) 是个 symlink 指向 `~/.claude/ai-project-templates`
- [ ] (可选) `ls ~/.claude/projects/-Users-leo/memory/MEMORY.md` 存在 (说明 memory 同步过来了)

---

## 验证完之后

任何机器都能继续:
- 接现有 project: `git clone <repo>` → 读 `AGENTS.md` + `docs/handoff.md` → 开干
- 起新 project: `ai-project-init <name> "<目标>"` → 一键 private repo + scaffold + push
