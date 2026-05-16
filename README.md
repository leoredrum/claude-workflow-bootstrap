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

### 一行命令 (推荐)

需要 macOS + Homebrew + git (Xcode CLT). repo 必须 public 才能无认证 clone:

```bash
curl -fsSL https://raw.githubusercontent.com/leoredrum/claude-workflow-bootstrap/main/install.sh | bash
```

跑完后再 `gh auth login` 走浏览器一次, 就齐了。

### 验证安装

运行以下命令确认所有工具正常:

```bash
# GitHub CLI 验证
gh auth status                    # 应返回: ✓ Logged in as <你的用户名>

# 项目工具验证
ai-project-init                   # 应返回用法说明
claude-plan                       # 应返回用法说明 (规划工具)
local-coder                       # 应返回用法说明 (本地编码工具)
get-secret                        # 应返回用法说明 (密钥管理工具)

# 完整安装验证
bootstrap-verify                  # 运行完整验证检查
```

如果任何检查失败,运行诊断模式:

```bash
bootstrap-verify --doctor         # 诊断模式 - 查找问题
```

验证报告将保存为 `bootstrap-verification-report.md` 在当前目录。

### 让 AI 帮跑

把 [`PROMPT.md`](PROMPT.md) 整段贴给新机器的 AI, 让它跑 setup + 给你核对清单。

### 手动逐步

```bash
# 1. 安装 GitHub CLI
brew install gh

# 2. Clone 仓库
git clone https://github.com/leoredrum/claude-workflow-bootstrap.git ~/claude-workflow-bootstrap

# 3. 运行 bootstrap 脚本
cd ~/claude-workflow-bootstrap && bash bootstrap.sh

# 4. GitHub 认证 (一次性)
gh auth login

# 5. 验证安装
gh auth status                    # 应返回: ✓ Logged in as <你的用户名>
ai-project-init                   # 应返回用法说明
claude-plan                       # 应返回用法说明 (规划工具)
local-coder                       # 应返回用法说明 (本地编码工具)
get-secret                        # 应返回用法说明 (密钥管理工具)
```

## Claude vs Claude-plan

- **claude** → 主命令 (日常交互、编程)
  - 直接对话式编程
  - 快速原型开发
  - 代码重构和调试
  - 文件操作和 Git 管理

- **claude-plan** → 规划工具 (项目规划、架构设计、任务分解)
  - 正式开发模式
  - 自动创建 `.project-ai/` 工作目录
  - 结构化项目规划
  - 任务分解和依赖管理
  - 架构设计文档生成

## Secret 管理规则

⚠️ **安全第一**: 永远不要把以下内容写进 git (代码/文档/commit msg 都不行):
- Cookie / 密码 / Token / 真实凭证
- API Keys / Access Tokens / Session IDs
- 私人配置 / 环境变量 / 凭证文件

**推荐做法**:
```bash
# 使用 get-secret 从 macOS Keychain 读取敏感信息
get-secret <service-name> <account-name>

# 例如: 获取 GitHub Token
get-secret github api-token
```

## 故障排除

### claude-plan not found
```bash
# 确保 ~/bin 在 PATH 中
export PATH="$HOME/bin:$PATH"
echo 'export PATH="$HOME/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

### local-coder fails
```bash
# 检查 Ollama 是否运行
ollama serve

# 验证模型是否可用
ollama list | grep qwen
```

### 验证失败
运行诊断模式来识别具体问题:
```bash
bootstrap-verify --doctor
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

## Pilot Testing

### Production Pilot Program (2025-05-17)

This project participated in a production pilot to validate the claude-plan workflow across multiple real projects:

**Projects Tested:**
1. crawler-workspace - Documentation enhancements
2. imagecreator-workspace - Documentation metadata additions
3. claude-workflow-bootstrap - README pilot section

**Pilot Results:**
- 9/9 tasks completed successfully (100% success rate)
- All tasks were low-risk documentation additions
- Zero unsafe write blocks
- Zero workflow violations

**Key Findings:**
- Direct execution mode works reliably for simple tasks
- Documentation changes are safe and predictable
- Version tracking in markdown files improves maintainability
