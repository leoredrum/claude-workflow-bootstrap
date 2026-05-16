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


def build_prompt(context: dict) -> str:
    """Build the prompt for Ollama."""
    task = context.get("TASK.md", "")

    return f"""You are a local AI coding assistant. Your task is to implement the requested changes based on the task description.

## Task
{task}

IMPORTANT: Respond ONLY with a valid JSON object in this exact format:
{{
  "summary": "Brief description of what was done",
  "commands": [
    {{"type": "write_file", "path": "relative/path/to/file", "content": "file content"}}
  ],
  "tests": ["test suggestion 1"],
  "risks": ["potential risk 1"]
}}
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


def apply_commands(commands: list, project_root: Path, project_ai_dir: Path) -> tuple:
    """Apply write/append commands with limits."""
    applied = []
    files_touched = []

    # Check file count limit
    if len(commands) > MAX_FILES_PER_RUN:
        record_attempt(project_ai_dir, f"Too many files: {len(commands)}", [], "BLOCKED")
        raise ValueError(f"Exceeds MAX_FILES_PER_RUN ({MAX_FILES_PER_RUN}): {len(commands)} commands")

    for cmd in commands:
        cmd_type = cmd.get("type")
        path_str = cmd.get("path", "")
        content = cmd.get("content", "")

        if not path_str:
            continue

        path = project_root / path_str
        files_touched.append(path_str)

        if not is_safe_path(path, project_root):
            print(f"WARNING: Skipping unsafe path: {path_str}", file=sys.stderr)
            record_attempt(project_ai_dir, f"Unsafe path: {path_str}", files_touched, "PARTIAL")
            continue

        # Check file size
        if not check_file_size(path, MAX_FILE_LINES):
            print(f"WARNING: File too large (> {MAX_FILE_LINES} lines): {path_str}", file=sys.stderr)
            record_attempt(project_ai_dir, f"File too large: {path_str}", files_touched, "PARTIAL")
            raise ValueError(f"File exceeds MAX_FILE_LINES: {path_str}")

        if DRY_RUN:
            print(f"[DRY-RUN] Would {cmd_type}: {path_str}", file=sys.stderr)
            applied.append(str(path.relative_to(project_root)))
            continue

        path.parent.mkdir(parents=True, exist_ok=True)

        if cmd_type == "write_file":
            path.write_text(content)
            applied.append(str(path.relative_to(project_root)))
        elif cmd_type == "append_file":
            with open(path, "a") as f:
                f.write(content)
            applied.append(str(path.relative_to(project_root)))

    return applied, len(commands)


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
                 tests: list, risks: list, status: str):
    """Write RESULT.md."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    changed_list = "\n".join(f"- {f}" for f in files_changed) if files_changed else "- No files changed"
    tests_list = "\n".join(f"- {t}" for t in tests) if tests else "- No tests suggested"
    risks_list = "\n".join(f"- {r}" for r in risks) if risks else "- No risks identified"

    content = f"""# Implementation Result

**Date:** {now}
**Status:** {status}
**implementation_executor:** local-coder
**backend:** ollama
**model:** {os.getenv('LOCAL_CODER_MODEL', 'qwen2.5-coder:32b')}

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

    # Read task for loop detection
    task_content = (project_ai_dir / "TASK.md").read_text()
    task_hash = hashlib.md5(task_content.encode()).hexdigest()[:8]

    # Check loop detection BEFORE running
    if check_loop_detection(project_ai_dir, task_hash):
        record_violation(project_ai_dir, f"Loop detected: task_hash {task_hash} attempted 3+ times")
        print(f"ERROR: Loop detected - same task attempted 3+ times. See ATTEMPT_HISTORY.md and WORKFLOW_VIOLATIONS.md", file=sys.stderr)
        sys.exit(1)

    context = read_context_files(project_ai_dir)
    prompt = build_prompt(context)

    try:
        raw_output = call_ollama(prompt, args.model, args.endpoint)
    except requests.RequestException as e:
        (project_ai_dir / "RESULT.md").write_text(
            f"# Implementation Result\n\n**Status:** BLOCKED\n\n**Error:** Failed to call Ollama: {e}"
        )
        record_attempt(project_ai_dir, f"Ollama error: {e}", [], "BLOCKED")
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
        sys.exit(1)

    commands = response.get("commands", [])
    try:
        files_changed, command_count = apply_commands(commands, project_root, project_ai_dir)
    except ValueError as e:
        # Guardrail violation
        (project_ai_dir / "RESULT.md").write_text(
            f"# Implementation Result\n\n**Status:** BLOCKED\n\n**Error:** Guardrail violation: {e}"
        )
        record_attempt(project_ai_dir, f"Guardrail: {e}", [], "BLOCKED")
        sys.exit(1)

    generate_patch(project_root, project_ai_dir)

    summary = response.get("summary", "No summary provided")
    tests = response.get("tests", [])
    risks = response.get("risks", [])

    status = "PASS"
    if not files_changed:
        status = "PARTIAL"
    if risks:
        status = "PARTIAL"

    write_result(project_ai_dir, summary, files_changed, tests, risks, status)
    update_handover(project_ai_dir, summary)

    # Record successful attempt
    record_attempt(project_ai_dir, summary, files_changed, status)

    print(f"local-coder complete: {status}", file=sys.stderr)
    print(f"Files changed: {len(files_changed)}", file=sys.stderr)


if __name__ == "__main__":
    main()
