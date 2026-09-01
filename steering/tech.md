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
| Tester Generators, Tester Consolidator, Deployer | `claude-haiku-4-5-20251001` |
| Cross-provider tester | `gpt-5.4` (OpenAI) |

## Config

- `agent-config.yml` is the single source of truth — no hardcoded values in CLAUDE.md or skills
- Validate after every edit: `python scripts/validate_config.py`
- Increment `config_version` on every model or skill change — this triggers the eval gate

## Pipeline state

- Each run lives in `pipeline/[run-name]/` — tracked in git
- `state.md` and `log.md` are append-only — never overwrite prior sections
- Worktree isolation: each parallel Coder activation writes to `.worktrees/[run-name]/` exclusively

## Providers

Supported: `anthropic`, `openai`, `google`, `mistral`  
Configured via environment variables — see `.env.example`
