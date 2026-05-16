# New MacBook Setup Guide

Complete setup for claude-plan workflow on a new MacBook.

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

```bash
# Install whitelisted mattpocock skills
bootstrap-install-skills

# Verify installation
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
