# Backlog

Ideas that are worth building but not yet in a pipeline run.

---

## Subagent-Per-Role Execution

**Status:** Backlog
**Context:** All roles currently run as skill invocations inside the orchestrator's single Claude Code session. This means every role uses the orchestrator's model (`claude-opus-4-8`), `parallel_execution: true` has no effect, and `max_cost_per_run` is unenforceable. The pipeline's architecture (shared blackboard via `state.md`, explicit output contracts, tester ensemble with cross-provider roles) was designed for true subagent isolation — it's just not wired up yet.

### Problem

| Capability | Config intent | Current reality |
|---|---|---|
| Model tiering | Haiku for deployer, Sonnet for coder | All roles run on Opus (orchestrator's model) |
| Parallel execution | Independent tasks run concurrently | Sequential — one context, one thread |
| Cost governance | `max_cost_per_run: 5.00` | Unenforceable — no per-role token counts |
| Context isolation | Each role starts clean | Prior roles' reasoning accumulates in window |
| Runtime model verification | Detectable from Agent tool call | No mechanism — log.md doesn't record model used |

### Target Architecture

The orchestrator spawns each role as a true subagent via the Agent tool with:
- `model:` set from `agent-config.yml` for that role
- `prompt:` = context brief (role guide + relevant `state.md` sections)
- `isolation: worktree` for Coder roles (already supported by `worktree_isolation: true`)

The orchestrator waits for the subagent's output contract artifacts to appear in `state.md` before proceeding. All inter-role communication continues through the existing blackboard — no new state mechanism needed.

### Changes Required

**`CLAUDE.md` — Role Activation Protocol**

Add explicit subagent spawn instructions to the activation protocol. When activating a role, the orchestrator must:

1. Read `agent-config.yml` for `roles.[role].model` and `roles.[role].tools`
2. Read `steering/roles/[role].md` for the role guide
3. Compose context brief: role guide + relevant `state.md` sections (as defined per role)
4. Spawn Agent tool with `model: [from config]`, `prompt: [context brief]`
5. Write activation entry to `log.md`: `| timestamp | role | model | skill | started |`
6. Wait for output contract section in `state.md` to reach expected status

**`log.md` schema — add `model_used` column**

```
| timestamp | role | model_used | skill | status | notes |
```

This makes model usage auditable per run without requiring external tooling.

**`scripts/check_providers.py` — add model verification**

Extend the existing connectivity check to make a minimal test call to each configured model and confirm the model ID in the API response. Print a pass/fail table at session start before Gate 0.

```
Provider     Model                    Status
anthropic    claude-opus-4-8          ✓ reachable
anthropic    claude-sonnet-5          ✓ reachable
anthropic    claude-haiku-4-5-20251001 ✓ reachable
openai       gpt-5.4                  ✓ reachable
```

**`agent-config.yml` — no structural changes needed**

The model and tools fields are already per-role. The orchestrator just needs to read and use them instead of ignoring them.

### Tester Ensemble

The four tester roles (`generator_a`, `generator_b`, `consolidator`, `arbiter`) are the most important case. With subagent-per-role:

- `generator_a` (Haiku/Anthropic) and `generator_b` (GPT/OpenAI) spawn in parallel
- `consolidator` spawns after both complete, reading their outputs from `state.md`
- `arbiter` spawns on disagreements only

This is the only way the cross-provider tester ensemble actually runs concurrently with different models.

### Acceptance Criteria

- [ ] Each role activation spawns an Agent tool call with the model from `agent-config.yml`
- [ ] `log.md` records `model_used` on every role activation
- [ ] `check_providers.py` verifies all configured models are reachable before Gate 0
- [ ] Independent tasks (flagged by Architect) spawn as concurrent subagents
- [ ] Tester `generator_a` and `generator_b` run in parallel on their respective providers
- [ ] Coder activations use `isolation: worktree` when `worktree_isolation: true`
- [ ] Orchestrator reads subagent completion from `state.md` output contract section, not from subagent return value

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
