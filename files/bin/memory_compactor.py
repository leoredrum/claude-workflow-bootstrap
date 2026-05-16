#!/usr/bin/env python3
"""Deterministic memory compactor for .project-ai files."""

import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

MAX_MEMORY_LINES = 500
MAX_HANDOFF_LINES = 300


def count_lines(path: Path) -> int:
    if not path.exists():
        return 0
    return len(path.read_text().splitlines())


def is_old_entry(line: str, days: int = 30) -> bool:
    """Check if entry is older than N days."""
    date_match = re.search(r'(\d{4}-\d{2}-\d{2})', line)
    if date_match:
        try:
            entry_date = datetime.strptime(date_match.group(1), "%Y-%m-%d")
            return (datetime.now() - entry_date).days > days
        except Exception:
            pass
    return False


def compact_memory(project_ai_dir: Path) -> dict:
    """Compact MEMORY.md if needed."""
    memory_file = project_ai_dir / "MEMORY.md"

    if not memory_file.exists():
        return {"action": "skip", "reason": "MEMORY.md not found"}

    line_count = count_lines(memory_file)

    if line_count <= MAX_MEMORY_LINES:
        return {"action": "skip", "reason": f"Lines: {line_count} <= {MAX_MEMORY_LINES}"}

    lines = memory_file.read_text().splitlines()

    # Simple deterministic compaction: keep last N entries per section
    sections = {}
    current_section = "general"

    for line in lines:
        if line.startswith("## "):
            current_section = line[3:].strip().lower()
            sections.setdefault(current_section, [])
        elif line.strip() and not line.startswith("#"):
            sections.setdefault(current_section, [])
            # Keep only last 10 entries per section
            if len(sections[current_section]) < 10:
                sections[current_section].append(line)

    # Rebuild
    compacted = ["# Project Memory\n"]
    for section, entries in sections.items():
        if entries:
            compacted.append(f"\n## {section.title()}\n")
            compacted.extend(entries)

    memory_file.write_text("\n".join(compacted))

    return {"action": "compacted", "before": line_count, "after": len(compacted)}


def compact_handoff(project_ai_dir: Path) -> dict:
    """Compact HANDOFF.md if needed."""
    handoff_file = project_ai_dir / "HANDOFF.md"

    if not handoff_file.exists():
        return {"action": "skip", "reason": "HANDOFF.md not found"}

    line_count = count_lines(handoff_file)

    if line_count <= MAX_HANDOFF_LINES:
        return {"action": "skip", "reason": f"Lines: {line_count} <= {MAX_HANDOFF_LINES}"}

    # Keep last 5 handoff entries
    content = handoff_file.read_text()
    entries = re.split(r'## \d{4}-\d{2}-\d{2}', content)

    # Keep header + last 5
    header = entries[0]
    recent = entries[-5:] if len(entries) > 5 else entries

    compacted = header + "\n".join(recent)
    handoff_file.write_text(compacted)

    return {"action": "compacted", "before": line_count, "after": len(compacted.splitlines())}


def main():
    if len(sys.argv) < 2:
        print("Usage: memory_compactor.py <project-root>")
        sys.exit(1)

    project_root = Path(sys.argv[1])
    project_ai_dir = project_root / ".project-ai"

    results = {
        "memory": compact_memory(project_ai_dir),
        "handoff": compact_handoff(project_ai_dir)
    }

    # Write summary
    summary_file = project_ai_dir / "COMPACTION_SUMMARY.md"
    summary_file.write_text(f"""# Memory Compaction Summary

**Date:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## MEMORY.md
- Action: {results['memory']['action']}
- {results['memory'].get('reason', '')}

## HANDOFF.md
- Action: {results['handoff']['action']}
- {results['handoff'].get('reason', '')}

## Recommendations

{"Memory files are healthy." if results['memory']['action'] == 'skip' else 'Consider archiving old MEMORY.md entries.'}
{"Handoff file is healthy." if results['handoff']['action'] == 'skip' else 'Consider archiving old HANDOFF.md entries.'}
""")

    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
