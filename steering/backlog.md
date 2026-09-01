# Backlog

Ideas that are worth building but not yet in a pipeline run.

---

## Cross-Agent Central Monitor

**Status:** KIV
**Context:** When running hundreds of parallel agents across git worktrees and different tools (Claude Code, Codex, etc.), tmux doesn't scale. Need a central dashboard.

<!-- cspell:ignore worktree worktrees myproject -->

### Architecture

A neutral drop directory `~/.agent-monitor/runs/` that any agent or wrapper writes to. A `monitor.py` polls this directory and renders a live status table.

### Registry file format

One JSON file per run at `~/.agent-monitor/runs/{run-id}.json`:

```json
{
  "id": "run-abc123",
  "agent": "claude-code",
  "label": "feat-auth in myproject",
  "project": "/path/to/project",
  "state_file": "/path/to/pipeline/feat-auth/state.md",
  "pid": 12345,
  "status": "running",
  "step": "coder",
  "started": "2026-09-01T10:30:00Z",
  "updated": "2026-09-01T10:35:00Z"
}
```

| Field | Values | Notes |
| --- | --- | --- |
| `agent` | `claude-code`, `codex`, `gemini-cli`, `custom` | Tool that's running |
| `status` | `running`, `done`, `failed`, `abandoned` | |
| `step` | e.g. `analyst`, `coder`, `tester` | `null` for non-Claude agents |
| `state_file` | absolute path | `null` for non-Claude agents — status only |

### Discovery logic (monitor.py)

1. Read all `~/.agent-monitor/runs/*.json` — cross-project pointers
2. `git worktree list --porcelain` — find same-repo worktrees
3. For each worktree path, glob `pipeline/*/state.md` and read step-level detail
4. Merge, deduplicate by run-id, render table

### Integration points

- **Claude Code agents:** write pointer at pipeline start, update on each state transition
- **Codex / other CLIs:** launch via `run-agent.sh <tool> <label> [args...]` wrapper — wrapper writes and updates the pointer around the subprocess
- **Cleanup:** pointer file deleted (or status set to `done`) when pipeline completes
