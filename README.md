# Claude Plan + Local Coder Workflow Bootstrap

**Leo 的完整 coding workflow 一键恢复包。**

在一台新 MacBook 上花 5 分钟就能恢复完整的结构化开发工作流：
- claude-plan（正式开发模式）
- local-coder（本地 AI 执行器）
- workflow-orchestrator（工作流编排）
- workflow-query（状态查询）
- workflow-admin（系统运维）
- SQLite workflow state
- mattpocock skills integration

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
```bash
claude-plan
```
结构化开发工作流：
- 创建 `.project-ai/` 工作目录
- 任务分解和约束定义
- local-coder 执行实现
- 约束验证和违规记录

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

## 限制

1. **不是 oMLX** - 当前使用 Ollama + qwen2.5-coder:32b
2. **不适合无人值守高风险任务** - 需要人工审核
3. **本地模型遵循度** - anchor 精确性仍有瓶颈
4. **Context Window 不会自动刷新** - 长会话需要手动轮换

### Context Rotation（会话轮换）

Claude Code **不会自动刷新**上下文窗口。当会话过长时会卡死。

**在长任务中，每完成一个阶段必须检查：**
```bash
workflow-admin context
```

**如果输出 ROTATE_REQUIRED：**
- 停止实现，不要硬撑
- 运行 `workflow-admin handoff`
- 新开 `claude-plan` 会话
- 运行 `workflow-admin resume` 获取恢复命令

**新会话恢复步骤：**
1. 新开 `claude-plan`
2. 运行 `workflow-admin resume`，复制输出
3. 将恢复 prompt 粘贴到新会话中

## 下一阶段

**oMLX Backend Migration**
- 迁移到 Apple Silicon 本地推理
- 提升模型质量
- 改善 prompt 遵循度

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
