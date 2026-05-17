# Claude Plan + Local Coder Workflow Bootstrap

**Leo 的多 Agent 工作流一键恢复包。**

在一台新 MacBook 上花 5 分钟就能恢复完整的结构化开发工作流：
- claude-plan（正式开发模式）
- local-coder（本地 AI 执行器）
- workflow-orchestrator（工作流编排）
- workflow-query（状态查询）
- workflow-admin（系统运维）
- SQLite workflow state
- mattpocock skills integration

---

## 项目定位

这是 **Claude Plan + Local Coder 多 Agent 工作流恢复包**。

### 系统组成

| 组件 | 功能 | 说明 |
|------|------|------|
| **Claude 主 agent** | 理解需求、规划、审查、汇报 | claude / claude-plan |
| **workflow-orchestrator** | 任务排队、分配、恢复 | 工作流调度层 |
| **local-coder** | 本地子 agent，实际代码修改 | Ollama + qwen2.5-coder:32b |
| **reviewer/tester** | 代码审查和测试 | 降低乱改风险 |
| **SQLite + .project-ai** | 长期记忆和恢复 | 状态持久化 |
| **workflow-admin** | 系统运维和监控 | health、context、handoff |
| **skill-router** | 自动选择合适的 skill | mattpocock/skills 白名单 |

### 多 Agent 协作流程

```
用户
  ↓
Claude 主 agent（理解需求、规划任务、审查结果、汇报）
  ↓
workflow-orchestrator（排队、分配任务、恢复状态）
  ↓
local-coder 本地子 agent（Ollama + qwen2.5-coder:32b）
  ↓ 实际修改代码
reviewer/tester workers（审查变更、运行测试）
  ↓
SQLite / HANDOFF / SESSION_HANDOFF（记录状态、支持会话恢复）
  ↓
Claude 主 agent（汇报结果）
```

**重要说明：local-coder 是子 agent**
- Claude 主 agent **不直接写代码**
- 所有代码修改由 local-coder 本地子 agent 执行
- 主 agent 只负责规划、审查、汇报
- 这样节省主 agent 上下文，避免长会话失忆

### 当前后端配置

- **本地后端**: Ollama + qwen2.5-coder:32b
- **运行方式**: 本地、离线可用
- **未接入**: oMLX（下一阶段）

---

## 为什么要这样做

### 问题

1. **Claude 长会话失忆** - context window 达到上限后，Claude 会"忘记"前面的内容
2. **任务状态丢失** - 刷新会话后，之前的任务进度全部丢失
3. **重复性工作浪费主 agent** - 简单的代码修改不应该消耗昂贵的 Claude API
4. **新电脑恢复困难** - 换电脑后需要重新配置整套开发环境

### 解决方案

1. **主 agent + 本地子 agent 分工**
   - Claude 主 agent：理解需求、规划、审查、汇报
   - local-coder 子 agent：实际代码修改
   - 节省主 agent 上下文

2. **状态持久化**
   - 任务状态写入 SQLite
   - 会话状态写入 .project-ai/HANDOFF.md
   - 支持会话恢复

3. **本地模型承担重复工作**
   - local-coder 使用 Ollama + qwen2.5-coder:32b
   - 离线可用
   - 降低 API 成本

4. **降低乱改风险**
   - reviewer worker 审查代码变更
   - tester worker 运行测试
   - 约束系统：allowed_files、forbidden_new_files

5. **新电脑一键恢复**
   - git clone + ./install.sh
   - 自动安装所有组件
   - 从 GitHub 恢复整套环境

---

## 当前架构

**主 agent + 本地子 agent 模式**

```
Claude Planner
    ↓
workflow-orchestrator
    ↓
local-coder → Ollama/qwen2.5-coder:32b
    ↓
reviewer/tester
    ↓
SQLite/.project-ai
```

**当前 backend:** Ollama + qwen2.5-coder:32b（本地、离线可用）

**未接入:** oMLX（下一阶段）

---

## mattpocock/skills 集成

### 来源

https://github.com/mattpocock/skills

### 集成方式

- **白名单方式**：不是全量安装
- **skill-router 自动选择**：根据任务类型自动路由
- **只能用于规划/诊断**：不允许绕过 local-coder → reviewer → tester pipeline

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

### 使用限制

**Skills 只用于：**
- planning（规划）
- diagnosis（诊断）
- TDD（测试驱动开发）
- handoff（会话交接）
- 架构理解

**Skills 不能：**
- 直接修改代码
- 绕过 local-coder
- 跳过 reviewer/tester

---

## 核心能力

### 约束系统
- `allowed_files` - 限制只能修改指定文件
- `forbidden_new_files` - 禁止创建新文件

### Edit Commands
- `replace_text` - 精确文本替换
- `insert_after` - anchor 后插入
- `insert_before` - anchor 前插入

### 安全保护
- Anchor 验证（不存在/多次匹配 → BLOCKED）
- 大文件覆盖保护（>200 行 → BLOCKED）
- Loop detection
- 违规记录

## 新机器一键安装

### 一行命令（推荐）

需要 macOS + Homebrew + git：

```bash
curl -fsSL https://raw.githubusercontent.com/leoredrum/claude-workflow-bootstrap/main/install.sh | bash
```

### 手动安装

```bash
# 1. Clone repo
git clone https://github.com/leoredrum/claude-workflow-bootstrap.git ~/claude-workflow-bootstrap

# 2. 运行安装
cd ~/claude-workflow-bootstrap && ./install.sh

# 3. 验证安装
bootstrap-verify
```

## 使用方式

### 普通模式
```bash
claude
```
直接对话式编程、快速原型、代码重构。

### 正式开发模式

#### claude-plan（普通正式开发）
```bash
claude-plan
```
标准结构化工作流：
- 创建 `.project-ai/` 工作目录
- 任务分解和约束定义
- local-coder 执行实现
- 约束验证和违规记录
- **需手动处理会话轮换和交接**

#### claude-plan-supervised（自动监控模式）
```bash
claude-plan-supervised
```
带自动监控的结构化工作流：
- 包含 claude-plan 的所有能力
- **自动监控会话健康状态**
- **自动生成 HANDOFF.md 交接文件**
- **自动生成新会话恢复命令**
- supervisor + handoff + resume 近似自动续接

**重要说明**：
- 当前仍不是官方无缝续接
- 是 supervisor + handoff + resume 的近似自动续接
- 会话轮换时仍需手动启动新会话并粘贴 resume 命令
- 目标是逐步接近真正的自动续接体验

### 健康检查
```bash
bootstrap-verify              # 基础验证
bootstrap-verify --doctor     # 诊断模式
```

### 系统运维
```bash
workflow-admin health          # 系统健康检查
workflow-admin metrics         # 统计指标
workflow-admin failures        # 失败分析
workflow-admin compact         # 数据压缩
workflow-admin stuck-workers   # 卡住的 workers
workflow-admin clean           # 清理临时文件
```

### Skill 路由
```bash
skill-router "如何优化 Python 性能"
```
自动选择最合适的 mattpocock skill。

## 验收记录

| 功能 | 状态 | 日期 |
|------|------|------|
| target-file constraints | ✅ PASS | 2026-05-17 |
| edit-mode commands | ✅ PASS | 2026-05-17 |
| crawler --verbose 真实任务 | ✅ PASS | 2026-05-17 |
| workflow-admin | ✅ PASS | 2026-05-17 |

## Context Window Limit 问题

### 重要说明

**Claude Code 的 context window limit 不会自动刷新。**

这不是额度问题，而是当前会话上下文满了。当会话过长时：
- Claude 会"忘记"前面的内容
- 输出质量下降
- 可能直接卡死

### 解决方法

**不要硬撑，而是使用 session rotation（会话轮换）。**

#### 检查 context 健康

```bash
workflow-admin context
```

输出示例：
```
🔍 Context Window Check
==================================================

📄 HANDOFF.md:
  ✓ 24 lines (threshold: 300)

📄 MEMORY.md:
  ✓ File not found (OK)

🗄️  SQLite Session Tasks:
  ✓ 2 tasks (threshold: 5)

==================================================
✅ OK - Context window is healthy
```

#### 如果输出 ROTATE_REQUIRED

```
❌ ROTATE_REQUIRED
   2 warnings >= 2 thresholds

⚠️  Action required:
   workflow-admin handoff
```

#### 会话轮换步骤

1. **生成会话交接文件**
   ```bash
   workflow-admin handoff
   ```
   生成 `.project-ai/SESSION_HANDOFF.md`

2. **新开 claude-plan 会话**

3. **获取恢复命令**
   ```bash
   workflow-admin resume
   ```
   复制输出，粘贴到新会话中

### 阈值设置

| 检查项 | 阈值 |
|--------|------|
| HANDOFF.md | > 300 行 → WARN |
| MEMORY.md | > 500 行 → WARN |
| PATCH.diff | > 800 行 → WARN |
| Session tasks | > 5 → WARN |
| **2+ WARN** | → **ROTATE_REQUIRED** |

---

## 限制

1. **不是 oMLX** - 当前使用 Ollama + qwen2.5-coder:32b
2. **不适合无人值守高风险任务** - 需要人工审核
3. **本地模型遵循度** - anchor 精确性仍有瓶颈
4. **Context Window 不会自动刷新** - 长会话需要手动轮换
5. **大型重构需要人工确认** - 不建议完全自动化

## 下一阶段

### oMLX Backend Migration

- 迁移到 Apple Silicon 本地推理
- 提升模型质量
- 改善 prompt 遵循度

### Backend Adapter 清理

- 清理旧的 backend adapter
- 统一 backend 接口
- 支持多 backend 切换

### 更强本地 Coder 模型测试

- 测试 Ollama 其他模型
- 测试 oMLX 模型
- Benchmark 对比

## 故障排除

### claude-plan not found
```bash
export PATH="$HOME/bin:$PATH"
echo 'export PATH="$HOME/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

### local-coder fails
```bash
# 检查 Ollama
ollama serve

# 验证模型
ollama list | grep qwen
```

### 验证失败
```bash
bootstrap-verify --doctor
```

## 设计取舍

- **Memory 不放 repo** - 个人偏好，手动同步
- **gh 用 SSH protocol** - 零成本复用现有 key
- **bootstrap.sh 幂等** - 重复跑无副作用
- **不动 ~/.zshrc** - 假设 ~/bin 在 PATH

## 升级

```bash
cd ~/claude-workflow-bootstrap
git pull
./install.sh
```

## License

MIT
