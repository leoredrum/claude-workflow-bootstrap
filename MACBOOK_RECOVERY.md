# MacBook New Machine Recovery Checklist

## 系统说明

这是一套 **Claude Plan + Local Coder 多 Agent 工作流**：

- **Claude 主 agent**: 理解需求、规划任务、审查结果、汇报
- **local-coder 本地子 agent**: 实际代码修改（Ollama + qwen2.5-coder:32b）
- **workflow-orchestrator**: 任务排队、分配、恢复
- **reviewer/tester**: 代码审查和测试
- **SQLite + .project-ai**: 长期记忆和会话恢复

**重要**: Claude 主 agent **不直接写代码**，所有代码修改由 local-coder 本地子 agent 执行。

## Prerequisites

- macOS 14+ (Sonoma or later)
- Homebrew installed
- Git installed
- Python 3.10+ installed
- Ollama installed (optional, for local-coder backend)

## Step 1: Clone Bootstrap Repository

```bash
git clone https://github.com/leoredrum/claude-workflow-bootstrap.git
cd claude-workflow-bootstrap
```

## Step 2: Run Installation

```bash
./install.sh
```

This will install:
- `claude-plan` → ~/bin/
- `local-coder` → ~/AI/local-coder/bin/
- `workflow-orchestrator` → ~/AI/local-coder/bin/
- `workflow-query` → ~/AI/local-coder/bin/
- CLAUDE global config → ~/.claude/CLAUDE.md

## Step 3: Verify Installation

```bash
# Check claude-plan
which claude-plan
claude-plan --help

# Check local-coder
which local-coder
local-coder --help

# Check workflow-orchestrator
which workflow-orchestrator
workflow-orchestrator --help

# Check workflow-query
which workflow-query
workflow-query --help
```

## Step 4: Configure Environment (Optional)

```bash
# Set local-coder model
export LOCAL_CODER_MODEL=qwen2.5-coder:32b

# Set local-coder backend
export LOCAL_CODER_BACKEND=ollama

# Set max files per run
export LOCAL_CODER_MAX_FILES=5
```

Add to ~/.zshrc or ~/.bashrc for persistence.

## Step 5: Start First Project

```bash
# Create new project
mkdir my-project
cd my-project

# Initialize with claude-plan
claude-plan

# Or manually create .project-ai structure
mkdir .project-ai
cat > .project-ai/TASK.md << 'EOF'
# Task: Initialize Project

Create initial project structure.
EOF

# Run local-coder
local-coder .project-ai/TASK.md

# Query results
workflow-query stats
workflow-query recent-files
```

## Components Installed

| Component | Location | Purpose |
|-----------|----------|---------|
| claude-plan | ~/bin/ | Workflow initialization |
| local-coder | ~/AI/local-coder/bin/ | Implementation worker |
| workflow_db.py | ~/AI/local-coder/bin/ | SQLite state database |
| memory_compactor.py | ~/AI/local-coder/bin/ | Memory compression |
| workflow-orchestrator | ~/AI/local-coder/bin/ | Task scheduler |
| workflow-query | ~/AI/local-coder/bin/ | Query CLI for state |
| CLAUDE.global.block.md | ~/.claude/ | Global Claude rules |

## Troubleshooting

### claude-plan not found
```bash
# Add ~/bin to PATH
export PATH="$HOME/bin:$PATH"
echo 'export PATH="$HOME/bin:$PATH"' >> ~/.zshrc
```

### local-coder fails
```bash
# Check Ollama is running
ollama serve

# Check model is available
ollama list
```

### workflow-query fails
```bash
# Check database exists
ls -la .project-ai/workflow_state.db
```

## Next Steps

1. Create your first project with `claude-plan`
2. Write task in `.project-ai/TASK.md`
3. Run `local-coder .project-ai/TASK.md`
4. Review results in `.project-ai/RESULT.md`
5. Query state with `workflow-query stats`

## Advanced Usage

### Multi-worker setup
```bash
# Start implementer worker
workflow-orchestrator start --worker-id impl-1 --type implementer &

# Start reviewer worker
workflow-orchestrator start --worker-id rev-1 --type reviewer &

# Start tester worker
workflow-orchestrator start --worker-id test-1 --type tester &

# Enqueue task
workflow-orchestrator enqueue "My task summary" --type implementer
```

### Session restore
```bash
# Restore previous session
workflow-query session-restore

# Get attempt history
cat .project-ai/ATTEMPT_HISTORY.md
```

### Memory compaction
```bash
# Run compactor
python3 ~/AI/local-coder/bin/memory_compactor.py .project-ai
```

## Uninstallation

```bash
# Remove scripts
rm ~/bin/claude-plan
rm ~/AI/local-coder/bin/local-coder
rm ~/AI/local-coder/bin/workflow-*
rm ~/AI/local-coder/bin/memory_compactor.py

# Remove configs
rm ~/.claude/CLAUDE.md

# Note: Project data (.project-ai/) is preserved
```
