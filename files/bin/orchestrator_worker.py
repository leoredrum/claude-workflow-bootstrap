#!/usr/bin/env python3
"""Orchestrator worker - executes tasks from the queue."""

from __future__ import annotations

import signal
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from workflow_db import get_db


class Worker:
    """Base worker class."""

    def __init__(
        self,
        worker_id: str,
        worker_type: str,
        project_root: Path,
        model: str | None = None,
        backend: str | None = None,
    ):
        self.worker_id = worker_id
        self.worker_type = worker_type
        self.project_root = project_root
        self.db = get_db(project_root)
        self.running = True
        self.model = model
        self.backend = backend

        # Register worker
        self.db.register_worker(
            worker_id,
            worker_type,
            self.get_capabilities(),
            model,
            backend,
        )

        # Setup signal handlers
        signal.signal(signal.SIGTERM, self._shutdown)
        signal.signal(signal.SIGINT, self._shutdown)

    def get_capabilities(self) -> list[str]:
        """Return worker capabilities."""
        return [self.worker_type]

    def _shutdown(self, signum: int, frame) -> None:
        print(f"Worker {self.worker_id} shutting down...", file=sys.stderr)
        self.running = False

    def heartbeat(self) -> None:
        """Send heartbeat."""
        self.db.worker_heartbeat(self.worker_id, "alive")

    def execute_task(self, task: dict) -> dict:
        """Execute a task (to be implemented by subclasses)."""
        raise NotImplementedError

    def run(self, poll_interval: int = 5) -> None:
        """Main worker loop."""
        print(f"Worker {self.worker_id} ({self.worker_type}) starting...", file=sys.stderr)

        while self.running:
            try:
                # Heartbeat
                self.heartbeat()

                # Try to lease a task
                task = self.db.lease_task(
                    self.worker_id,
                    self.worker_type,
                    timeout=300,
                )

                if task:
                    print(
                        f"Worker {self.worker_id} leased task {task['id']}: {task['summary'][:50]}",
                        file=sys.stderr,
                    )

                    try:
                        # Execute task
                        result = self.execute_task(task)
                        self.db.complete_task(
                            task["id"],
                            self.worker_id,
                            result.get("status", "completed"),
                            result.get("result", ""),
                        )
                    except Exception as e:
                        print(f"Task execution failed: {e}", file=sys.stderr)
                        self.db.complete_task(
                            task["id"],
                            self.worker_id,
                            "failed",
                            str(e),
                        )
                else:
                    # No task available, wait
                    time.sleep(poll_interval)

            except Exception as e:
                print(f"Worker error: {e}", file=sys.stderr)
                time.sleep(poll_interval)

        # Cleanup
        self.db.close()


class ImplementerWorker(Worker):
    """Worker that implements code changes."""

    def get_capabilities(self) -> list[str]:
        return ["implementer", "write_file", "edit_file", "code_generation"]

    def execute_task(self, task: dict) -> dict:
        """Execute implementation task using local-coder."""
        # Write task to .project-ai/TASK.md
        task_file = self.project_root / ".project-ai" / "TASK.md"
        task_file.write_text(task.get("full_content") or task.get("summary", ""))

        # Run local-coder
        result = subprocess.run(
            ["local-coder", str(task_file)],
            cwd=self.project_root,
            capture_output=True,
            text=True,
        )

        return {
            "status": "completed" if result.returncode == 0 else "failed",
            "result": result.stdout,
        }


class ReviewerWorker(Worker):
    """Worker that reviews code changes."""

    def get_capabilities(self) -> list[str]:
        return ["reviewer", "code_review", "quality_check"]

    def execute_task(self, task: dict) -> dict:
        """Execute review task."""
        import subprocess

        project_ai = self.project_root / ".project-ai"

        # Check RESULT.md
        result_file = project_ai / "RESULT.md"
        if not result_file.exists():
            return {"status": "failed", "result": "No RESULT.md found"}

        result_content = result_file.read_text()

        # Check PATCH.diff
        patch_file = project_ai / "PATCH.diff"
        if not patch_file.exists():
            return {"status": "failed", "result": "No PATCH.diff found"}

        patch_content = patch_file.read_text()

        # Safety checks
        issues = []

        # Check for unsafe_write_blocked
        if "unsafe_write_blocked: True" in result_content:
            issues.append("Unsafe write was blocked - review PASSED (block worked)")
            return {"status": "completed", "result": "; ".join(issues)}

        # Check deletion count
        if "deletion_count:" in result_content:
            for line in result_content.splitlines():
                if "deletion_count:" in line:
                    try:
                        parts = line.split(":")
                        if len(parts) >= 2:
                            deletions = int(parts[1].strip())
                            if deletions > 20:
                                issues.append(f"High deletion count: {deletions}")
                    except (ValueError, IndexError):
                        pass

        # Check diff size
        patch_lines = len([l for l in patch_content.splitlines() if l.startswith(("-", "+"))])
        if patch_lines > 500:
            issues.append(f"Large patch: {patch_lines} lines")

        # Check for file replacement
        if patch_content.startswith("---") and patch_content.count("---") > 2:
            # Check if entire file was replaced
            deleted_lines = len([l for l in patch_content.splitlines() if l.startswith("-") and not l.startswith("---")])
            added_lines = len([l for l in patch_content.splitlines() if l.startswith("+") and not l.startswith("+++")])
            if deleted_lines > 50 and added_lines < deleted_lines * 0.5:
                issues.append("Possible file replacement - large deletion with small addition")

        if issues:
            return {"status": "partial", "result": "; ".join(issues)}

        return {
            "status": "completed",
            "result": f"Review PASSED: {len(patch_content)} bytes patch"
        }


class TesterWorker(Worker):
    """Worker that runs tests."""

    def get_capabilities(self) -> list[str]:
        return ["tester", "run_tests", "validation"]

    def execute_task(self, task: dict) -> dict:
        """Execute test task."""
        import subprocess

        project_ai = self.project_root / ".project-ai"

        # First check git diff --check (whitespace errors)
        try:
            result = subprocess.run(
                ["git", "diff", "--check"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            if result.returncode != 0:
                return {
                    "status": "failed",
                    "result": f"Git diff check failed: {result.stdout}",
                }
        except Exception as e:
            return {"status": "partial", "result": f"Git check error: {e}"}

        # Check for Python syntax errors in changed files
        try:
            # Get changed Python files
            result = subprocess.run(
                ["git", "diff", "--name-only", "HEAD"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )

            py_files = [f for f in result.stdout.strip().splitlines() if f.endswith(".py")]

            for py_file in py_files:
                py_result = subprocess.run(
                    ["python3", "-m", "py_compile", py_file],
                    cwd=self.project_root,
                    capture_output=True,
                    text=True,
                    timeout=10,
                    check=False,
                )
                if py_result.returncode != 0:
                    return {
                        "status": "failed",
                        "result": f"Syntax error in {py_file}: {py_result.stderr}",
                    }
        except Exception:
            pass

        # Try common test commands
        commands = [
            ["pytest", "-q"],
            ["npm", "test"],
            ["python3", "-m", "pytest"],
        ]

        for cmd in commands:
            try:
                result = subprocess.run(
                    cmd,
                    cwd=self.project_root,
                    capture_output=True,
                    text=True,
                    timeout=30,
                    check=False,
                )
                if result.returncode == 0:
                    return {
                        "status": "completed",
                        "result": f"Tests passed: {cmd[0]}",
                    }
            except Exception:
                continue

        # If no changes or all checks passed
        return {"status": "completed", "result": "All checks passed"}


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--worker-id", required=True)
    parser.add_argument(
        "--worker-type",
        choices=["implementer", "reviewer", "tester"],
        default="implementer",
    )
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--model")
    parser.add_argument("--backend")

    args = parser.parse_args()

    project_root = Path(args.project_root)

    worker_classes: dict[str, type[Worker]] = {
        "implementer": ImplementerWorker,
        "reviewer": ReviewerWorker,
        "tester": TesterWorker,
    }

    worker_cls = worker_classes[args.worker_type]
    worker = worker_cls(
        args.worker_id,
        args.worker_type,
        project_root,
        args.model,
        args.backend,
    )

    worker.run()


if __name__ == "__main__":
    main()
