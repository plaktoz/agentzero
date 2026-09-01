# Structure

## Top-level layout

```
agent-config.yml          — central config; models, roles, tools, skills, deploy settings
CLAUDE.md                 — orchestrator identity and command reference
steering/                 — always-loaded context files (this directory)
  product.md              — goals, scope, non-goals
  tech.md                 — model IDs, stack, constraints
  structure.md            — this file; file layout and naming rules
  roles/                  — per-role mandate, output contract, known failure modes
pipeline/                 — one subdirectory per run; git-tracked
  [run-name]/
    state.md              — shared blackboard; append-only
    log.md                — execution log; one row per agent action; append-only
    design-preview.html   — generated UI mockup (UI tasks only)
knowledge_base/           — accumulated lessons and guardrails
  index.md                — entry point; every distilled file linked from here
  guardrails.yaml         — human-ratified hard rules; read at session start
  guardrails_candidates.md — lessons awaiting human ratification
  failure-patterns.md     — aggregate table; one row per distinct failure pattern
  lessons/
    raw/                  — one file per failure event; append-only
    distilled/            — generalized rules; one file per pattern
eval/                     — prompt/config versioning and scoring
  config-history/         — immutable snapshots: v[n].yml per config version
  roles/                  — golden tests per role
  scores-log.md           — append-only eval results
scripts/
  validate_config.py      — validates agent-config.yml structure
  check_providers.py      — live connectivity check for all configured providers
```

## Naming conventions

- Run names: `[type]-[slug]` — e.g. `feat-dark-mode`, `fix-auth-bug`, `refactor-api-layer`
- Lesson files: lowercase, hyphenated, descriptive — e.g. `coder-scope-creep-on-refactor.md`
- Raw event files: `[YYYY-MM-DD]-[run-name]-[failure-type].md`
- Eval snapshots: `v[config_version].yml`

## Append-only rules

These files are **never** overwritten or edited after creation:
- `pipeline/[run-name]/log.md`
- `knowledge_base/lessons/raw/*.md`
- `eval/config-history/*.yml`
- `eval/scores-log.md`

Status fields in `pipeline/[run-name]/state.md` (gate statuses, task table statuses) are the **only** fields updated in-place.
