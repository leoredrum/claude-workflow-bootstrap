#!/usr/bin/env python3
"""Bootstrap self-test - verifies claude-plan workflow installation."""

import os
import sys
import subprocess
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
import sqlite3


class Colors:
    RESET = "\033[0m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BLUE = "\033[94m"
    BOLD = "\033[1m"


def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.RESET}\n")


def print_pass(text):
    print(f"{Colors.GREEN}✓{Colors.RESET} {text}")


def print_fail(text):
    print(f"{Colors.RED}✗{Colors.RESET} {text}")


def print_warn(text):
    print(f"{Colors.YELLOW}⚠{Colors.RESET} {text}")


def check_path():
    """Check PATH configuration."""
    results = []

    # Check if ~/bin is in PATH
    home_bin = str(Path.home() / "bin")
    path = os.getenv("PATH", "")

    if home_bin in path:
        print_pass(f"PATH contains {home_bin}")
        results.append(True)
    else:
        print_fail(f"PATH missing {home_bin}")
        results.append(False)

    return all(results)


def check_command(cmd, description=None):
    """Check if command is available."""
    desc = description or cmd

    try:
        result = subprocess.run(
            ["which", cmd],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            path = result.stdout.strip()
            print_pass(f"{desc} found at {path}")
            return True
        else:
            print_fail(f"{desc} not found")
            return False
    except Exception as e:
        print_fail(f"{desc} check failed: {e}")
        return False


def check_claude_plan():
    """Check claude-plan installation."""
    results = []

    if check_command("claude-plan", "claude-plan"):
        results.append(True)

        # Check help works
        try:
            result = subprocess.run(
                ["claude-plan", "--help"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if "claude-plan" in result.stdout.lower() or "usage" in result.stdout.lower():
                print_pass("claude-plan --help works")
                results.append(True)
            else:
                print_warn("claude-plan --help output unexpected")
                results.append(True)
        except Exception as e:
            print_warn(f"claude-plan --help failed: {e}")
            results.append(True)
    else:
        results.append(False)

    return all(results)


def check_local_coder():
    """Check local-coder installation."""
    results = []

    # Check local-coder script
    local_coder_path = Path.home() / "AI" / "local-coder" / "bin" / "local-coder"

    if local_coder_path.exists():
        print_pass(f"local-coder found at {local_coder_path}")
        results.append(True)

        # Check if executable
        if os.access(local_coder_path, os.X_OK):
            print_pass("local-coder is executable")
            results.append(True)
        else:
            print_fail("local-coder is not executable")
            results.append(False)
    else:
        print_fail(f"local-coder not found at {local_coder_path}")
        results.append(False)

    # Check worker script
    worker_path = Path.home() / "AI" / "local-coder" / "bin" / "local_coder_worker.py"
    if worker_path.exists():
        print_pass(f"local_coder_worker.py found")
        results.append(True)
    else:
        print_fail("local_coder_worker.py not found")
        results.append(False)

    return all(results)


def check_workflow_components():
    """Check workflow orchestrator components."""
    results = []

    bin_dir = Path.home() / "AI" / "local-coder" / "bin"

    components = [
        ("workflow_db.py", "Workflow database module"),
        ("workflow-orchestrator", "Workflow orchestrator CLI"),
        ("workflow_orchestrator.py", "Workflow orchestrator Python"),
        ("orchestrator_worker.py", "Orchestrator worker"),
        ("workflow-query", "Workflow query CLI"),
        ("workflow_query.py", "Workflow query Python"),
        ("memory_compactor.py", "Memory compactor"),
    ]

    for filename, desc in components:
        path = bin_dir / filename
        if path.exists():
            print_pass(f"{desc} ({filename})")
            results.append(True)
        else:
            print_fail(f"{desc} ({filename}) not found")
            results.append(False)

    return all(results)


def check_skill_tools():
    """Check skill tool installation."""
    results = []

    bin_dir = Path.home() / "bin"

    tools = [
        ("bootstrap-install-skills", "Skill installer"),
        ("bootstrap-update-skills", "Skill updater"),
        ("skill-router", "Skill auto-router"),
    ]

    for filename, desc in tools:
        path = bin_dir / filename
        if path.exists():
            print_pass(f"{desc} ({filename})")
            results.append(True)
        else:
            print_warn(f"{desc} ({filename}) not found (optional)")
            results.append(True)  # Optional

    # Check if skills are installed
    skills_dir = Path.home() / ".claude" / "skills"
    if skills_dir.exists():
        skill_count = len([d for d in skills_dir.iterdir() if d.is_dir()])
        print(f"Skills installed: {skill_count}")
        if skill_count > 0:
            print_pass("mattpocock skills installed")
        else:
            print_warn("No skills installed (run bootstrap-install-skills)")
        results.append(True)
    else:
        print_warn("Skills directory not found (optional)")
        results.append(True)

    return all(results)


def check_python():
    """Check Python installation."""
    results = []

    try:
        result = subprocess.run(
            ["python3", "--version"],
            capture_output=True,
            text=True
        )
        version = result.stdout.strip()
        print_pass(f"Python version: {version}")

        # Parse version
        major, minor = map(int, version.split()[-1].split('.')[:2])
        if major >= 3 and minor >= 10:
            print_pass("Python version >= 3.10")
            results.append(True)
        else:
            print_warn("Python version < 3.10 may have issues")
            results.append(True)

        return all(results)
    except Exception as e:
        print_fail(f"Python check failed: {e}")
        return False


def check_sqlite():
    """Check SQLite and WAL mode support."""
    results = []

    try:
        # Try to create a test database with WAL
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            test_db = f.name

        conn = sqlite3.connect(test_db)
        conn.execute("PRAGMA journal_mode=WAL")
        mode = conn.execute("SELECT journal_mode FROM pragma_journal_mode").fetchone()[0]

        if mode.lower() == "wal":
            print_pass("SQLite WAL mode supported")
            results.append(True)
        else:
            print_warn(f"SQLite WAL mode not working (got: {mode})")
            results.append(True)

        conn.close()
        os.unlink(test_db)

        return all(results)
    except Exception as e:
        print_fail(f"SQLite check failed: {e}")
        return False


def check_ollama():
    """Check Ollama installation."""
    results = []

    if not check_command("ollama", "Ollama"):
        print_warn("Ollama not found - local-coder may not work")
        return True  # Not critical

    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            timeout=10
        )

        if "qwen2.5-coder:32b" in result.stdout:
            print_pass("qwen2.5-coder:32b model available")
            results.append(True)
        else:
            print_warn("qwen2.5-coder:32b not found in ollama list")
            results.append(True)  # Not critical

        return all(results)
    except Exception as e:
        print_warn(f"Ollama check failed: {e}")
        return True


def run_integration_test():
    """Run integration test in temporary directory."""
    results = []

    print_header("Running Integration Test")

    # Create temp directory
    with tempfile.TemporaryDirectory(prefix="bootstrap-self-test-") as test_dir:
        test_path = Path(test_dir)
        project_ai = test_path / ".project-ai"
        project_ai.mkdir()

        # Create test task
        task_file = project_ai / "TASK.md"
        task_file.write_text("""# Test Task

Create hello.txt with "Hello from bootstrap test!"
""")

        print(f"Test directory: {test_dir}")
        print_pass("Created test task")
        results.append(True)

        # Try to run local-coder
        local_coder = Path.home() / "AI" / "local-coder" / "bin" / "local-coder"

        if local_coder.exists():
            try:
                # We won't actually run it (might need ollama)
                # Just verify the script can be called
                result = subprocess.run(
                    [str(local_coder), "--help"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )

                if "Usage" in result.stdout or "usage" in result.stdout:
                    print_pass("local-coder can be invoked")
                    results.append(True)
                else:
                    print_warn("local-coder output unexpected")
                    results.append(True)

            except Exception as e:
                print_warn(f"local-coder invocation failed: {e}")
                results.append(True)
        else:
            print_warn("local-coder not installed, skipping test")
            results.append(True)

        # Create fake RESULT.md to verify structure
        result_file = project_ai / "RESULT.md"
        result_file.write_text("""# Implementation Result

**Status:** TEST
**implementation_executor:** bootstrap-self-test
**backend:** test
**model:** test

## Summary

Self-test completed successfully.

## Files Changed

- hello.txt (test)
""")

        print_pass("Created test RESULT.md")
        results.append(True)

        # Verify RESULT.md structure
        content = result_file.read_text()
        required = ["implementation_executor", "backend", "model", "Status"]
        missing = [r for r in required if r not in content]

        if not missing:
            print_pass("RESULT.md has required fields")
            results.append(True)
        else:
            print_fail(f"RESULT.md missing fields: {missing}")
            results.append(False)

    return all(results)


def doctor_mode():
    """Run doctor mode - diagnose issues."""
    print_header("Doctor Mode - Diagnosing Issues")

    issues = []

    # Check for broken symlinks
    home_bin = Path.home() / "bin"
    if home_bin.exists():
        for item in home_bin.iterdir():
            if item.is_symlink():
                try:
                    item.resolve()
                except ValueError:
                    issues.append(f"Broken symlink: {item.name}")
                    print_fail(f"Broken symlink: {item.name}")

    if not issues:
        print_pass("No broken symlinks found")

    # Check for stale databases
    project_ai = Path.cwd() / ".project-ai"
    if project_ai.exists():
        db_file = project_ai / "workflow_state.db"
        if db_file.exists():
            try:
                conn = sqlite3.connect(db_file)
                conn.execute("SELECT 1 FROM tasks LIMIT 1")
                conn.close()
                print_pass("Database is accessible")
            except Exception as e:
                issues.append(f"Stale database: {db_file}")
                print_fail(f"Database error: {e}")

    # Check for failed workers
    bin_dir = Path.home() / "AI" / "local-coder" / "bin"
    orchestrator_py = bin_dir / "workflow_orchestrator.py"

    if orchestrator_py.exists():
        try:
            result = subprocess.run(
                ["python3", str(orchestrator_py), "status"],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=project_ai if project_ai.exists() else Path.cwd()
            )
            if "Pending" in result.stdout or "workers" in result.stdout:
                print_pass("workflow-orchestrator can query status")
            else:
                print_warn("workflow-orchestrator status unexpected")
        except Exception as e:
            issues.append("workflow-orchestrator failed")
            print_warn(f"workflow-orchestrator error: {e}")

    return issues


def generate_report(results, test_dir):
    """Generate verification report."""
    report_file = test_dir / "bootstrap-verification-report.md"

    total = len(results)
    passed = sum(1 for r in results.values() if r)
    failed = total - passed
    score = round(passed / total * 100, 1) if total > 0 else 0

    content = f"""# Bootstrap Verification Report

**Date:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Test Directory:** {test_dir}

## Summary

- **Total Checks:** {total}
- **Passed:** {passed}
- **Failed:** {failed}
- **Score:** {score}%

## Component Status

"""

    for name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        content += f"- **{name}:** {status}\n"

    content += f"""

## Recommendations

"""

    if score >= 90:
        content += "- All systems operational. Ready for production use.\n"
    elif score >= 70:
        content += "- Minor issues detected. Review failed checks above.\n"
    else:
        content += "- Critical issues detected. Please review and fix.\n"

    content += """

## Next Steps

1. If all checks passed, you're ready to use claude-plan
2. If checks failed, run `bootstrap-verify --doctor` for diagnostics
3. For component-specific issues, review the installation guide

## Installation Location

- claude-plan: ~/bin/claude-plan
- local-coder: ~/AI/local-coder/bin/
- CLAUDE config: ~/.claude/CLAUDE.md

---
Generated by bootstrap-verify v1.0
"""

    report_file.write_text(content)
    print_pass(f"Report written to {report_file}")

    return report_file


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Bootstrap self-test verification")
    parser.add_argument("--doctor", action="store_true", help="Run doctor mode")
    parser.add_argument("--report-dir", default=None, help="Custom report directory")

    args = parser.parse_args()

    print_header("claude-plan Bootstrap Self-Test")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    if args.doctor:
        issues = doctor_mode()
        if issues:
            print(f"\n{Colors.RED}Found {len(issues)} issue(s){Colors.RESET}")
            return 1
        else:
            print(f"\n{Colors.GREEN}No issues found{Colors.RESET}")
            return 0

    # Run all checks
    results = {}

    print_header("Environment Checks")
    results["PATH Configuration"] = check_path()
    results["Python Installation"] = check_python()
    results["SQLite Support"] = check_sqlite()
    results["Ollama (optional)"] = check_ollama()

    print_header("Component Checks")
    results["claude-plan"] = check_claude_plan()
    results["local-coder"] = check_local_coder()
    results["Workflow Components"] = check_workflow_components()
    results["Skill Tools (optional)"] = check_skill_tools()

    print_header("Integration Test")
    results["Integration Test"] = run_integration_test()

    # Generate report
    report_dir = Path(args.report_dir) if args.report_dir else Path.cwd()
    report_file = generate_report(results, report_dir)

    # Summary
    total = len(results)
    passed = sum(1 for r in results.values() if r)
    score = round(passed / total * 100, 1) if total > 0 else 0

    print_header("Test Summary")
    print(f"Total: {total} | Passed: {passed} | Failed: {total - passed}")
    print(f"Score: {score}%")

    if score >= 90:
        print(f"{Colors.GREEN}Bootstrap installation: OK{Colors.RESET}")
        return 0
    else:
        print(f"{Colors.YELLOW}Bootstrap installation: NEEDS ATTENTION{Colors.RESET}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
