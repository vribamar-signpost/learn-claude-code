# Lesson evidence

Signpost Claude Code training, deliverable "Completed learn-claude-code repo": evidence of each lesson run.

The training plan lists lessons s01–s19. Upstream has since reorganized the course into 17 lessons (`s01_agent_loop` … `s17_goal_loop`); see the root README "Version Status" section. Every current lesson has a transcript here.

## How the transcripts were produced

`run_lessons.py` starts each lesson's `code.py` in a pseudo-terminal, types the prompts suggested in that lesson's README, and saves the full session (with ANSI codes stripped) as `<lesson>.txt`. Lessons run in a separate git worktree (`../learn-claude-code-run`), so files the model creates or deletes stay out of this checkout. Permission prompts are approved, except tool calls touching `/etc`, `/tmp`, or `sudo`, which are denied to show the deny path.

```sh
uv venv --python 3.12 .venv && uv pip install -r requirements.txt pexpect
cp .env.example .env   # set ANTHROPIC_API_KEY and MODEL_ID
.venv/bin/python evidence/run_lessons.py          # all lessons
.venv/bin/python evidence/run_lessons.py s09 s13  # selected lessons
```
