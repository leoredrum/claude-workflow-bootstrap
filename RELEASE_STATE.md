# claude-workflow-bootstrap Release State

**Date:** 2026-05-17
**Branch:** pilot-production
**Commit:** 601449c
**Status:** Production Ready

## 系统架构

```
claude-workflow-bootstrap/
├── bootstrap.sh              # 一键安装入口
├── install.sh                # 完整安装脚本
├── files/
│   ├── bin/                  # 可执行工具
│   │   ├── claude-plan       # 正式开发模式 wrapper
│   │   ├── local-coder       # local AI 执行器
│   │   ├── local_coder_worker.py
│   │   ├── workflow-orchestrator  # 工作流编排 CLI
│   │   ├── workflow_orchestrator.py
│   │   ├── workflow-query
│   │   ├── workflow_query.py
│   │   ├── workflow_db.py
│   │   ├── bootstrap-verify  # 安装后验证
│   │   ├── bootstrap_self_test.py
│   │   ├── bootstrap-install-skills  # skills 安装
│   │   ├── bootstrap-update-skills
│   │   ├── skill-router
│   │   └── memory_compactor.py
│   ├── claude/
│   │   └── CLAUDE.global.block.md
│   └── templates/
│       └── project-CLAUDE.md
└── third_party/
    └── mattpocock-skills/    # 第三方 skills
```

## 使用模式

### 1. 普通模式 (Quick Chat)
直接使用 Claude Code：
```bash
claude
```

### 2. 正式开发模式 (claude-plan)
结构化开发工作流：
```bash
claude-plan
# 创建 .project-ai/{TASK.md,RESULT.md,PATCH.diff}
# local-coder 执行实现
# 支持约束验证
```

## 当前 Backend

**Ollama + qwen2.5-coder:32b**
- 本地运行
- 离线可用
- 支持 edit-mode commands

**未接入：**
- oMLX (下一阶段)

## local-coder 当前能力

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

## Workflow Orchestrator

**SQLite state database** (`.project-ai/workflow_state.db`)
- 任务队列管理
- Worker 注册与心跳
- Attempt history
- Violation tracking

**Workers:**
- ImplementerWorker - 执行代码实现
- ReviewerWorker - 代码审查
- TesterWorker - 运行测试

## workflow-admin - 运维工具

**日常维护命令：**

```bash
workflow-admin health          # 系统健康检查
workflow-admin metrics         # 指标统计
workflow-admin failures        # 失败分析
workflow-admin compact         # 数据压缩
workflow-admin stuck-workers   # 检查卡住的 workers
workflow-admin clean           # 清理临时文件
```

**只读命令：** health, metrics, failures, stuck-workers
**需要确认：** compact (默认 --dry-run), clean (需要 --apply)

## mattpocock Skills 白名单

### 批准安装
- diagnose
- tdd
- handoff
- zoom-out
- grill-with-docs
- to-prd
- to-issues
- improve-codebase-architecture
- git-guardrails-claude-code

### 明确排除
- prototype
- triage
- caveman
- write-a-skill
- migrate-to-shoehorn
- scaffold-exercises
- setup-pre-commit

## 新 MacBook 恢复步骤

### 1. 克隆 repo
```bash
git clone https://github.com/leoredrum/claude-workflow-bootstrap.git
cd claude-workflow-bootstrap
```

### 2. 运行安装
```bash
./install.sh
```

### 3. 安装后验证
```bash
bootstrap-verify
```

## 安装后验证

### 基础验证
```bash
bootstrap-verify
```

### 完整诊断
```bash
bootstrap-verify --doctor
```

### 自检
```bash
bootstrap_self_test.py
```

## 当前限制

1. **模型遵循度**
   - qwen2.5-coder:32b 偶尔忽略 prompt 使用 write_file
   - 需要精确的 anchor 文本

2. **Anchor 精确性**
   - 用户需要在 TASK.md 中提供精确 anchor
   - 空格/引号差异会导致 anchor_not_found

3. **适用场景**
   - 适合：结构化修改、明确目标
   - 暂不适合：无人值守高风险任务

## 下一阶段

### oMLX Backend Migration
- 迁移到 Apple Silicon 本地推理
- 提升模型质量
- 改善 prompt 遵循度

### 改进项
- 自动 anchor 检测
- 代码质量 reviewer 增强
- 更好的错误恢复

## 验收记录

| 功能 | 状态 | 日期 |
|------|------|------|
| target-file constraints | ✅ PASS | 2026-05-17 |
| edit-mode commands | ✅ PASS | 2026-05-17 |
| crawler --verbose 真实任务 | ✅ PASS | 2026-05-17 |
| bootstrap skills integration | ✅ PASS | 2026-05-17 |
| bootstrap verify | ✅ PASS | 2026-05-17 |
