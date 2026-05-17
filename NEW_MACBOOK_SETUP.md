# New MacBook Setup Guide

Complete setup for **Claude Plan + Local Coder 多 Agent 工作流** on a new MacBook.

## 系统说明

这是一套多 Agent 协作的开发工作流：

- **Claude 主 agent**: 理解需求、规划任务、审查结果、汇报
- **local-coder 本地子 agent**: 实际代码修改（Ollama + qwen2.5-coder:32b）
- **workflow-orchestrator**: 任务排队、分配、恢复
- **reviewer/tester**: 代码审查和测试
- **SQLite + .project-ai**: 长期记忆和会话恢复

**重要**: Claude 主 agent **不直接写代码**，所有代码修改由 local-coder 本地子 agent 执行。

## 不会备份的内容

⚠️ 这套系统 **不会** 备份以下内容：
- 密码、API Key、Token
- macOS Keychain
- 本地 Ollama 模型（需要重新 pull）
- oMLX 模型
- runtime DB、log 文件

你需要自行备份这些敏感信息。

## Step 1: System Prerequisites

macOS Sonoma (14.0+) or later required.

## Step 2: Install Homebrew

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Follow the post-install instructions to add Homebrew to your PATH.

## Step 3: Install Git

```bash
brew install git
```

## Step 4: Install Python

```bash
brew install python@3.11
```

Verify:
```bash
python3 --version  # Should show 3.11.x
```

## Step 5: (Optional) Install Ollama

For local-coder functionality:

```bash
brew install ollama
ollama serve &

# Pull recommended model
ollama pull qwen2.5-coder:32b
```

## Step 6: Clone Bootstrap Repository

```bash
git clone https://github.com/leoredrum/claude-workflow-bootstrap.git
cd claude-workflow-bootstrap
```

## Step 7: Run Installation

```bash
./install.sh
```

This installs:
- claude-plan → ~/bin/
- local-coder → ~/AI/local-coder/bin/
- workflow-orchestrator → ~/AI/local-coder/bin/
- workflow-query → ~/AI/local-coder/bin/
- bootstrap-verify → ~/bin/
- CLAUDE config → ~/.claude/CLAUDE.md

## Step 8: Verify Installation

```bash
# Run verification
bootstrap-verify

# Expected output: All checks PASS
# Report saved to: bootstrap-verification-report.md
```

## Step 9: (Optional) Doctor Check

If verification has issues:

```bash
bootstrap-verify --doctor

# This will diagnose:
# - Broken symlinks
# - Missing components
# - Stale databases
# - Worker issues
```

## Step 10: GitHub Authentication

```bash
gh auth login
```

Interactive steps:
1. Select: GitHub.com
2. Select: SSH
3. Select: Skip
4. Select: Login with a web browser
5. Enter device code at https://github.com/login/device

Verify:
```bash
gh auth status  # Should return: Logged in as <your-username>
```

## Step 11: Start First Project

```bash
# Create project directory
mkdir my-first-project
cd my-first-project

# Initialize with claude-plan
claude-plan

# Or manually:
mkdir .project-ai
cat > .project-ai/TASK.md << 'EOF'
# Task: Initialize Project

Create hello.py with "Hello, World!"
EOF

# Run local-coder
local-coder .project-ai/TASK.md

# Check results
cat .project-ai/RESULT.md
cat .project-ai/PATCH.diff

# Query database
workflow-query stats
```

## Verification Checklist

- [ ] Homebrew installed
- [ ] Git installed
- [ ] Python 3.11+ installed
- [ ] claude-workflow-bootstrapped cloned
- [ ] install.sh completed successfully
- [ ] claude-plan command works
- [ ] local-coder command works
- [ ] bootstrap-verify passes all checks
- [ ] GitHub authentication completed
- [ ] First project created successfully

## Next Steps

1. Review CLAUDE.md for workflow rules
2. Read MACBOOK_RECOVERY.md for detailed documentation
3. Start using claude-plan for real projects

## 使用方式

### 普通模式
```bash
claude
```
直接对话，快速原型。

### 正式开发模式
```bash
claude-plan
```
结构化开发工作流：
- 创建 `.project-ai/` 工作目录
- TASK.md（任务定义 + 约束）
- RESULT.md（执行结果）
- PATCH.diff（代码变更）

### 健康检查
```bash
bootstrap-verify              # 基础验证
bootstrap-verify --doctor     # 诊断模式
```

### 系统运维
```bash
workflow-admin health          # 系统健康检查
workflow-admin context         # Context window 状态检查
workflow-admin handoff         # 生成会话交接文件
workflow-admin resume          # 生成新会话恢复命令
```

### 技能路由
```bash
skill-router "修复 crawler 登录失败 bug"
```
自动选择最合适的 mattpocock skill。

## Uninstallation

```bash
# Remove scripts
rm ~/bin/claude-plan
rm ~/bin/bootstrap-verify
rm -rf ~/AI/local-coder

# Remove config
rm ~/.claude/CLAUDE.md

# Project data (.project-ai/) is preserved
```

## Support

For issues:
1. Run `bootstrap-verify --doctor`
2. Check verification report
3. Review GitHub issues

## Step 9.5: Install Skills (Optional)

For specialized task guidance:

### mattpocock/skills 说明

- **来源**: https://github.com/mattpocock/skills
- **集成方式**: 白名单方式（不是全量安装）
- **用途**: planning、diagnosis、TDD、handoff、架构理解
- **限制**: 不能绕过 local-coder → reviewer → tester pipeline

### 安装

```bash
# Install whitelisted mattpocock skills
bootstrap-install-skills

# Verify installation
ls ~/.claude/skills/

# Available skills
echo "diagnose, tdd, handoff, zoom-out, grill-with-docs, to-prd, to-issues, improve-codebase-architecture, git-guardrails-claude-code, setup-matt-pocock-skills"
```

### 当前白名单

| Skill | 用途 |
|-------|------|
| diagnose | 调试和故障诊断 |
| tdd | 测试驱动开发指导 |
| handoff | 会话交接和上下文压缩 |
| zoom-out | 理解代码库架构 |
| grill-with-docs | 澄清模糊需求 |
| to-prd | 转换为 PRD 格式 |
| to-issues | 分解为 issue |
| improve-codebase-architecture | 代码质量改进 |
| git-guardrails-claude-code | Git 操作指导 |
| setup-matt-pocock-skills | 安装 mattpocock skills |

### Using Skills
ls ~/.claude/skills/

# Available skills
echo "diagnose, tdd, handoff, zoom-out, grill-with-docs, to-prd, to-issues, improve-codebase-architecture, git-guardrails-claude-code"
```

### Using Skills

```bash
# Auto-route task to skill
skill-router "fix the login bug"

# Use skill in Claude
Claude> /diagnose "error in authentication"
```
