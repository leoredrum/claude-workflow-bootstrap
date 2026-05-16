#!/usr/bin/env python3
"""Workflow orchestrator CLI."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from workflow_db import get_db
from orchestrator_worker import ImplementerWorker, ReviewerWorker, TesterWorker


def find_project_root() -> Path:
    """Find project root with .project-ai."""
    cwd = Path.cwd()
    while cwd != cwd.parent:
        if (cwd / ".project-ai").exists():
            return cwd
        cwd = cwd.parent
    return Path.cwd()


def cmd_status(args) -> None:
    """Show orchestrator status."""
    project_root = find_project_root()
    db = get_db(project_root)

    cur = db.conn.execute("""
        SELECT
            (SELECT COUNT(*) FROM task_queue WHERE status = 'pending') as pending,
            (SELECT COUNT(*) FROM task_queue WHERE status = 'leased') as leased,
            (SELECT COUNT(*) FROM task_queue WHERE status = 'completed') as completed,
            (SELECT COUNT(*) FROM task_queue WHERE status = 'failed') as failed,
            (SELECT COUNT(*) FROM worker_registry WHERE status = 'busy') as busy_workers,
            (SELECT COUNT(*) FROM worker_registry WHERE status = 'idle') as idle_workers
    """)

    stats = cur.fetchone()
    print(f"Pending:    {stats[0]}")
    print(f"Leased:     {stats[1]}")
    print(f"Completed:  {stats[2]}")
    print(f"Failed:     {stats[3]}")
    print(f"Busy Workers:  {stats[4]}")
    print(f"Idle Workers:  {stats[5]}")

    db.close()


def cmd_queue(args) -> None:
    """Show task queue."""
    project_root = find_project_root()
    db = get_db(project_root)

    cur = db.conn.execute("""
        SELECT id, summary, worker_type, status, priority, created_at
        FROM task_queue
        ORDER BY priority DESC, created_at ASC
        LIMIT 20
    """)

    print(f"{'ID':<5} {'Status':<12} {'Type':<12} {'Prio':<5} {'Summary':<30}")
    print("-" * 70)

    for row in cur.fetchall():
        print(f"{row[0]:<5} {row[3]:<12} {row[2]:<12} {row[4]:<5} {row[1][:30]}")

    db.close()


def cmd_workers(args) -> None:
    """Show workers."""
    project_root = find_project_root()
    db = get_db(project_root)

    cur = db.conn.execute("""
        SELECT worker_id, worker_type, status, current_task,
               datetime(last_heartbeat) as heartbeat
        FROM worker_registry
        ORDER BY last_heartbeat DESC
    """)

    print(f"{'Worker ID':<20} {'Type':<12} {'Status':<12} {'Current Task':<10} {'Last Heartbeat':<20}")
    print("-" * 80)

    for row in cur.fetchall():
        task_str = str(row[3]) if row[3] else "None"
        print(f"{row[0]:<20} {row[1]:<12} {row[2]:<12} {task_str:<10} {row[4][:19]}")

    db.close()


def cmd_enqueue(args) -> None:
    """Enqueue a task."""
    if not args.summary:
        print("Error: summary required")
        sys.exit(1)

    project_root = find_project_root()
    db = get_db(project_root)

    worker_type = args.type or "implementer"
    task_id = db.enqueue_task(args.summary, "", worker_type)

    print(f"Task enqueued: ID={task_id}")
    db.close()


def cmd_retry(args) -> None:
    """Retry a task."""
    project_root = find_project_root()
    db = get_db(project_root)

    db.retry_task(args.task_id)
    print(f"Task {args.task_id} marked for retry")
    db.close()


def cmd_recover(args) -> None:
    """Recover stale leases."""
    project_root = find_project_root()
    db = get_db(project_root)

    recovered = db.recover_stale_leases()
    print(f"Recovered {len(recovered)} stale tasks")

    for item in recovered:
        print(f"  Task {item['task_id']}: {item['summary'][:30]}")

    db.close()


def cmd_start(args) -> None:
    """Start a worker."""
    if not args.worker_id:
        print("Error: --worker-id required")
        sys.exit(1)

    worker_type = args.type or "implementer"
    project_root = find_project_root()

    worker_classes: dict[str, type] = {
        "implementer": ImplementerWorker,
        "reviewer": ReviewerWorker,
        "tester": TesterWorker,
    }

    worker_cls = worker_classes[worker_type]
    worker = worker_cls(
        args.worker_id,
        worker_type,
        project_root,
        args.model,
        args.backend,
    )

    print(f"Starting {worker_type} worker: {args.worker_id}")
    worker.run()


def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")

    # start command
    start_p = subparsers.add_parser("start")
    start_p.add_argument("--worker-id", required=True)
    start_p.add_argument("--type", choices=["implementer", "reviewer", "tester"])
    start_p.add_argument("--model")
    start_p.add_argument("--backend")

    # enqueue command
    enqueue_p = subparsers.add_parser("enqueue")
    enqueue_p.add_argument("summary")
    enqueue_p.add_argument("--type", choices=["implementer", "reviewer", "tester"])

    # retry command
    retry_p = subparsers.add_parser("retry")
    retry_p.add_argument("task_id", type=int)

    # status, queue, workers, recover, stop (no args)
    subparsers.add_parser("status")
    subparsers.add_parser("queue")
    subparsers.add_parser("workers")
    subparsers.add_parser("recover")
    subparsers.add_parser("stop")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    commands = {
        "start": cmd_start,
        "status": cmd_status,
        "queue": cmd_queue,
        "workers": cmd_workers,
        "enqueue": cmd_enqueue,
        "retry": cmd_retry,
        "recover": cmd_recover,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
