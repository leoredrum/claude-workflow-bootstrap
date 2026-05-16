#!/usr/bin/env python3
"""Workflow State Database - SQLite backend for claude-plan workflow."""

from __future__ import annotations

import sqlite3
import hashlib
import json
import time
from pathlib import Path
from typing import Optional, List, Dict, Any
import sys


SCHEMA_VERSION = 2


class WorkflowDB:
    """SQLite-based workflow state database."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None
        self._connect()
        self._ensure_schema()

    def _connect(self):
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.execute("PRAGMA journal_mode = WAL")

    def close(self):
        if self._conn:
            self._conn.close()

    @property
    def conn(self) -> sqlite3.Connection:
        """Get the database connection, ensuring it exists."""
        if self._conn is None:
            raise RuntimeError("Database connection not initialized")
        return self._conn

    def _ensure_schema(self):
        """Create or migrate schema."""
        cur = self.conn.cursor()

        # Schema version table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY,
                applied_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        current_version = cur.execute("SELECT MAX(version) FROM schema_version").fetchone()[0] or 0

        if current_version < SCHEMA_VERSION:
            self._run_migrations(current_version)
            cur.execute(f"INSERT INTO schema_version (version) VALUES ({SCHEMA_VERSION})")
            self.conn.commit()

    def _run_migrations(self, from_version: int):
        """Run schema migrations."""
        cur = self.conn.cursor()

        if from_version < 1:
            # Migration 1: Initial schema
            cur.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_hash TEXT UNIQUE NOT NULL,
                    summary TEXT NOT NULL,
                    full_content TEXT,
                    status TEXT DEFAULT 'pending',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER NOT NULL,
                    attempt_number INTEGER DEFAULT 1,
                    executor TEXT NOT NULL,
                    backend TEXT,
                    model TEXT,
                    status TEXT DEFAULT 'in_progress',
                    started_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    completed_at TEXT,
                    result_summary TEXT,
                    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS files_changed (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    attempt_id INTEGER NOT NULL,
                    path TEXT NOT NULL,
                    action TEXT NOT NULL,
                    lines_added INTEGER DEFAULT 0,
                    lines_removed INTEGER DEFAULT 0,
                    file_hash TEXT,
                    FOREIGN KEY (attempt_id) REFERENCES attempts(id) ON DELETE CASCADE
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS workflow_violations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    attempt_id INTEGER,
                    reason TEXT NOT NULL,
                    status TEXT DEFAULT 'unresolved',
                    detected_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    resolved_at TEXT,
                    FOREIGN KEY (attempt_id) REFERENCES attempts(id) ON DELETE SET NULL
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS handoffs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    attempt_id INTEGER NOT NULL,
                    session_summary TEXT NOT NULL,
                    next_steps TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (attempt_id) REFERENCES attempts(id) ON DELETE CASCADE
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS memory_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT NOT NULL,
                    content TEXT NOT NULL,
                    tags TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    archived_at TEXT,
                    is_active INTEGER DEFAULT 1
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS tests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    attempt_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    command TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    output TEXT,
                    ran_at TEXT,
                    FOREIGN KEY (attempt_id) REFERENCES attempts(id) ON DELETE CASCADE
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS patches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    attempt_id INTEGER NOT NULL,
                    patch_content TEXT NOT NULL,
                    parent_patch_id INTEGER,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    applied INTEGER DEFAULT 0,
                    FOREIGN KEY (attempt_id) REFERENCES attempts(id) ON DELETE CASCADE,
                    FOREIGN KEY (parent_patch_id) REFERENCES patches(id) ON DELETE SET NULL
                )
            """)

            # Indexes
            cur.execute("CREATE INDEX IF NOT EXISTS idx_tasks_hash ON tasks(task_hash)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_attempts_task ON attempts(task_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_attempts_status ON attempts(status)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_files_attempt ON files_changed(attempt_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_files_path ON files_changed(path)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_violations_status ON workflow_violations(status)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_tests_status ON tests(status)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_tests_attempt ON tests(attempt_id)")

        if from_version < 2:
            # Migration 2: Orchestrator tables
            cur.execute("""
                CREATE TABLE IF NOT EXISTS worker_registry (
                    worker_id TEXT PRIMARY KEY,
                    worker_type TEXT NOT NULL,
                    capabilities TEXT NOT NULL,
                    model TEXT,
                    backend TEXT,
                    status TEXT DEFAULT 'idle',
                    current_task INTEGER,
                    last_heartbeat TEXT DEFAULT CURRENT_TIMESTAMP,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (current_task) REFERENCES task_queue(id)
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS task_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_hash TEXT UNIQUE NOT NULL,
                    summary TEXT NOT NULL,
                    full_content TEXT,
                    priority INTEGER DEFAULT 5,
                    status TEXT DEFAULT 'pending',
                    worker_type TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS task_leases (
                    task_id INTEGER PRIMARY KEY,
                    worker_id TEXT NOT NULL,
                    leased_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    timeout INTEGER DEFAULT 300,
                    FOREIGN KEY (task_id) REFERENCES task_queue(id) ON DELETE CASCADE,
                    FOREIGN KEY (worker_id) REFERENCES worker_registry(worker_id)
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS worker_heartbeats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    worker_id TEXT NOT NULL,
                    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                    status TEXT NOT NULL,
                    FOREIGN KEY (worker_id) REFERENCES worker_registry(worker_id) ON DELETE CASCADE
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS task_dependencies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER NOT NULL,
                    depends_on_task_id INTEGER NOT NULL,
                    FOREIGN KEY (task_id) REFERENCES task_queue(id) ON DELETE CASCADE,
                    FOREIGN KEY (depends_on_task_id) REFERENCES task_queue(id) ON DELETE CASCADE
                )
            """)

            # Indexes for orchestrator
            cur.execute("CREATE INDEX IF NOT EXISTS idx_queue_status ON task_queue(status, priority)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_queue_worker_type ON task_queue(worker_type, status)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_leases_worker ON task_leases(worker_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_heartbeats_worker ON worker_heartbeats(worker_id, timestamp)")

        self.conn.commit()

    def create_task(self, summary: str, full_content: str = "") -> int:
        """Create a new task."""
        task_hash = hashlib.md5(summary.encode()).hexdigest()[:16]
        cur = self.conn.cursor()
        try:
            cur.execute(
                "INSERT INTO tasks (task_hash, summary, full_content) VALUES (?, ?, ?)",
                (task_hash, summary, full_content)
            )
            self.conn.commit()
            rowid = cur.lastrowid
            return rowid if rowid is not None else 0
        except sqlite3.IntegrityError:
            # Task with this hash already exists
            cur = self.conn.execute("SELECT id FROM tasks WHERE task_hash = ?", (task_hash,))
            row = cur.fetchone()
            return row[0] if row else 0

    def start_attempt(self, task_id: int, executor: str,
                      backend: Optional[str] = None, model: Optional[str] = None) -> int:
        """Start a new attempt for a task."""
        cur = self.conn.cursor()

        # Get attempt number
        cur.execute("SELECT COUNT(*) FROM attempts WHERE task_id = ?", (task_id,))
        result = cur.fetchone()
        attempt_number = (result[0] if result else 0) + 1

        cur.execute(
            """INSERT INTO attempts (task_id, attempt_number, executor, backend, model, status)
               VALUES (?, ?, ?, ?, ?, 'in_progress')""",
            (task_id, attempt_number, executor, backend, model)
        )
        self.conn.commit()
        rowid = cur.lastrowid
        return rowid if rowid is not None else 0

    def complete_attempt(self, attempt_id: int, status: str, result_summary: str):
        """Mark an attempt as completed."""
        self.conn.execute(
            """UPDATE attempts SET status = ?, completed_at = CURRENT_TIMESTAMP,
               result_summary = ? WHERE id = ?""",
            (status, result_summary, attempt_id)
        )
        self.conn.commit()

    def add_file_change(self, attempt_id: int, path: str, action: str,
                       lines_added: int = 0, lines_removed: int = 0):
        """Record a file change."""
        file_hash = None
        file_path = Path(path)
        if file_path.exists():
            file_hash = hashlib.md5(file_path.read_bytes()).hexdigest()[:16]

        self.conn.execute(
            """INSERT INTO files_changed (attempt_id, path, action, lines_added, lines_removed, file_hash)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (attempt_id, path, action, lines_added, lines_removed, file_hash)
        )
        self.conn.commit()

    def add_violation(self, attempt_id: Optional[int], reason: str):
        """Record a workflow violation."""
        self.conn.execute(
            "INSERT INTO workflow_violations (attempt_id, reason) VALUES (?, ?)",
            (attempt_id, reason)
        )
        self.conn.commit()

    def add_handoff(self, attempt_id: int, session_summary: str, next_steps: str = ""):
        """Record a handoff entry."""
        self.conn.execute(
            """INSERT INTO handoffs (attempt_id, session_summary, next_steps)
               VALUES (?, ?, ?)""",
            (attempt_id, session_summary, next_steps)
        )
        self.conn.commit()

    def add_memory(self, category: str, content: str, tags: str = "") -> int:
        """Add a memory entry."""
        cur = self.conn.execute(
            "INSERT INTO memory_entries (category, content, tags) VALUES (?, ?, ?)",
            (category, content, tags)
        )
        self.conn.commit()
        rowid = cur.lastrowid
        return rowid if rowid is not None else 0

    def add_test(self, attempt_id: int, name: str, command: str):
        """Add a test record."""
        self.conn.execute(
            "INSERT INTO tests (attempt_id, name, command) VALUES (?, ?, ?)",
            (attempt_id, name, command)
        )
        self.conn.commit()

    def update_test(self, test_id: int, status: str, output: str = ""):
        """Update test result."""
        self.conn.execute(
            "UPDATE tests SET status = ?, output = ?, ran_at = CURRENT_TIMESTAMP WHERE id = ?",
            (status, output, test_id)
        )
        self.conn.commit()

    def add_patch(self, attempt_id: int, patch_content: str, parent_patch_id: Optional[int] = None):
        """Add a patch record."""
        self.conn.execute(
            "INSERT INTO patches (attempt_id, patch_content, parent_patch_id) VALUES (?, ?, ?)",
            (attempt_id, patch_content, parent_patch_id)
        )
        self.conn.commit()

    # Query methods
    def get_recent_failures(self, limit: int = 10) -> List[Dict]:
        """Get recent failed attempts."""
        cur = self.conn.execute("""
            SELECT a.id, a.attempt_number, t.summary, a.status, a.completed_at, a.result_summary
            FROM attempts a
            JOIN tasks t ON a.task_id = t.id
            WHERE a.status IN ('failed', 'partial', 'blocked')
            ORDER BY a.completed_at DESC
            LIMIT ?
        """, (limit,))
        return [dict(row) for row in cur.fetchall()]

    def get_recent_files(self, limit: int = 20) -> List[Dict]:
        """Get recently changed files."""
        cur = self.conn.execute("""
            SELECT f.path, f.action, COUNT(*) as change_count,
                   MAX(a.completed_at) as last_changed
            FROM files_changed f
            JOIN attempts a ON f.attempt_id = a.id
            GROUP BY f.path, f.action
            ORDER BY last_changed DESC
            LIMIT ?
        """, (limit,))
        return [dict(row) for row in cur.fetchall()]

    def get_high_failure_files(self, min_failures: int = 3) -> List[Dict]:
        """Get files that fail frequently."""
        cur = self.conn.execute("""
            SELECT path, COUNT(*) as failure_count
            FROM files_changed f
            JOIN attempts a ON f.attempt_id = a.id
            WHERE a.status IN ('failed', 'partial', 'blocked')
            GROUP BY path
            HAVING failure_count >= ?
            ORDER BY failure_count DESC
        """, (min_failures,))
        return [dict(row) for row in cur.fetchall()]

    def get_consecutive_failures(self, task_hash: str) -> int:
        """Count consecutive failures for a task."""
        cur = self.conn.execute("""
            SELECT COUNT(*)
            FROM attempts a
            JOIN tasks t ON a.task_id = t.id
            WHERE t.task_hash = ? AND a.status IN ('failed', 'partial', 'blocked')
        """, (task_hash,))
        return cur.fetchone()[0]

    def get_session_restore(self, session_id: Optional[str] = None) -> Dict:
        """Get data for session restore."""
        if session_id:
            cur = self.conn.execute("""
                SELECT t.summary, a.result_summary, h.session_summary, h.next_steps
                FROM attempts a
                JOIN tasks t ON a.task_id = t.id
                LEFT JOIN handoffs h ON a.id = h.attempt_id
                WHERE a.id = ?
            """, (session_id,))
        else:
            cur = self.conn.execute("""
                SELECT t.summary, a.result_summary, h.session_summary, h.next_steps
                FROM attempts a
                JOIN tasks t ON a.task_id = t.id
                LEFT JOIN handoffs h ON a.id = h.attempt_id
                ORDER BY a.completed_at DESC
                LIMIT 1
            """)
        row = cur.fetchone()
        return dict(row) if row else {}

    def get_patch_lineage(self, patch_id: int) -> List[Dict]:
        """Get patch lineage (ancestors)."""
        lineage = []
        current_id = patch_id

        while current_id:
            cur = self.conn.execute("""
                SELECT p.id, p.patch_content, p.created_at,
                       a.task_id, t.summary
                FROM patches p
                JOIN attempts a ON p.attempt_id = a.id
                JOIN tasks t ON a.task_id = t.id
                WHERE p.id = ?
            """, (current_id,))
            row = cur.fetchone()
            if not row:
                break

            lineage.append(dict(row))

            # Get parent
            cur = self.conn.execute("SELECT parent_patch_id FROM patches WHERE id = ?", (current_id,))
            parent = cur.fetchone()
            current_id = parent[0] if parent else None

        return lineage

    def suggest_rollback(self, attempt_id: int) -> Dict:
        """Suggest rollback based on patch lineage."""
        cur = self.conn.execute("""
            SELECT p.id, p.patch_content, p.created_at, p.parent_patch_id
            FROM patches p
            WHERE p.attempt_id = ?
        """, (attempt_id,))

        patches = cur.fetchall()
        if not patches:
            return {"can_rollback": False, "reason": "No patches found"}

        # Get the parent patch
        row = patches[0]
        parent_id = row["parent_patch_id"]
        if not parent_id:
            return {"can_rollback": False, "reason": "No parent patch to rollback to"}

        cur = self.conn.execute("SELECT patch_content FROM patches WHERE id = ?", (parent_id,))
        parent_patch = cur.fetchone()

        return {
            "can_rollback": True,
            "rollback_to": parent_id,
            "parent_patch": parent_patch["patch_content"] if parent_patch else None
        }

    # ========== Task Queue Methods ==========

    def enqueue_task(
        self,
        summary: str,
        full_content: str,
        worker_type: str = "implementer",
        priority: int = 5,
    ) -> int:
        """Add a task to the queue."""
        task_hash = hashlib.md5(f"{summary}:{worker_type}".encode()).hexdigest()[:16]
        cur = self.conn.cursor()
        try:
            cur.execute(
                """INSERT INTO task_queue (task_hash, summary, full_content, worker_type, priority)
                   VALUES (?, ?, ?, ?, ?)""",
                (task_hash, summary, full_content, worker_type, priority),
            )
            self.conn.commit()
            return cur.lastrowid
        except sqlite3.IntegrityError:
            cur = self.conn.execute("SELECT id FROM task_queue WHERE task_hash = ?", (task_hash,))
            row = cur.fetchone()
            return row[0] if row else 0

    def lease_task(
        self, worker_id: str, worker_type: str, timeout: int = 300
    ) -> Optional[Dict]:
        """Lease a task for a worker (transaction-safe)."""
        try:
            cur = self.conn.cursor()

            # Find pending task (with satisfied dependencies)
            cur.execute("""
                SELECT tq.id, tq.task_hash, tq.summary, tq.full_content
                FROM task_queue tq
                WHERE tq.status = 'pending'
                  AND tq.worker_type = ?
                  AND NOT EXISTS (
                    SELECT 1 FROM task_dependencies td
                    WHERE td.task_id = tq.id
                    AND EXISTS (
                        SELECT 1 FROM task_queue tq2
                        WHERE tq2.id = td.depends_on_task_id
                        AND tq2.status != 'completed'
                    )
                  )
                ORDER BY tq.priority DESC, tq.created_at ASC
                LIMIT 1
            """, (worker_type,))

            row = cur.fetchone()
            if not row:
                return None

            task_id = row[0]

            # Create lease
            cur.execute(
                "INSERT INTO task_leases (task_id, worker_id, timeout) VALUES (?, ?, ?)",
                (task_id, worker_id, timeout),
            )

            # Update task status
            cur.execute(
                "UPDATE task_queue SET status = 'leased', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (task_id,),
            )

            # Update worker
            cur.execute(
                "UPDATE worker_registry SET current_task = ?, status = 'busy' WHERE worker_id = ?",
                (task_id, worker_id),
            )

            self.conn.commit()

            return {
                "id": task_id,
                "task_hash": row[1],
                "summary": row[2],
                "full_content": row[3],
            }
        except sqlite3.OperationalError:
            self.conn.rollback()
            return None

    def complete_task(self, task_id: int, worker_id: str, status: str, result: str = ""):
        """Mark a task as completed."""
        cur = self.conn.cursor()

        # Update task
        cur.execute(
            "UPDATE task_queue SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (status, task_id),
        )

        # Remove lease
        cur.execute("DELETE FROM task_leases WHERE task_id = ?", (task_id,))

        # Free worker
        cur.execute(
            "UPDATE worker_registry SET current_task = NULL, status = 'idle' WHERE worker_id = ?",
            (worker_id,),
        )

        self.conn.commit()

    def retry_task(self, task_id: int):
        """Retry a failed task."""
        self.conn.execute(
            "UPDATE task_queue SET status = 'pending', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (task_id,),
        )
        self.conn.commit()

    def cancel_task(self, task_id: int):
        """Cancel a task."""
        self.conn.execute(
            "UPDATE task_queue SET status = 'cancelled' WHERE id = ?",
            (task_id,),
        )
        self.conn.commit()

    def recover_stale_leases(self, timeout_seconds: int = 300) -> List[Dict]:
        """Recover tasks from dead workers."""
        cur = self.conn.cursor()

        # Find stale leases
        cur.execute("""
            SELECT tl.task_id, tl.worker_id, tq.summary
            FROM task_leases tl
            JOIN task_queue tq ON tl.task_id = tq.id
            WHERE datetime(tl.leased_at, '+' || tl.timeout || ' seconds') < datetime('now')
        """)

        stale = cur.fetchall()

        for task_id, worker_id, summary in stale:
            # Reset task to pending
            cur.execute(
                "UPDATE task_queue SET status = 'pending' WHERE id = ?",
                (task_id,),
            )
            # Remove lease
            cur.execute("DELETE FROM task_leases WHERE task_id = ?", (task_id,))
            # Mark worker as dead
            cur.execute(
                "UPDATE worker_registry SET status = 'dead', current_task = NULL WHERE worker_id = ?",
                (worker_id,),
            )

        self.conn.commit()
        return [{"task_id": r[0], "worker_id": r[1], "summary": r[2]} for r in stale]

    def register_worker(
        self,
        worker_id: str,
        worker_type: str,
        capabilities: list,
        model: str = None,
        backend: str = None,
    ):
        """Register or update a worker."""
        self.conn.execute("""
            INSERT INTO worker_registry (worker_id, worker_type, capabilities, model, backend, status)
            VALUES (?, ?, ?, ?, ?, 'idle')
            ON CONFLICT(worker_id) DO UPDATE SET
                worker_type = excluded.worker_type,
                capabilities = excluded.capabilities,
                model = excluded.model,
                backend = excluded.backend,
                status = 'idle',
                last_heartbeat = CURRENT_TIMESTAMP
        """, (worker_id, worker_type, json.dumps(capabilities), model, backend))
        self.conn.commit()

    def worker_heartbeat(self, worker_id: str, status: str = "alive"):
        """Update worker heartbeat."""
        self.conn.execute(
            "INSERT INTO worker_heartbeats (worker_id, status) VALUES (?, ?)",
            (worker_id, status),
        )
        self.conn.execute(
            "UPDATE worker_registry SET last_heartbeat = CURRENT_TIMESTAMP WHERE worker_id = ?",
            (worker_id,),
        )
        self.conn.commit()

    def get_dead_workers(self, timeout_seconds: int = 120) -> List[str]:
        """Get workers that haven't sent heartbeat."""
        cur = self.conn.execute("""
            SELECT worker_id FROM worker_registry
            WHERE datetime(last_heartbeat, '+' || ? || ' seconds') < datetime('now')
            AND status != 'dead'
        """, (timeout_seconds,))
        return [r[0] for r in cur.fetchall()]


def get_db(project_root: Path) -> WorkflowDB:
    """Get or create workflow DB for a project."""
    db_path = project_root / ".project-ai" / "workflow_state.db"
    return WorkflowDB(db_path)


def main():
    """CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: workflow_db.py <command> [args]")
        sys.exit(1)

    cmd = sys.argv[1]

    # Simple commands for testing
    if cmd == "init" and len(sys.argv) >= 3:
        project_root = Path(sys.argv[2])
        db = get_db(project_root)
        print(f"DB initialized at: {project_root}/.project-ai/workflow_state.db")
        db.close()


if __name__ == "__main__":
    main()
