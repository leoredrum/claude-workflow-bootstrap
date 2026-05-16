#!/usr/bin/env python3
"""local-coder worker: reads task, calls Ollama, applies changes."""

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import requests

# Add workflow_db to path
sys.path.insert(0, str(Path(__file__).parent))
from workflow_db import get_db

# Hard guardrails - configurable via env
MAX_FILES_PER_RUN = int(os.getenv("LOCAL_CODER_MAX_FILES", "5"))
MAX_FILE_LINES = int(os.getenv("LOCAL_CODER_MAX_LINES", "3000"))
MAX_PATCH_LINES = int(os.getenv("LOCAL_CODER_MAX_PATCH_LINES", "500"))
DRY_RUN = os.getenv("LOCAL_CODER_DRY_RUN", "0") == "1"


def check_file_size(path: Path, max_lines: int) -> bool:
    """Check if file has too many lines."""
    if path.exists():
        line_count = len(path.read_text().splitlines())
        return line_count <= max_lines
    return True  # New file is OK


def count_patch_lines(patch_content: str) -> int:
    """Count lines in patch."""
    return len([l for l in patch_content.splitlines() if l.startswith('+') or l.startswith('-')])


def record_attempt(project_ai_dir: Path, task_summary: str, files_touched: list, result: str) -> str:
    """Record attempt in history."""
    history_file = project_ai_dir / "ATTEMPT_HISTORY.md"

    task_hash = hashlib.md5(task_summary.encode()).hexdigest()[:8]

    entry = f"""
## Attempt - {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

- Task Hash: {task_hash}
- Files: {', '.join(files_touched) if files_touched else 'None'}
- Result: {result}
"""

    if history_file.exists():
        content = history_file.read_text()
        history_file.write_text(entry + content)
    else:
        history_file.write_text("# Attempt History\n\n" + entry)

    return task_hash


def check_loop_detection(project_ai_dir: Path, task_hash: str) -> bool:
    """Check if same task was attempted 3+ times."""
    history_file = project_ai_dir / "ATTEMPT_HISTORY.md"
    if not history_file.exists():
        return False

    content = history_file.read_text()
    count = content.count(f"Task Hash: {task_hash}")
    return count >= 3


def detect_violation(project_ai_dir: Path) -> bool:
    """Check for workflow violations."""
    result_file = project_ai_dir / "RESULT.md"
    if not result_file.exists():
        return True  # Missing RESULT.md is a violation

    content = result_file.read_text()
    if "implementation_executor: local-coder" not in content:
        return True
    if "backend: ollama" not in content:
        return True

    return False


def record_violation(project_ai_dir: Path, reason: str):
    """Record workflow violation."""
    violation_file = project_ai_dir / "WORKFLOW_VIOLATIONS.md"

    entry = f"""
## Violation - {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

- Reason: {reason}
- Status: UNRESOLVED
"""

    if violation_file.exists():
        content = violation_file.read_text()
        violation_file.write_text(entry + content)
    else:
        violation_file.write_text("# Workflow Violations\n\n" + entry)


def read_context_files(project_ai_dir: Path) -> dict:
    """Read all relevant .project-ai files."""
    context = {}
    for name in ["TASK.md", "MEMORY.md", "HANDOFF.md", "BUGS.md", "DECISIONS.md"]:
        path = project_ai_dir / name
        if path.exists():
            context[name] = path.read_text()
    return context


def build_prompt(context: dict, allowed_files: list = None, forbidden_new: bool = False) -> str:
    """Build the prompt for Ollama with edit-mode instructions."""
    task = context.get("TASK.md", "")

    # Build constraint-specific instructions
    constraint_instructions = ""
    if allowed_files:
        allowed_list = "\n".join(f"  - {f}" for f in allowed_files)
        constraint_instructions = f"""

## Target File Constraints

You are ONLY allowed to modify these files:
{allowed_list}

**CRITICAL EDITING RULES:**
1. For EXISTING files in allowed_files, you MUST use edit commands:
   - replace_text: Replace exact text match
   - insert_after: Insert text after an anchor line
   - insert_before: Insert text before an anchor line

2. Do NOT use write_file for existing allowed files - it will be BLOCKED

3. write_file is ONLY for:
   - Creating new files (if forbidden_new_files allows)
   - Files NOT in allowed_files list

4. Edit command formats:
   - replace_text: {{"type": "replace_text", "path": "path/to/file", "old": "exact old text", "new": "replacement"}}
   - insert_after: {{"type": "insert_after", "path": "path/to/file", "anchor": "exact anchor line", "content": "text to insert"}}
   - insert_before: {{"type": "insert_before", "path": "path/to/file", "anchor": "exact anchor line", "content": "text to insert"}}
"""

    if forbidden_new:
        constraint_instructions += f"""

## New File Restrictions

forbidden_new_files: true - You CANNOT create new files.
Use edit commands on existing allowed files only.
"""

    return f"""You are a local AI coding assistant. Your task is to implement the requested changes based on the task description.

## Task
{task}
{constraint_instructions}
IMPORTANT: Respond ONLY with a valid JSON object in this exact format:
{{
  "summary": "Brief description of what was done",
  "commands": [
    {{"type": "replace_text", "path": "relative/path/to/file", "old": "exact old text to find", "new": "replacement text"}},
    {{"type": "insert_after", "path": "relative/path/to/file", "anchor": "exact anchor line", "content": "text to insert"}},
    {{"type": "insert_before", "path": "relative/path/to/file", "anchor": "exact anchor line", "content": "text to insert"}}
  ],
  "tests": ["test suggestion 1"],
  "risks": ["potential risk 1"]
}}

For NEW files only (if allowed):
  {{"type": "write_file", "path": "relative/path/to/file", "content": "file content"}}
"""


def call_ollama(prompt: str, model: str, endpoint: str) -> str:
    """Call Ollama API."""
    response = requests.post(
        f"{endpoint}/api/chat",
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": {"temperature": 0.2}
        },
        timeout=300
    )
    response.raise_for_status()
    return response.json()["message"]["content"]


def parse_response(raw_output: str) -> dict:
    """Parse JSON response from Ollama."""
    try:
        start = raw_output.find("{")
        end = raw_output.rfind("}") + 1
        if start >= 0 and end > start:
            json_str = raw_output[start:end]
            return json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse JSON: {e}")
    raise ValueError("No JSON found in output")


def check_unsafe_overwrite(project_root: Path, commands: list) -> tuple:
    """Check for unsafe file overwrites."""
    unsafe = []
    safe_commands = []

    for cmd in commands:
        cmd_type = cmd.get("type")
        path_str = cmd.get("path", "")

        if cmd_type == "write_file":
            file_path = project_root / path_str

            # Check if file exists
            if file_path.exists():
                # Check for explicit allow_overwrite
                allow_overwrite = cmd.get("allow_overwrite", False)
                has_replace_keyword = "replace entire file" in str(commands).lower()

                # Protected files
                protected = ["AGENTS.md", "CLAUDE.md", "README.md", ".gitignore", "setup.py", "pyproject.toml", "package.json", "tsconfig.json"]
                is_protected = any(p in path_str for p in protected)

                if not allow_overwrite and not has_replace_keyword:
                    if is_protected:
                        unsafe.append({
                            "path": path_str,
                            "reason": "protected file cannot be overwritten",
                            "suggestion": "use append_file or insert_after"
                        })
                    else:
                        # Check file size
                        try:
                            line_count = len(file_path.read_text().splitlines())
                            if line_count > 200:
                                unsafe.append({
                                    "path": path_str,
                                    "reason": f"file too large ({line_count} lines) to overwrite",
                                    "suggestion": "use insert_after, insert_before, or replace_block"
                                })
                            else:
                                # Small file, allow but convert to safer operation
                                safe_commands.append({
                                    **cmd,
                                    "type": "write_file_safe",
                                    "original_type": "write_file",
                                    "note": "existing file, verify output"
                                })
                        except Exception:
                            safe_commands.append(cmd)
                else:
                    safe_commands.append(cmd)
            else:
                safe_commands.append(cmd)
        else:
            safe_commands.append(cmd)

    return unsafe, safe_commands


def validate_diff(project_root: Path) -> dict:
    """Validate git diff for safety."""
    try:
        result = subprocess.run(
            ["git", "diff", "--numstat"],
            cwd=project_root,
            capture_output=True,
            text=True,
            check=False
        )

        additions = 0
        deletions = 0

        for line in result.stdout.strip().splitlines():
            if line:
                parts = line.split()
                if len(parts) >= 2:
                    additions += int(parts[0]) if parts[0] != "-" else 0
                    deletions += int(parts[1]) if parts[1] != "-" else 0

        # Safety checks
        is_safe = True
        reasons = []

        if deletions > 20:
            is_safe = False
            reasons.append(f"Too many deletions: {deletions} lines")

        if deletions > additions * 2:
            is_safe = False
            reasons.append(f"Deletions ({deletions}) exceed 2x additions ({additions})")

        return {
            "is_safe": is_safe,
            "additions": additions,
            "deletions": deletions,
            "reasons": reasons
        }
    except Exception as e:
        return {"is_safe": False, "additions": 0, "deletions": 0, "reasons": [str(e)]}



def extract_task_constraints(task_content: str) -> dict:
    """Extract allowed_files and forbidden_new_files from TASK.md."""
    constraints = {
        "allowed_files": [],
        "forbidden_new_files": False
    }

    lines = task_content.splitlines()
    in_allowed_files_section = False

    for line in lines:
        stripped = line.strip()

        # Check if we're entering allowed_files section
        if stripped.startswith("allowed_files:"):
            in_allowed_files_section = True
            continue

        # Check if we're leaving the section (next heading or non-list item)
        if in_allowed_files_section:
            if stripped.startswith("- ") or stripped.startswith("  -"):
                file_path = stripped.split("-", 1)[1].strip()
                # Filter out non-file paths (should contain / or . extension)
                if file_path and ('/' in file_path or '.' in file_path):
                    if file_path not in constraints["allowed_files"]:
                        constraints["allowed_files"].append(file_path)
            elif stripped and not stripped.startswith("#"):
                # Non-empty, non-comment line ends the section
                in_allowed_files_section = False

        # Parse forbidden_new_files (can be anywhere)
        if "forbidden_new_files:" in stripped and "true" in stripped.lower():
            constraints["forbidden_new_files"] = True

    return constraints


def validate_target_files(project_root: Path, commands: list, 
                         allowed_files: list, forbidden_new: bool) -> tuple:
    """Validate commands against target file constraints."""
    violations = []
    safe_commands = []
    
    for cmd in commands:
        cmd_type = cmd.get("type")
        path_str = cmd.get("path", "")
        
        if not path_str:
            safe_commands.append(cmd)
            continue
        
        # Check if this is a file creation
        is_new_file = cmd_type in ["write_file"] and not (project_root / path_str).exists()
        
        # Check forbidden_new_files
        if forbidden_new and is_new_file:
            violations.append({
                "type": "forbidden_new_file",
                "path": path_str,
                "reason": "Task forbids creating new files"
            })
            continue
        
        # Check if file is in allowed list
        if allowed_files:
            path_in_allowed = any(
                path_str == af or path_str.endswith("/" + af) or "/" + af in path_str
                for af in allowed_files
            )
            
            if not path_in_allowed and cmd_type in ["write_file", "edit_file", "append_file"]:
                violations.append({
                    "type": "not_allowed_file",
                    "path": path_str,
                    "reason": f"File not in allowed_files: {allowed_files}"
                })
                continue
        
        safe_commands.append(cmd)
    
    return violations, safe_commands


def validate_applied_files(project_root: Path, allowed_files: list = None, 
                          required_files: list = None) -> dict:
    """Validate that applied changes match constraints."""
    import subprocess
    
    # Get changed files
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            cwd=project_root,
            capture_output=True,
            text=True
        )
        applied = [f for f in result.stdout.strip().splitlines() if f]
    except:
        applied = []
    
    validation = {
        "applied_files": applied,
        "unexpected_files": [],
        "missing_files": [],
        "target_file_modified": False
    }
    
    # Check for unexpected files
    if allowed_files:
        for f in applied:
            if not any(f == af or f.endswith("/" + af) for af in allowed_files):
                validation["unexpected_files"].append(f)
    
    # Check for missing required files
    if required_files:
        for req in required_files:
            if not any(req == f or req.endswith("/" + f) for f in applied):
                validation["missing_files"].append(req)
    
    # Check if any target file was modified
    validation["target_file_modified"] = len(applied) > 0 and len(validation["unexpected_files"]) == 0
    
    return validation


def is_safe_path(path: Path, project_root: Path) -> bool:
    """Check if path is safe to write."""
    try:
        abs_path = (project_root / path).resolve()
        project_abs = project_root.resolve()
    except Exception:
        return False

    try:
        abs_path.relative_to(project_abs)
    except ValueError:
        return False

    path_str = str(abs_path).lower()
    dangerous = [
        "/.ssh/", "/.aws/", "/.config/", "/.claude/",
        "/etc/", "/system/", "/library/", "/usr/", "/bin/", "/sbin/"
    ]
    for d in dangerous:
        if d in path_str:
            return False

    filename = abs_path.name.lower()
    secret_keywords = ["secret", "key", "token", "password", "credential"]
    if any(k in filename for k in secret_keywords):
        if ".project-ai" not in path_str or abs_path.suffix not in [".md", ".txt"]:
            return False

    return True


def apply_replace_text(path: Path, old: str, new: str) -> tuple:
    """Apply replace_text command with strict validation.

    Returns: (success, error_reason)
    - success: True if replacement worked
    - error_reason: "anchor_not_found", "ambiguous_anchor", or None
    """
    if not path.exists():
        return False, "file_not_found"

    file_content = path.read_text()

    # Check if old text exists
    if old not in file_content:
        return False, "old_text_not_found"

    # Check for ambiguous match (multiple occurrences)
    count = file_content.count(old)
    if count > 1:
        return False, f"ambiguous_anchor ({count} occurrences)"

    # Perform replacement
    new_content = file_content.replace(old, new, 1)
    path.write_text(new_content)
    return True, None


def apply_insert_after(path: Path, anchor: str, content: str) -> tuple:
    """Apply insert_after command with strict validation.

    Returns: (success, error_reason)
    """
    if not path.exists():
        return False, "file_not_found"

    file_content = path.read_text()

    # Check if anchor exists
    if anchor not in file_content:
        return False, "anchor_not_found"

    # Check for ambiguous match
    count = file_content.count(anchor)
    if count > 1:
        return False, f"ambiguous_anchor ({count} occurrences)"

    # Perform insertion
    new_content = file_content.replace(anchor, anchor + "\n" + content, 1)
    path.write_text(new_content)
    return True, None


def apply_insert_before(path: Path, anchor: str, content: str) -> tuple:
    """Apply insert_before command with strict validation.

    Returns: (success, error_reason)
    """
    if not path.exists():
        return False, "file_not_found"

    file_content = path.read_text()

    # Check if anchor exists
    if anchor not in file_content:
        return False, "anchor_not_found"

    # Check for ambiguous match
    count = file_content.count(anchor)
    if count > 1:
        return False, f"ambiguous_anchor ({count} occurrences)"

    # Perform insertion
    new_content = file_content.replace(anchor, content + "\n" + anchor, 1)
    path.write_text(new_content)
    return True, None


def apply_commands(commands: list, project_root: Path, project_ai_dir: Path) -> tuple:
    """Apply write/append/edit commands with safety checks."""
    applied = []
    files_touched = []

    # Check file count limit
    if len(commands) > MAX_FILES_PER_RUN:
        record_attempt(project_ai_dir, f"Too many files: {len(commands)}", [], "BLOCKED")
        raise ValueError(f"Exceeds MAX_FILES_PER_RUN ({MAX_FILES_PER_RUN}): {len(commands)} commands")

    # Check for unsafe overwrites
    unsafe, safe_commands = check_unsafe_overwrite(project_root, commands)

    if unsafe:
        reasons = "; ".join([f"{u['path']}: {u['reason']}" for u in unsafe])
        record_attempt(project_ai_dir, f"Unsafe overwrite blocked: {reasons}", files_touched, "BLOCKED")
        raise ValueError(f"BLOCKED - Unsafe overwrite: {reasons}")

    for cmd in safe_commands:
        cmd_type = cmd.get("type")
        path_str = cmd.get("path", "")
        content = cmd.get("content", "")

        if not path_str:
            continue

        path = project_root / path_str
        files_touched.append(path_str)

        # Handle edit commands (NEW - strict validation)
        if cmd_type == "replace_text":
            old_text = cmd.get("old", "")
            new_text = cmd.get("new", "")
            if not old_text:
                error_msg = f"replace_text missing 'old' parameter for {path_str}"
                record_attempt(project_ai_dir, error_msg, files_touched, "BLOCKED")
                raise ValueError(f"BLOCKED - {error_msg}")

            success, error = apply_replace_text(path, old_text, new_text)
            if success:
                applied.append(str(path.relative_to(project_root)))
            else:
                error_msg = f"replace_text failed for {path_str}: {error}"
                record_attempt(project_ai_dir, error_msg, files_touched, "BLOCKED")
                raise ValueError(f"BLOCKED - {error_msg}")

        elif cmd_type == "insert_after":
            # Support both 'anchor' (new) and 'marker' (old) for compatibility
            anchor = cmd.get("anchor", cmd.get("marker", ""))
            if not anchor:
                error_msg = f"insert_after missing 'anchor' for {path_str}"
                record_attempt(project_ai_dir, error_msg, files_touched, "BLOCKED")
                raise ValueError(f"BLOCKED - {error_msg}")

            success, error = apply_insert_after(path, anchor, content)
            if success:
                applied.append(str(path.relative_to(project_root)))
            else:
                error_msg = f"insert_after failed for {path_str}: {error}"
                record_attempt(project_ai_dir, error_msg, files_touched, "BLOCKED")
                raise ValueError(f"BLOCKED - {error_msg}")

        elif cmd_type == "insert_before":
            # Support both 'anchor' (new) and 'marker' (old) for compatibility
            anchor = cmd.get("anchor", cmd.get("marker", ""))
            if not anchor:
                error_msg = f"insert_before missing 'anchor' for {path_str}"
                record_attempt(project_ai_dir, error_msg, files_touched, "BLOCKED")
                raise ValueError(f"BLOCKED - {error_msg}")

            success, error = apply_insert_before(path, anchor, content)
            if success:
                applied.append(str(path.relative_to(project_root)))
            else:
                error_msg = f"insert_before failed for {path_str}: {error}"
                record_attempt(project_ai_dir, error_msg, files_touched, "BLOCKED")
                raise ValueError(f"BLOCKED - {error_msg}")

        elif cmd_type == "replace_block":
            start_marker = cmd.get("start_marker", "")
            end_marker = cmd.get("end_marker", "")
            if path.exists() and start_marker and end_marker:
                try:
                    file_content = path.read_text()
                    start_idx = file_content.find(start_marker)
                    end_idx = file_content.find(end_marker) + len(end_marker)
                    if start_idx >= 0 and end_idx > start_idx:
                        new_content = file_content[:start_idx] + content + file_content[end_idx:]
                        path.write_text(new_content)
                        applied.append(str(path.relative_to(project_root)))
                    else:
                        print(f"WARNING: Block markers not found in {path_str}", file=sys.stderr)
                except Exception as e:
                    print(f"WARNING: replace_block failed: {e}", file=sys.stderr)

        elif cmd_type == "write_file" or cmd_type == "write_file_safe":
            # Original write_file logic
            if not is_safe_path(path, project_root):
                print(f"WARNING: Skipping unsafe path: {path_str}", file=sys.stderr)
                record_attempt(project_ai_dir, f"Unsafe path: {path_str}", files_touched, "PARTIAL")
                continue

            if not check_file_size(path, MAX_FILE_LINES):
                print(f"WARNING: File too large: {path_str}", file=sys.stderr)
                record_attempt(project_ai_dir, f"File too large: {path_str}", files_touched, "PARTIAL")
                raise ValueError(f"File exceeds MAX_FILE_LINES: {path_str}")

            if DRY_RUN:
                print(f"[DRY-RUN] Would write: {path_str}", file=sys.stderr)
                applied.append(str(path.relative_to(project_root)))
                continue

            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
            applied.append(str(path.relative_to(project_root)))

        elif cmd_type == "append_file":
            if not is_safe_path(path, project_root):
                print(f"WARNING: Skipping unsafe path: {path_str}", file=sys.stderr)
                record_attempt(project_ai_dir, f"Unsafe path: {path_str}", files_touched, "PARTIAL")
                continue

            if DRY_RUN:
                print(f"[DRY-RUN] Would append: {path_str}", file=sys.stderr)
                applied.append(str(path.relative_to(project_root)))
                continue

            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "a") as f:
                f.write(content)
            applied.append(str(path.relative_to(project_root)))

    return applied, len(safe_commands)


def generate_patch(project_root: Path, project_ai_dir: Path):
    """Generate git diff patch."""
    baseline = project_ai_dir / ".baseline.diff"
    if baseline.exists():
        baseline.read_text()

    try:
        result = subprocess.run(
            ["git", "diff", "HEAD"],
            cwd=project_root,
            capture_output=True,
            text=True,
            check=False
        )
        patch = result.stdout or result.stderr

        if baseline.exists():
            old = baseline.read_text()
            if patch == old:
                patch = "No changes from baseline"

        (project_ai_dir / "PATCH.diff").write_text(patch or "No changes")
    except Exception as e:
        (project_ai_dir / "PATCH.diff").write_text(f"Error generating patch: {e}")


def write_result(project_ai_dir: Path, summary: str, files_changed: list,
                 tests: list, risks: list, status: str,
                 unsafe_write_blocked: bool = False,
                 deletion_count: int = 0,
                 addition_count: int = 0,
                 allowed_files: list = None,
                 applied_files: list = None,
                 unexpected_files: list = None,
                 target_file_modified: bool = None):
    """Write RESULT.md with safety info."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    unsafe_status = "BLOCKED" if unsafe_write_blocked else status

    changed_list = "\n".join(f"- {f}" for f in files_changed) if files_changed else "- No files changed"
    tests_list = "\n".join(f"- {t}" for t in tests) if tests else "- No tests suggested"
    risks_list = "\n".join(f"- {r}" for r in risks) if risks else "- No risks identified"

    diff_safe = deletion_count <= addition_count * 2 and deletion_count <= 20
    
    # Constraint validation section
    constraint_section = ""
    if allowed_files is not None:
        allowed_list = "\n".join(f"  - {f}" for f in allowed_files)
        constraint_section = f"""

## Constraint Validation

- **allowed_files:**
{allowed_list}
- **applied_files:** {applied_files if applied_files else []}
- **unexpected_files:** {unexpected_files if unexpected_files else []}
- **target_file_modified:** {target_file_modified if target_file_modified is not None else "N/A"}
"""

    content = f"""# Implementation Result

**Date:** {now}
**Status:** {unsafe_status}
**implementation_executor:** local-coder
**backend:** ollama
**model:** {os.getenv('LOCAL_CODER_MODEL', 'qwen2.5-coder:32b')}

## Safety Checks

- **unsafe_write_blocked:** {unsafe_write_blocked}
- **deletion_count:** {deletion_count}
- **addition_count:** {addition_count}
- **diff_safe:** {diff_safe}
{constraint_section}
## Summary

{summary}

## Files Changed

{changed_list}

## Tests Suggested

{tests_list}

## Tests Run

- Manual verification required

## Risks

{risks_list}
"""
    (project_ai_dir / "RESULT.md").write_text(content)


def update_handover(project_ai_dir: Path, summary: str):
    """Update HANDOFF.md."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    handoff_path = project_ai_dir / "HANDOFF.md"

    existing = ""
    if handoff_path.exists():
        existing = handoff_path.read_text()

    new_entry = f"""## {now} - local-coder Session

{summary}

- implementation_executor: local-coder
- backend: ollama

"""

    handoff_path.write_text(new_entry + existing)


def main():
    parser = argparse.ArgumentParser(description="local-coder worker")
    parser.add_argument("--task-file", required=True)
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--model", default="qwen2.5-coder:32b")
    parser.add_argument("--endpoint", default="http://127.0.0.1:11434")
    args = parser.parse_args()

    project_root = Path(args.project_root)
    project_ai_dir = project_root / ".project-ai"

    if not project_ai_dir.exists():
        print(f"ERROR: .project-ai directory not found at {project_ai_dir}", file=sys.stderr)
        sys.exit(1)

    # Initialize database
    db = get_db(project_root)
    attempt_id: int = 0

    try:
        # Read task for loop detection
        task_content = (project_ai_dir / "TASK.md").read_text()
        task_hash = hashlib.md5(task_content.encode()).hexdigest()[:8]

        # Check loop detection BEFORE running
        if check_loop_detection(project_ai_dir, task_hash):
            record_violation(project_ai_dir, f"Loop detected: task_hash {task_hash} attempted 3+ times")
            db.add_violation(None, f"Loop detected: task_hash {task_hash} attempted 3+ times")
            print(f"ERROR: Loop detected - same task attempted 3+ times. See ATTEMPT_HISTORY.md and WORKFLOW_VIOLATIONS.md", file=sys.stderr)
            sys.exit(1)

        # Create task and start attempt in database
        task_id = db.create_task(summary=task_content[:200], full_content=task_content)
        attempt_id = db.start_attempt(task_id, executor="local-coder", backend="ollama", model=args.model)

        # Parse constraints for edit-mode prompt
        constraints = extract_task_constraints(task_content)
        allowed_files = constraints.get("allowed_files", [])
        forbidden_new = constraints.get("forbidden_new_files", False)

        context = read_context_files(project_ai_dir)
        prompt = build_prompt(context, allowed_files=allowed_files if allowed_files else None, forbidden_new=forbidden_new)

        try:
            raw_output = call_ollama(prompt, args.model, args.endpoint)
        except requests.RequestException as e:
            (project_ai_dir / "RESULT.md").write_text(
                f"# Implementation Result\n\n**Status:** BLOCKED\n\n**Error:** Failed to call Ollama: {e}"
            )
            record_attempt(project_ai_dir, f"Ollama error: {e}", [], "BLOCKED")
            db.complete_attempt(attempt_id, "blocked", f"Ollama error: {e}")
            sys.exit(1)

        (project_ai_dir / "local-coder-raw-output.txt").write_text(raw_output)

        try:
            response = parse_response(raw_output)
        except (ValueError, json.JSONDecodeError) as e:
            (project_ai_dir / "RESULT.md").write_text(
                f"# Implementation Result\n\n**Status:** FAILED\n\n**Error:** Failed to parse model output as JSON: {e}\n\n"
                f"Raw output saved to local-coder-raw-output.txt"
            )
            record_attempt(project_ai_dir, f"Parse error: {e}", [], "FAILED")
            db.complete_attempt(attempt_id, "failed", f"Parse error: {e}")
            sys.exit(1)

        commands = response.get("commands", [])
        
        # Extract and validate target file constraints
        constraints = extract_task_constraints(task_content)
        allowed_files = constraints.get("allowed_files", [])
        forbidden_new = constraints.get("forbidden_new_files", False)
        
        # Validate commands against constraints
        violations, safe_commands = validate_target_files(project_root, commands, allowed_files, forbidden_new)
        
        if violations:
            # Build violation message
            violation_msgs = []
            for v in violations:
                violation_msgs.append(f"- {v['path']}: {v['reason']}")
            
            error_msg = "Target file constraint violations:\n" + "\n".join(violation_msgs)
            
            write_result(
                project_ai_dir,
                f"Task constraint violation: {len(violations)} command(s) blocked",
                [],
                [],
                violation_msgs,
                "BLOCKED",
                unsafe_write_blocked=False,
                deletion_count=0,
                addition_count=0
            )
            record_attempt(project_ai_dir, f"Constraint violation: {len(violations)} blocked", [], "BLOCKED")
            db.add_violation(attempt_id, f"Target file constraints: {violation_msgs}")
            db.complete_attempt(attempt_id, "blocked", f"Task constraint violation")
            print(f"ERROR: Task constraint violations detected - see RESULT.md", file=sys.stderr)
            sys.exit(1)
        
        # Apply validated commands
        try:
            files_changed, command_count = apply_commands(safe_commands, project_root, project_ai_dir)
        except ValueError as e:
            # Guardrail violation - unsafe overwrite blocked
            error_msg = str(e)
            is_unsafe_write = "Unsafe overwrite" in error_msg or "BLOCKED" in error_msg

            write_result(
                project_ai_dir,
                f"Guardrail violation: {error_msg}",
                [],
                [],
                [error_msg],
                "BLOCKED",
                unsafe_write_blocked=is_unsafe_write,
                deletion_count=0,
                addition_count=0
            )
            record_attempt(project_ai_dir, f"Guardrail: {e}", [], "BLOCKED")
            db.complete_attempt(attempt_id, "blocked", f"Guardrail violation: {e}")
            sys.exit(1)

        # Record file changes in database
        for file_path in files_changed:
            db.add_file_change(attempt_id, file_path, "write")

        generate_patch(project_root, project_ai_dir)

        # Post-validation: check applied files match constraints
        applied_validation = validate_applied_files(project_root, allowed_files if allowed_files else None)
        
        # Add unexpected files to risks
        if applied_validation["unexpected_files"]:
            risks.extend([
                f"Unexpected file modified: {f}" 
                for f in applied_validation["unexpected_files"]
            ])
            if not applied_validation["target_file_modified"]:
                status = "BLOCKED"
        
        # Validate diff for safety
        diff_validation = validate_diff(project_root)
        deletion_count = diff_validation["deletions"]
        addition_count = diff_validation["additions"]

        summary = response.get("summary", "No summary provided")
        tests = response.get("tests", [])
        risks = response.get("risks", [])
        
        # Track constraint validation in summary
        if allowed_files:
            summary += f"\n\n**Constraints:** allowed_files={allowed_files}, forbidden_new_files={forbidden_new}"
            summary += f"\n**Applied files:** {applied_validation['applied_files']}"
            if applied_validation["unexpected_files"]:
                summary += f"\n**Unexpected files:** {applied_validation['unexpected_files']}"

        status = "PASS"
        if not files_changed:
            status = "PARTIAL"
        if risks:
            status = "PARTIAL"
        if not diff_validation["is_safe"]:
            status = "BLOCKED"
            risks.extend(diff_validation["reasons"])

        write_result(
            project_ai_dir, summary, files_changed, tests, risks, status,
            unsafe_write_blocked=False,
            deletion_count=deletion_count,
            addition_count=addition_count,
            allowed_files=allowed_files if allowed_files else None,
            applied_files=applied_validation.get("applied_files") if allowed_files else None,
            unexpected_files=applied_validation.get("unexpected_files") if allowed_files else None,
            target_file_modified=applied_validation.get("target_file_modified") if allowed_files else None
        )
        update_handover(project_ai_dir, summary)

        # Record handoff in database
        risks_str = "; ".join(risks) if risks else ""
        db.add_handoff(attempt_id, summary, risks_str)

        # Record patch in database
        patch_file = project_ai_dir / "PATCH.diff"
        if patch_file.exists():
            patch_content = patch_file.read_text()
            db.add_patch(attempt_id, patch_content)

        # Complete the attempt in database
        db.complete_attempt(attempt_id, status.lower(), summary)

        # Record successful attempt (legacy)
        record_attempt(project_ai_dir, summary, files_changed, status)

        print(f"local-coder complete: {status}", file=sys.stderr)
        print(f"Files changed: {len(files_changed)}", file=sys.stderr)
    finally:
        db.close()


if __name__ == "__main__":
    main()
