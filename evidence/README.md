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

## Results

All runs used `claude-haiku-4-5-20251001`.

| Lesson | Transcript | What it shows |
|---|---|---|
| s01 | [s01_agent_loop.txt](s01_agent_loop.txt) | Single bash tool driving the loop; creates and runs `hello.py` |
| s02 | [s02_tool_use.txt](s02_tool_use.txt) | Dispatch map with read/write/edit/glob tools, multiple calls per turn |
| s03 | [s03_permission.txt](s03_permission.txt) | Permission gates: allowed, approved `rm`, denied write to `/etc` |
| s04 | [s04_hooks.txt](s04_hooks.txt) | `[HOOK]` logs around every tool call; `/tmp` delete stopped as `[blocked] 'rm -rf /'` |
| s05 | [s05_todo_write.txt](s05_todo_write.txt) | `todo_write` plan first, statuses moving to completed |
| s06 | [s06_subagent.txt](s06_subagent.txt) | Subagent with fresh context returning only its final text |
| s07 | [s07_skill_loading.txt](s07_skill_loading.txt) | Skill catalog in prompt, full `SKILL.md` loaded on demand |
| s08 | [s08_context_compact.txt](s08_context_compact.txt) | Several file reads, then a 202,706-char result flagged as large output (compaction happens inside the context and is not printed) |
| s09 | [s09_memory.txt](s09_memory.txt) | Preference stored, recalled after restart; session-only rule not persisted |
| s10 | [s10_task_system.txt](s10_task_system.txt) | File-backed task graph with dependencies unblocking on completion |
| s11 | [s11_background_tasks.txt](s11_background_tasks.txt) | Background jobs `bg_0001` / `bg_0002` started, collected and summarized on a later turn |
| s12 | [s12_cron_scheduler.txt](s12_cron_scheduler.txt) | Durable cron job scheduled, listed, fired (`[cron] due` / `delivered`) and cancelled |
| s13 | [s13_agent_teams.txt](s13_agent_teams.txt) | Lead + 3 teammates, task board, task-bound worktree, mailbox results and idle notifications (API credits ran out in the final lines) |
| s14 | [s14_mcp_plugin.txt](s14_mcp_plugin.txt) | `connect_mcp` then `mcp__docs__search` / `mcp__docs__get_version` |
| s15 | [s15_integrated_harness.txt](s15_integrated_harness.txt) | Hooks, permissions, cron reminder (`[cron auto]` / `[cron inject]`), background job, memory and todos in one loop |
| s16 | [s16_workflow_runtime.txt](s16_workflow_runtime.txt) | Deterministic demo, resume from journal (`agents=0 tokens=0`), live review-changes workflow |
| s17 | [s17_goal_loop.txt](s17_goal_loop.txt) | `/goal` with evaluator confirming `[goal] achieved` |
