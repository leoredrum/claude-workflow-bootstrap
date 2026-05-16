# Project CLAUDE.md Template

This is a template for project-specific CLAUDE.md files. Copy this file to your project root and customize it for your needs.

<!-- LEO_CLAUDE_PLAN_WORKFLOW_START -->
## Claude Plan Workflow

This project uses the claude-plan wrapper for structured workflow management.

### Workflow Files (.project-ai/)
- **TASK.md**: Current task description and requirements
- **RESULT.md**: Results and outcomes from completed tasks
- **PATCH.diff**: Patches to be applied with `git apply .project-ai/PATCH.diff`
- **MEMORY.md**: Project-specific learnings and context
- **BUGS.md**: Known bugs and their status
- **DECISIONS.md**: Architectural and implementation decisions
- **HANDOFF.md**: Information for handoff between sessions/developers

### Usage
- Start session: `claude-plan` (automatically sets up workflow structure)
- Update files during development
- Review HANDOFF.md when taking over a project
- Check MEMORY.md for project context

### Implementation Boundary Rules (CRITICAL)

1. **Claude Code Built-in Agents RESTRICTION**
   - Claude Code built-in general-purpose agent is NOT allowed to perform coding implementation
   - Built-in agents MAY ONLY: planning, review, summarize, search, diagnosis

2. **Implementation Requirement**
   - For formal development tasks, implementation MUST be done via: `local-coder .project-ai/TASK.md`
   - This ensures proper local AI execution with full context

3. **Claude Agent Scope**
   - Claude main agent or Claude built-in sub-agents: planning, review, summarize, search, diagnosis ONLY
   - NO direct code writing by Claude agents for formal development tasks

4. **Stub Detection**
   - If local-coder is still a stub, MUST report: "local-coder currently stub; implementation was not actually performed by local AI"

5. **Violation Detection**
   - If code was actually written by Claude itself or general-purpose agent, final report MUST mark as: WORKFLOW VIOLATION

6. **Final Report Requirements**
   Every development session MUST report:
   - **implementation_executor**: local-coder / claude-main / claude-subagent / manual
   - **workflow_status**: PASS / VIOLATION / BLOCKED
   - Files changed (with paths)
   - Commands run (with exit codes)
   - Tests passed/failed (with counts)
   - Remaining risks or concerns
   - Next steps or handover information
<!-- LEO_CLAUDE_PLAN_WORKFLOW_END -->

## Project Overview

[Add project description here]

## Project Structure

[Describe directory structure and key files]

## Development Guidelines

[Add project-specific development guidelines]

## Build and Test Instructions

```bash
# Build commands
# Example: npm run build or make build

# Test commands
# Example: npm test or make test
```

## Dependencies

[List key dependencies and their purposes]

## Configuration

[Describe configuration files and environment variables]

## Common Tasks

[Document common development tasks and workflows]

## Troubleshooting

[Add common issues and solutions]
