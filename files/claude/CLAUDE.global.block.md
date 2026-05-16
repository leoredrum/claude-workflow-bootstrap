# Global Claude Workflow Rules

<!-- LEO_GLOBAL_WORKFLOW_START -->
## Global Workflow Rules

These rules apply to all Claude Code sessions across all projects.

### Core Principles

1. **No Secrets in Git**: Never commit cookies, passwords, tokens, or real credentials to git repositories. This includes code, documentation, and commit messages.

2. **Permission Awareness**: Always respect file system permissions and access controls. Never attempt to bypass security restrictions.

3. **Incremental Progress**: Make small, verifiable changes rather than large, risky modifications. Test after each change.

4. **Context Preservation**: Maintain project context through proper documentation and handoff procedures.

### Workflow Standards

1. **Project Structure**:
   - Use `claude-plan` to initialize project workflow structure
   - Maintain `.project-ai/` directory with workflow files
   - Keep CLAUDE.md updated with project-specific context

2. **Task Management**:
   - Document current tasks in `.project-ai/TASK.md`
   - Record results in `.project-ai/RESULT.md`
   - Track decisions in `.project-ai/DECISIONS.md`
   - Maintain handoff notes in `.project-ai/HANDOFF.md`

3. **Implementation Boundary Rules (CRITICAL)**

   - **Claude Code Built-in Agents RESTRICTION**
     - Claude Code built-in general-purpose agent is NOT allowed to perform coding implementation
     - Built-in agents MAY ONLY: planning, review, summarize, search, diagnosis

   - **Implementation Requirement**
     - For formal development tasks, implementation MUST be done via: `local-coder .project-ai/TASK.md`
     - This ensures proper local AI execution with full context

   - **Claude Agent Scope**
     - Claude main agent or Claude built-in sub-agents: planning, review, summarize, search, diagnosis ONLY
     - NO direct code writing by Claude agents for formal development tasks

   - **Stub Detection**
     - If local-coder is still a stub, MUST report: "local-coder currently stub; implementation was not actually performed by local AI"

   - **Violation Detection**
     - If code was actually written by Claude itself or general-purpose agent, final report MUST mark as: WORKFLOW VIOLATION

   - **Final Report Requirements**
     Every development session MUST report:
     - **implementation_executor**: local-coder / claude-main / claude-subagent / manual
     - **workflow_status**: PASS / VIOLATION / BLOCKED
     - Files changed (with paths)
     - Commands run (with exit codes)
     - Tests passed/failed (with counts)
     - Remaining risks or concerns
     - Whether local-coder was used (yes/no)
     - Next steps or handoff information

4. **Code Quality**:
   - Follow existing code style and patterns
   - Write clear, self-documenting code
   - Add comments only when necessary to explain complex logic
   - Prefer readability over cleverness

5. **Git Hygiene**:
   - Commit frequently with clear, descriptive messages
   - Never commit sensitive data (keys, tokens, passwords)
   - Use `.gitignore` to exclude sensitive files
   - Review changes before committing

### Tool Usage Guidelines

1. **Read Operations**: Use Read tool for file contents, not Bash cat/head/tail
2. **File Modifications**: Use Edit tool for changes, not Bash sed/awk
3. **File Creation**: Use Write tool only for new files or complete rewrites
4. **Search Operations**: Use ripgrep (rg) for code searches, not grep
5. **Background Tasks**: Use run_in_background for long-running operations

### Error Handling

1. **Graceful Degradation**: When tools fail, provide clear error messages
2. **Recovery**: Suggest recovery steps when operations fail
3. **Logging**: Maintain clear logs of operations for debugging
4. **Validation**: Validate inputs and preconditions before execution

### Security Practices

1. **Input Validation**: Always validate user input and file paths
2. **Safe Execution**: Never execute untrusted code or commands
3. **Secret Management**: Use secure tools like `get-secret` for credential access
4. **Permissions**: Respect file system permissions and access controls

### Communication Standards

1. **Clear Status Updates**: Report progress clearly and concisely
2. **Actionable Feedback**: Provide specific, actionable suggestions
3. **Context Awareness**: Maintain awareness of project state and history
4. **Question Clarity**: Ask specific, well-formed questions when clarification is needed

<!-- LEO_GLOBAL_WORKFLOW_END -->


## Skills Integration (mattpocock/skills)

This workflow includes whitelisted skills from mattpocock/skills for specialized guidance.

### Whitelisted Skills

- **diagnose** - Debug and troubleshoot issues
- **tdd** - Test-driven development guidance
- **handoff** - Session handoff and context compression
- **zoom-out** - Understand codebase architecture
- **grill-with-docs** - Clarify ambiguous requirements
- **to-prd** - Convert requirements to PRD format
- **to-issues** - Break down tasks into issues
- **improve-codebase-architecture** - Code quality improvements
- **git-guardrails-claude-code** - Git operation guidance

### Skill Routing Rules

Claude should automatically select appropriate skills based on task content:

- Bug/error/crash → `/diagnose`
- Test/pytest → `/tdd`
- Unclear/ambiguous → `/grill-with-docs`
- Handoff/handover → `/handoff`
- Architecture/structure → `/zoom-out`
- PRD/requirements → `/to-prd`
- Issue breakdown → `/to-issues`
- Code quality/refactor → `/improve-codebase-architecture`
- Git operations → `/git-guardrails-claude-code`

### Skill Constraints

1. **Skills are for guidance only** - They help with planning, diagnosis, and documentation
2. **Implementation must use local-coder** - Skills cannot bypass the implementation pipeline
3. **Pipeline must be respected** - All code changes go through: implementation → review → test
4. **Conflict resolution** - If skill suggests something that conflicts with claude-plan workflow, claude-plan workflow takes precedence
5. **No skill auto-execution** - Skills provide recommendations; Claude executes via local-coder

### Using Skills

To invoke a skill:
```
Use /skill-name in conversation with Claude
Example: /diagnose "The login module is failing"
```

To auto-route a task:
```bash
skill-router "fix the login bug"
```

### Installing Skills

After bootstrap installation:
```bash
# Install whitelisted skills
bootstrap-install-skills

# Update skills
bootstrap-update-skills
```
