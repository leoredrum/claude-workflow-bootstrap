#!/usr/bin/env python3
"""Workflow query CLI."""

from __future__ import annotations

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from workflow_db import get_db


def print_table(headers: list, rows: list):
    """Print a simple table."""
    if not rows:
        print("No results")
        return

    # Calculate widths
    widths = [len(h) for h in headers]
    for row in rows:
        for i, val in enumerate(row):
            widths[i] = max(widths[i], len(str(val)[:30]))

    # Print header
    header = " | ".join(h.ljust(w) for h, w in zip(headers, widths))
    print(header)
    print("-" * len(header))

    # Print rows
    for row in rows:
        print(" | ".join(str(v)[:30].ljust(w) for v, w in zip(row, widths)))


def main():
    if len(sys.argv) < 2:
        print("Usage: workflow_query.py <command> [args]")
        sys.exit(1)

    # Find project root
    cwd = Path.cwd()
    project_root = None
    while cwd != cwd.parent:
        if (cwd / ".project-ai" / "workflow_state.db").exists():
            project_root = cwd
            break
        cwd = cwd.parent
    else:
        # Try current directory
        if (Path.cwd() / ".project-ai" / "workflow_state.db").exists():
            project_root = Path.cwd()
        else:
            print("Error: workflow_state.db not found in .project-ai/")
            sys.exit(1)

    db = get_db(project_root)
    cmd = sys.argv[1]

    try:
        if cmd == "recent-failures":
            limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
            results = db.get_recent_failures(limit)
            print_table(["ID", "Task", "Status", "Completed"],
                       [[r["id"], r["summary"][:30], r["status"], r["completed_at"][:19]] for r in results])

        elif cmd == "recent-files":
            limit = int(sys.argv[2]) if len(sys.argv) > 2 else 20
            results = db.get_recent_files(limit)
            print_table(["Path", "Action", "Count", "Last Changed"],
                       [[r["path"], r["action"], r["change_count"], r["last_changed"][:19]] for r in results])

        elif cmd == "high-failure-files":
            min_fail = int(sys.argv[2]) if len(sys.argv) > 2 else 3
            results = db.get_high_failure_files(min_fail)
            print_table(["Path", "Failure Count"],
                       [[r["path"], r["failure_count"]] for r in results])

        elif cmd == "session-restore":
            session_id = sys.argv[2] if len(sys.argv) > 2 else None
            result = db.get_session_restore(session_id)
            if result:
                print(json.dumps(result, indent=2))
            else:
                print("No session data found")

        elif cmd == "task-status":
            cur = db.conn.execute("""
                SELECT t.summary, a.status, COUNT(a.id) as attempts
                FROM tasks t
                LEFT JOIN attempts a ON t.id = a.task_id
                GROUP BY t.id
                ORDER BY MAX(a.completed_at) DESC
            """)
            print_table(["Task", "Status", "Attempts"],
                       [[r["summary"][:30], r["status"] or "pending", r["attempts"]] for r in cur.fetchall()])

        elif cmd == "violations":
            cur = db.conn.execute("""
                SELECT reason, status, detected_at
                FROM workflow_violations
                WHERE status = 'unresolved'
                ORDER BY detected_at DESC
            """)
            print_table(["Reason", "Status", "Detected"],
                       [[r["reason"][:40], r["status"], r["detected_at"][:19]] for r in cur.fetchall()])

        elif cmd == "patch-lineage":
            patch_id = int(sys.argv[2])
            lineage = db.get_patch_lineage(patch_id)
            for i, patch in enumerate(lineage):
                print(f"Patch {i}: ID={patch['id']} Created={patch['created_at']}")
                print(f"  Task: {patch['summary'][:50]}")

        elif cmd == "rollback-suggest":
            attempt_id = int(sys.argv[2])
            result = db.suggest_rollback(attempt_id)
            print(json.dumps(result, indent=2))

        elif cmd == "stats":
            cur = db.conn.execute("""
                SELECT
                    (SELECT COUNT(*) FROM tasks) as tasks,
                    (SELECT COUNT(*) FROM attempts) as attempts,
                    (SELECT COUNT(*) FROM files_changed) as files,
                    (SELECT COUNT(*) FROM workflow_violations) as violations,
                    (SELECT COUNT(*) FROM patches) as patches
            """)
            stats = cur.fetchone()
            print(f"Tasks: {stats[0]}")
            print(f"Attempts: {stats[1]}")
            print(f"Files changed: {stats[2]}")
            print(f"Violations: {stats[3]}")
            print(f"Patches: {stats[4]}")

        else:
            print(f"Unknown command: {cmd}")
            sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
