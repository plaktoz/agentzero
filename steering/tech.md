# Tech

## Runtime

- Agent runtime: Claude Code CLI
- Shell: zsh (macOS) / bash (Linux)
- Python 3.9+ required for validation scripts (`scripts/validate_config.py`, `scripts/check_providers.py`)

## Model IDs (exact strings — do not abbreviate)

| Role tier | Model ID |
|---|---|
| Orchestrator, Architect | `claude-opus-4-8` |
| Analyst, Designer, Coder, Tester Arbiter, Release Documenter | `claude-sonnet-5` |
| Tester Generators, Tester Consolidator, Deployer | `claude-haiku-4-5` |
| Cross-provider tester | `gpt-5.4` (OpenAI) |

## Config

- `agent-config.yml` is the single source of truth — no hardcoded values in CLAUDE.md or skills
- Validate after every edit: `python scripts/validate_config.py`
- Increment `config_version` on every model or skill change — this triggers the eval gate

## Pipeline state

- Each run lives in `pipeline/[run-name]/` — tracked in git
- `state.md` and `log.md` are append-only — never overwrite prior sections
- Worktree isolation: each parallel Coder activation writes to `.worktrees/[run-name]/` exclusively

### log.md schema

Each activation appends exactly one row to `pipeline/[run]/log.md` with the following columns:

| timestamp | run | role | model_used | provider | status | detail |
|---|---|---|---|---|---|---|

| Column | Format | Description |
|---|---|---|
| `timestamp` | ISO 8601 UTC e.g. `2026-09-01T14:23:05Z` | Wall-clock time the activation started |
| `run` | string | Pipeline run directory name (matches `pipeline/[run]/`) |
| `role` | string | Role name as declared in `agent-config.yml` |
| `model_used` | string | Exact model string used for this activation (from `agent-config.yml`) |
| `provider` | string | `anthropic` \| `openai` \| `google` \| `mistral` |
| `status` | string | `ok` \| `error` \| `skipped` |
| `detail` | string | Skill invoked (ok), error message (error), or skip reason (skipped) |

Orchestrator writes Path A log rows; `call_provider.py` writes Path B log rows.

## Providers

Supported: `anthropic`, `openai`, `google`, `mistral`  
Configured via environment variables — see `.env.example`
