# agentzero installer

Deploy the autonomous multi-agent SDLC pipeline into any project — new (greenfield) or existing (brownfield).

## Prerequisites

| Requirement | Notes |
|---|---|
| [Claude Code](https://claude.ai/code) | The pipeline runs inside Claude Code sessions |
| Python 3.10+ | For validation scripts |
| Git | Branches, worktrees, and PR workflow |
| [GitHub CLI (`gh`)](https://cli.github.com) | PR creation and merge (`gh auth login` required) |
| Docker or Podman | For sandboxed test execution (optional — falls back to process isolation) |
| Anthropic API key | Required — primary model provider |
| OpenAI API key | Required for `tester_generator_b` (cross-provider tester) |

---

## Install

### One-liner (no clone needed)

```bash
curl -fsSL https://raw.githubusercontent.com/plaktoz/agentzero/main/dist/install.sh | bash -s -- my-project
```

Replace `my-project` with your project directory name. The directory will be created if it doesn't exist.

To install into an existing directory:

```bash
curl -fsSL https://raw.githubusercontent.com/plaktoz/agentzero/main/dist/install.sh | bash -s -- /path/to/existing-project
```

### From a local clone

```bash
git clone https://github.com/plaktoz/agentzero.git
./agentzero/dist/install.sh my-project
```

Or into the current directory:

```bash
./agentzero/dist/install.sh
```

The installer detects whether your project is greenfield or brownfield and adjusts automatically.

### What gets installed

```
your-project/
  .agents/skills/         ← pipeline skills (Analyst, Architect, Coder, Tester, etc.)
  .claude/
    CLAUDE.md             ← Orchestrator instructions (appended if CLAUDE.md exists)
    settings.json         ← permission allowlist for standard pipeline ops
    skills -> ../.agents/skills   ← symlink for Claude Code skill loading
  CONTEXT.md              ← shared pipeline vocabulary (pre-filled; add project terms via /proj-start)
  agent-config.yml        ← pipeline configuration (models, cost cap, retry limits)
  .env.example            ← API credential template
  steering/               ← orchestrator context: product.md, tech.md, structure.md, backlog.md
    roles/                ← per-role mandate and output contract (one .md per role)
  knowledge_base/         ← lessons, guardrails, guardrail candidates, failure patterns
  eval/                   ← golden tests per role, scores log
  pipeline/               ← run state (state.md, log.md per run) — starts empty
  scripts/                ← validate_config.py, check_providers.py, call_provider.py, requirements.txt
```

### Brownfield behaviour

Existing files are never overwritten:
- `agent-config.yml` — skipped if present (compare with source for new fields)
- `.agents/skills/[name]` — individual skills skipped if the directory already exists
- `CLAUDE.md` — agentzero block appended if the file exists and block is not already present
- `.claude/settings.json` — skipped if present
- `CONTEXT.md` — skipped if present
- `knowledge_base/`, `eval/`, `pipeline/` — skipped if directory exists

---

## Configure

**1. API credentials** — copy the template and fill in your keys:

```bash
cp .env.example .env
# edit .env
```

Required variables:

```
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_BASE_URL=https://api.anthropic.com     # or your proxy
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.openai.com/v1        # or your proxy
```

**2. `agent-config.yml`** — key settings to review before first run:

| Field | Default | What to set |
|---|---|---|
| `cost_governance.max_cost_per_run` | `5.00` | Your budget cap per pipeline run (USD) |
| `pipeline.max_tester_retries` | `3` | TDD retry limit before human escalation |
| `pipeline.worktree_isolation` | `true` | Use git worktrees for parallel features |
| `test_env.runtime` | `docker` | `docker` / `podman` / `none` |
| `test_env.isolation` | `auto` | `auto` / `containerized` / `process` |
| `deploy.target_environment` | `local` | `local` / `staging` / `production` |

**3. Validate**:

```bash
python3 -m venv .venv && .venv/bin/pip install -r scripts/requirements.txt
python3 scripts/validate_config.py
python3 scripts/check_providers.py
```

---

## First run

Open the project in Claude Code, then:

| You have… | Command |
|---|---|
| A new project, nothing built yet | `/proj-start` |
| An existing project, one feature to add | `/proj-new-feature` |
| An existing project, multiple related features | `/proj-epic` |
| An existing bug to fix | `/proj-fix-bug` |

---

## Pipeline overview

```
User input
    │
    ▼
Orchestrator ──── Gate 0: plan approval ────────────────────┐
    │                                                         │ human
    ▼                                                         ▼
Analyst (to-spec / PRD) ─── Gate 1: spec approval ──────────┤
    │                                                         │ human
    ▼                                                         │
Designer (optional, UI) ─── Gate 2: design approval ────────┤
    │                                                         │ human
    ▼
Architect (codebase-design)
    │
    ▼
Tester Ensemble Phase 1  ← writes tests from spec (TDD)
    │  generator_a + generator_b (parallel, cross-provider)
    │  consolidator → arbiter
    ▼
Coder (implement / diagnosing-bugs)
    │  works in isolated git worktree
    ▼
Tester Ensemble Phase 2  ← runs tests against code
    │
    ▼
Quality Gate (autonomous) ─── FAIL → back to Coder
    │  PASS
    ▼
Build Verifier (autonomous) ← install check + smoke tests
    │  PASS
    ▼
Gate 3: test sign-off ─────────────────────────────────────── human
    │
    ▼
Release Documenter → signoff_package.md
    │
    ▼
Deployer ── merges PR, runs deploy
    │
    ▼
Delivery Manager (autonomous) ← retro.md (token/cost/duration report)
```

### Key constraints (all configurable in `agent-config.yml`)

| Constraint | Default | Trigger |
|---|---|---|
| TDD + quality gate retries | 3 | Escalate to human |
| Spec revision rounds | 2 | Escalate to human |
| Design revision rounds | 2 | Escalate to human |
| Code review cycles | 2 | Escalate to human |
| Cost cap per run | $5.00 | Halt + escalate |

---

## Upgrade

To get updated skills after a new agentzero release:

```bash
curl -fsSL https://raw.githubusercontent.com/plaktoz/agentzero/main/dist/install.sh | bash -s -- /path/to/your-project
```

The installer only adds new skills — it never overwrites existing ones. To force-update a specific skill, delete it first:

```bash
rm -rf /path/to/your-project/.agents/skills/proj-protocol
curl -fsSL https://raw.githubusercontent.com/plaktoz/agentzero/main/dist/install.sh | bash -s -- /path/to/your-project
```

---

## Uninstall

```bash
# from a local clone:
./dist/uninstall.sh /path/to/your-project
```

Removes: `.agents/skills/`, `.claude/skills` symlink, `.worktrees/`
Prompts before removing: `pipeline/`, `eval/`, `knowledge_base/`, `steering/`
Always kept: `agent-config.yml`, `.env.example`, `scripts/`, your source code

---

## Customising skills

Skills are plain Markdown files in `.agents/skills/[skill-name]/SKILL.md`. Edit them directly in your project — changes affect only that project and are not overwritten by upgrades unless you explicitly delete the skill directory.

To add a project-specific skill:

```bash
mkdir -p .agents/skills/my-custom-skill
cat > .agents/skills/my-custom-skill/SKILL.md << 'EOF'
# My Custom Skill
...
EOF
```

It will automatically be available in Claude Code via `/my-custom-skill`.

---

## Architecture notes

- **Orchestrator** — the Claude Code session you interact with. Coordinates all other roles. Never writes code directly.
- **Blackboard** — `pipeline/[run-name]/state.md` is append-only shared state. All roles read from and write to it via the Orchestrator.
- **Subagent dispatch** — Anthropic-provider roles are spawned via the Agent tool with `model:` set from `agent-config.yml`. Cross-provider roles (e.g. `tester_generator_b`) are dispatched via `scripts/call_provider.py`.
- **Worktree isolation** — each parallel feature gets its own `git worktree` so Coder agents never share a working directory.
- **Knowledge base** — lessons extracted from failed runs are distilled into tagged rules and injected into future role briefs automatically.
- **Eval gate** — before any model or prompt change rolls out, golden tests for affected roles must pass scoring thresholds.
