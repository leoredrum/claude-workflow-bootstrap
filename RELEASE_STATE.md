# claude-workflow-bootstrap Release State

**Date:** 2026-05-17
**Branch:** pilot-production
**Commit:** 18a8473
**Status:** Production Ready

## 系统定位

**Claude Plan + Local Coder 多 Agent 工作流 Bootstrap**

这是 Leo 的多 Agent 工作流一键恢复包，用于在新 MacBook 上快速恢复完整的结构化开发工作流。

### 多 Agent 架构说明

本系统采用 **主 agent + 本地子 agent** 模式：

- **Claude 主 agent**: 负责理解需求、规划任务、审查结果、汇报
- **local-coder 本地子 agent**: 负责实际代码修改
- **workflow-orchestrator**: 负责任务排队、分配、恢复
- **reviewer/tester**: 负责代码审查和测试

**重要**: Claude 主 agent **不直接写代码**，所有代码修改由 local-coder 本地子 agent 执行。这样设计是为了：
- 节省主 agent 上下文
- 避免 Claude 长会话失忆
- 把任务状态写入文件和 SQLite
- 让本地模型承担重复 coding 工作

## 系统架构

```
用户
  ↓ 理解需求
Claude 主 agent（claude / claude-plan）
  ↓ 规划任务
workflow-orchestrator
  ↓ 编排任务队列
local-coder (local_coder_worker.py)
  ↓ 调用 AI
Ollama/qwen2.5-coder:32b
  ↓ 生成代码
reviewer/tester workers
  ↓ 验证结果
SQLite (.project-ai/workflow_state.db)
  ↓ 记录状态
Claude 主 agent
  ↓ 汇报结果
```

## 核心组件

### 规划层
- **claude-plan** - 正式开发模式 wrapper
- `.project-ai/` - 工作状态目录（TASK.md、RESULT.md、PATCH.diff、HANDOFF.md）

### 执行层
- **local-coder** - 本地 AI 执行器（子 agent）
- **local_coder_worker.py** - Python worker 实现

### 编排层
- **workflow-orchestrator** - 任务编排 CLI
- **workflow_orchestrator.py** - Python 实现
- **workflow_db.py** - SQLite 状态管理

### 查询层
- **workflow-query** - 状态查询 CLI
- **workflow-query.py** - Python 实现

### 运维层
- **workflow-admin** - 系统维护 CLI
  - health: 系统健康检查
  - context: Context window 状态检查
  - handoff: 生成会话交接文件
  - resume: 生成新会话恢复命令

### 验证层
- **bootstrap-verify** - 安装验证
- **bootstrap_self_test.py** - 自检脚本

### Skills
- **mattpocock/skills** - 第三方 skills（白名单方式）
  - 来源: https://github.com/mattpocock/skills
  - 安装: bootstrap-install-skills
  - 路由: skill-router

## 使用模式

### 1. 普通模式
```bash
claude
```
直接对话，快速原型。

### 2. 正式开发模式
```bash
claude-plan
```
结构化工作流：
- TASK.md（任务定义 + 约束）
- RESULT.md（执行结果）
- PATCH.diff（代码变更）

## 当前 Backend

**Ollama + qwen2.5-coder:32b**
- 本地运行
- 离线可用
- 支持 edit-mode commands

**未接入：**
- oMLX（下一阶段）

## local-coder 能力

### 约束系统
- `allowed_files` - 限制只能修改指定文件
- `forbidden_new_files` - 禁止创建新文件

### Edit Commands
- `replace_text` - 精确文本替换
- `insert_after` - anchor 后插入
- `insert_before` - anchor 前插入
- `append_file` - 追加内容

### 安全保护
- Anchor 验证（不存在/多次匹配 → BLOCKED）
- 大文件覆盖保护（>200 行 → BLOCKED）
- 路径安全检查
- Loop detection

## workflow-admin 命令

| 命令 | 功能 | 只读 |
|------|------|------|
| health | 系统健康检查（含 context） | ✓ |
| context | Context window 状态检查 | ✓ |
| handoff | 生成会话交接文件 | ✗ |
| resume | 生成新会话恢复命令 | ✓ |
| metrics | 统计指标 | ✓ |
| failures | 失败分析 | ✓ |
| compact | 数据压缩 | (--dry-run) |
| stuck-workers | 卡住的 workers | ✓ |
| clean | 临时文件清理 | (--apply) |

## Context Rotation（会话轮换）

Claude Code **不会自动刷新**上下文窗口。长会话会卡死。

**阈值：**
- HANDOFF.md > 300 行 → WARN
- MEMORY.md > 500 行 → WARN
- PATCH.diff > 800 行 → WARN
- 当前 session 任务数 > 5 → WARN
- 任意两个 WARN → ROTATE_REQUIRED

**使用流程：**
```bash
# 检查 context
workflow-admin context

# 如果需要轮换
workflow-admin handoff  # 生成 SESSION_HANDOFF.md
# 新开 claude-plan 会话
workflow-admin resume   # 获取恢复 prompt
```

## mattpocock Skills 白名单

### 批准
- diagnose, tdd, handoff, zoom-out
- grill-with-docs, to-prd, to-issues
- improve-codebase-architecture
- git-guardrails-claude-code

### 排除
- prototype, triage, caveman
- write-a-skill, migrate-to-shoehorn
- scaffold-exercises, setup-pre-commit

## 新 MacBook 恢复

### 一键安装
```bash
curl -fsSL https://raw.githubusercontent.com/leoredrum/claude-workflow-bootstrap/main/install.sh | bash
```

### 验证
```bash
bootstrap-verify
bootstrap-verify --doctor
```

### 检查健康
```bash
workflow-admin health
```

## 验收记录

| 功能 | 状态 | 日期 |
|------|------|------|
| target-file constraints | ✅ PASS | 2026-05-17 |
| edit-mode commands | ✅ PASS | 2026-05-17 |
| crawler --verbose | ✅ PASS | 2026-05-17 |
| workflow-admin | ✅ PASS | 2026-05-17 |

## 当前限制

1. **模型遵循度** - qwen2.5-coder:32b 偶尔忽略 prompt
2. **Anchor 精确性** - 需要用户提供精确 anchor
3. **无人值守** - 不适合高风险自动任务
4. **Context Window** - 不会自动刷新，需要 session rotation
5. **大型重构** - 需要人工确认，不建议完全自动化

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
