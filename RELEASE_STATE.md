# claude-workflow-bootstrap Release State

**Date:** 2026-05-17
**Branch:** pilot-production
**Commit:** 18a8473
**Status:** Production Ready

## 系统定位

**Claude Plan + Local Coder Workflow Bootstrap**

这是 Leo 的完整 coding workflow 一键恢复包，用于在新 MacBook 上快速恢复结构化开发工作流。

## 系统架构

```
Claude Planner
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
```

## 核心组件

### 规划层
- **claude-plan** - 正式开发模式 wrapper
- `.project-ai/` - 工作状态目录

### 执行层
- **local-coder** - 本地 AI 执行器
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

### 验证层
- **bootstrap-verify** - 安装验证
- **bootstrap_self_test.py** - 自检脚本

### Skills
- **mattpocock/skills** - 第三方 skills
- **bootstrap-install-skills** - 安装脚本
- **skill-router** - 自动路由

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
| health | 系统健康检查 | ✓ |
| metrics | 统计指标 | ✓ |
| failures | 失败分析 | ✓ |
| compact | 数据压缩 | (--dry-run) |
| stuck-workers | 卡住的 workers | ✓ |
| clean | 临时文件清理 | (--apply) |

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

## 下一阶段

**oMLX Backend Migration**
- 迁移到 Apple Silicon 本地推理
- 提升模型质量
- 改善 prompt 遵循度
