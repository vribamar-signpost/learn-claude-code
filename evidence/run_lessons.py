#!/usr/bin/env python3
"""Drive each lesson's interactive REPL with the prompts suggested in its
README and save a plain-text transcript as evidence.

Lessons run inside a throwaway git worktree (default: ../learn-claude-code-run)
so files the model creates or deletes never touch this checkout.

Usage:
    .venv/bin/python evidence/run_lessons.py            # all lessons
    .venv/bin/python evidence/run_lessons.py s01 s07    # selected lessons
"""

import datetime
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import pexpect
from dotenv import dotenv_values

REPO = Path(__file__).resolve().parent.parent
EVIDENCE = REPO / "evidence"
RUN_DIR = Path(os.getenv("LESSON_RUN_DIR", REPO.parent / "learn-claude-code-run"))
PYTHON = REPO / ".venv" / "bin" / "python"

PROMPT_RE = r"s\d\d >> "
ALLOW_RE = r"Allow\? \[y/N\] "
ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]|[\x01\x02]|\r")
# Tool calls whose preceding output matches this are denied instead of approved.
DENY_RE = re.compile(r"/etc/|/tmp\b|sudo|rm -rf /(\s|$)")

TURN_TIMEOUT = 900

# Each step: ("say", text) | ("wait", seconds) | ("settle", quiet_s, max_s) | ("restart",)
LESSONS = {
    "s01_agent_loop": {"steps": [
        ("say", 'Create a file called hello.py that prints "Hello, World!"'),
        ("say", "List all Python files in this directory"),
    ]},
    "s02_tool_use": {"steps": [
        ("say", "Read the file README.md and tell me what this project is about"),
        ("say", 'Create a file called test.py that prints "hello", then read it back'),
        ("say", "Find all Python files in this directory"),
        ("say", "Read both README.md and requirements.txt, then create a summary file"),
    ]},
    "s03_permission": {"steps": [
        ("say", "Create a file called test.txt in the current directory"),
        ("say", "Delete the file test.txt"),
        ("say", "What files are in the current directory?"),
        ("say", "Try to write a file to /etc/something"),
    ]},
    "s04_hooks": {"steps": [
        ("say", "Read the file README.md"),
        ("say", "Create a file called test.txt"),
        ("say", "Delete all temporary files in /tmp"),
    ]},
    "s05_todo_write": {"steps": [
        ("say", "Refactor s05_todo_write/example/hello.py: add type hints, docstrings, and a main guard"),
        ("say", "Create a Python package under s05_todo_write/example/demo_pkg with __init__.py, utils.py, and tests/test_utils.py"),
    ]},
    "s06_subagent": {"steps": [
        ("say", "Use a subtask to find what testing framework this project uses"),
        ("say", "Use a task to create s06_subagent/example/string_tools.py with a slugify(text: str) function, then verify it from the parent agent"),
    ]},
    "s07_skill_loading": {"steps": [
        ("say", "What skills are available?"),
        ("say", "Load the code-review skill and follow its instructions"),
        ("say", "Review README.md and load the relevant skill first"),
    ]},
    "s08_context_compact": {"steps": [
        ("say", "Read the README.md files from s01_agent_loop through s05_todo_write. Compare their top-level headings and summarize the naming pattern."),
        ("say", "Analyze the structure of web/src/data/generated/docs.json and explain the main fields in one lesson record."),
    ]},
    "s09_memory": {"steps": [
        ("say", "I prefer using tabs for indentation. Remember that."),
        ("restart",),
        ("say", "What indentation style do I prefer?"),
        ("say", "I prefer concise commit messages in the imperative mood. Remember that."),
        ("say", "What indentation style do I prefer?"),
        ("say", "Do not create files in this session."),
    ]},
    "s10_task_system": {"steps": [
        ("say", "Create tasks: setup database schema, create API endpoints (depends on schema), write tests (depends on endpoints), write docs (depends on schema)"),
        ("say", "List all tasks and their statuses"),
        ("say", "Claim the first unblocked task and complete it"),
        ("say", "List tasks again - which ones are now unblocked?"),
    ]},
    "s11_background_tasks": {"steps": [
        ("say", "Run pip list in the background and find all Python files in this directory"),
        ("say", "Run a short sleep in the background, then list all Markdown files"),
        ("say", "Did the background jobs finish? Summarize their results."),
    ]},
    "s12_cron_scheduler": {"steps": [
        ("say", 'Schedule "run date" every 2 minutes and keep it after restart.'),
        ("say", "List all cron jobs."),
        ("wait", 150),
        ("say", "Cancel the cron job you just created."),
    ]},
    "s13_agent_teams": {"steps": [
        ("say", "Put the backend refactor on a shared task board. Complete configuration, authentication, and tests in parallel where dependencies allow. Use a worktree for authentication, preserve existing interfaces, and summarize the result."),
        ("say", "Go ahead."),
        ("settle", 120, 1200),
    ]},
    "s14_mcp_plugin": {"steps": [
        ("say", "Connect to the docs server, search for agent hooks, and tell me the current documentation API version."),
    ]},
    "s15_integrated_harness": {"steps": [
        ("say", "Inspect this repository and tell me which Python files matter most."),
        ("say", "Search the connected documentation for agent loop guidance."),
        ("say", "Remind me about the meeting in 3 minutes."),
        ("say", "Install the dependencies in the background while you read README.md."),
        ("wait", 200),
        ("say", "Summarize what happened in this session, including any reminders or background results."),
    ]},
    "s16_workflow_runtime": {"runs": [
        {"args": ["demo"], "steps": []},
        {"args": ["resume"], "steps": []},
        {"args": [], "steps": [
            ("say", "Read the changes from `git show HEAD --stat --patch`, place that text in args.changes, and run the saved review-changes workflow."),
        ]},
    ]},
    "s17_goal_loop": {"steps": [
        ("say", "/goal s17_goal_loop/example/fizzbuzz.py defines fizzbuzz(n) and python -m pytest s17_goal_loop/example exits with code 0"),
    ]},
}


def ensure_worktree():
    if (RUN_DIR / ".git").exists():
        return
    subprocess.run(
        ["git", "-C", str(REPO), "worktree", "add", "--detach", str(RUN_DIR), "HEAD"],
        check=True,
    )


def child_env():
    env = dict(os.environ)
    env.update({k: v for k, v in dotenv_values(REPO / ".env").items() if v is not None})
    env["PATH"] = f"{PYTHON.parent}{os.pathsep}{env.get('PATH', '')}"
    env["PYTHONUNBUFFERED"] = "1"
    env["TERM"] = "xterm"
    return env


class Transcript:
    def __init__(self):
        self.parts = []

    def write(self, data):
        self.parts.append(data)

    def flush(self):
        pass

    def text(self):
        return ANSI_RE.sub("", "".join(self.parts))


def pump(child, until, timeout):
    """Read output, answering permission prompts, until `until` matches.
    Returns the matched pattern index (0=prompt) or raises on EOF/timeout."""
    deadline = time.time() + timeout
    while True:
        remaining = max(1, deadline - time.time())
        idx = child.expect([until, ALLOW_RE, pexpect.EOF], timeout=remaining)
        if idx == 1:
            context = ANSI_RE.sub("", child.before[-800:])
            child.sendline("n" if DENY_RE.search(context) else "y")
            continue
        return idx


def drain(child, seconds, quiet=None):
    """Keep reading output for `seconds` (or until `quiet` seconds of silence)."""
    end = time.time() + seconds
    last_output = time.time()
    while time.time() < end:
        try:
            idx = child.expect([ALLOW_RE, r".+"], timeout=5)
            if idx == 0:
                context = ANSI_RE.sub("", child.before[-800:])
                child.sendline("n" if DENY_RE.search(context) else "y")
            last_output = time.time()
        except pexpect.TIMEOUT:
            if quiet and time.time() - last_output >= quiet:
                return
        except pexpect.EOF:
            return


def spawn(script, args, log, env):
    log.write(f"\n$ python {script} {' '.join(args)}\n")
    child = pexpect.spawn(
        str(PYTHON), [script, *args], cwd=str(RUN_DIR), env=env,
        encoding="utf-8", codec_errors="replace", dimensions=(60, 220),
    )
    child.logfile_read = log
    return child


def run_once(lesson, args, steps, log, env):
    script = f"{lesson}/code.py"
    child = spawn(script, args, log, env)
    interactive = bool(steps)
    try:
        if interactive:
            pump(child, PROMPT_RE, 120)
        for step in steps:
            kind = step[0]
            if kind == "say":
                child.sendline(step[1])
                if pump(child, PROMPT_RE, TURN_TIMEOUT) == 2:
                    return "exited early"
            elif kind == "wait":
                drain(child, step[1])
            elif kind == "settle":
                drain(child, step[2], quiet=step[1])
            elif kind == "restart":
                child.sendline("q")
                child.expect(pexpect.EOF, timeout=60)
                child = spawn(script, args, log, env)
                pump(child, PROMPT_RE, 120)
        if interactive:
            child.sendline("q")
        child.expect(pexpect.EOF, timeout=TURN_TIMEOUT)
        child.close()
        return f"exit {child.exitstatus}"
    except pexpect.TIMEOUT:
        return "timeout"
    finally:
        if child.isalive():
            child.terminate(force=True)


def run_lesson(lesson, env):
    spec = LESSONS[lesson]
    runs = spec.get("runs", [{"args": [], "steps": spec.get("steps", [])}])
    log = Transcript()
    started = datetime.datetime.now()
    model = env.get("MODEL_ID", "?")
    log.write(f"# {lesson}\n# run at {started:%Y-%m-%d %H:%M:%S} · model {model}\n")
    results = [run_once(lesson, r["args"], r["steps"], log, env) for r in runs]
    elapsed = (datetime.datetime.now() - started).total_seconds()
    out = EVIDENCE / f"{lesson}.txt"
    out.write_text(log.text(), encoding="utf-8")
    status = ", ".join(results)
    print(f"{lesson}: {status} ({elapsed:.0f}s) -> {out.relative_to(REPO)}", flush=True)
    return status, elapsed


def main(selected):
    lessons = [l for l in LESSONS if not selected or any(l.startswith(s) for s in selected)]
    ensure_worktree()
    env = child_env()
    if not env.get("ANTHROPIC_API_KEY") or not env.get("MODEL_ID"):
        sys.exit("Set ANTHROPIC_API_KEY and MODEL_ID in .env first")
    for lesson in lessons:
        run_lesson(lesson, env)


if __name__ == "__main__":
    main(sys.argv[1:])
