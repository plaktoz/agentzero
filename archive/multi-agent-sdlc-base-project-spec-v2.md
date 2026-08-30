# Multi-Agent SDLC Base Project — Spec for Bootstrap (v2)

## Purpose
Build a base project template for a role-based, multi-LLM agent system that handles the full software delivery lifecycle: greenfield development, brownfield development, change requests, and fixes. Language-agnostic. Self-improving via a compounding lessons-learned knowledge base.

This doc is meant to hand to a coding agent to scaffold the initial project structure and stub implementations.

---

## 1. Roles and Tasks

| Role | Primary Task | Key Outputs |
|---|---|---|
| **Business Analyst (BA)** | Gather requirements, clarify ambiguity | `requirements.md`, `acceptance_criteria.md`, `open_questions.md` |
| **Architect** | System design; decomposes project into **features** with dependency annotations | `architecture.md`, `adr/*.md`, `interface_contracts/*`, `feature_breakdown.json` |
| **Designer** *(optional)* | UI/UX design; activated only when task has a UI/UX component | `design-preview.html`, design notes |
| **Developer** | Implementation (language-adapted via skills); decomposes assigned feature into tasks; owns DB migrations | Code, PRs, `task_breakdown.json`, `db/migrations/*.sql` |
| **Tester (ensemble)** | Generate + consolidate test cases across multiple LLMs; run automated tests and feed failures back to Developer | `test_plan.md`, test files, structured failure reports |
| **Deployer** | Execute deployment, pre-deploy gate checks, run pending migrations against target environment | Deployment logs, gate check results |
| **Release Documenter** | Compile all stage outputs into a sign-off-ready package; hard-block if mandatory artifacts are missing | `signoff_package.md` |
| **Lesson Pipeline** *(supporting, not in main SDLC chain)* | Observe → extract → validate → distill lessons from failed or escalated runs | Raw + distilled entries in `/knowledge_base/lessons/` |

Notes:
- **DBA role is merged into Developer.** Schema design and migrations are the Developer's responsibility, enforced via the DB migrations conventions in §12.
- **End User gate is external.** Human sign-off happens outside the pipeline. The Release Documenter produces the sign-off package; approval is a manual process.

Each agent config is self-describing (provider/model/key are per-agent, not global):
```yaml
role: architect
provider: anthropic
model: claude-opus-5
api_key_ref: ${ANTHROPIC_API_KEY_ARCHITECT}   # never inline raw keys — env var or secrets manager
fallback:
  provider: openai
  model: gpt-5.x
  api_key_ref: ${OPENAI_API_KEY}
inputs: [requirements.md, existing_codebase (brownfield)]
outputs: [architecture.md, adr/*.md, interface_contracts/*, feature_breakdown.json]
skills_allowed: [codebase_scanner, dependency_graph, adr_template]
handoff_to: developer
```
Model choice per role maps to cognitive demand — Opus-tier for BA/Architect (ambiguity, tradeoffs), lighter/faster models for mechanical stages (deployer, simple fixes). Use LiteLLM (or similar) as the abstraction layer so provider/model/key is fully config-driven per agent, with automatic fallback on error/rate-limit.

---

## 2. Greenfield vs. Brownfield vs. CR/Fix

Same roles and skills across all three; differs in entry point:

- **Greenfield**: BA → Architect → Designer* → Dev → Tester → Deployer (linear backbone; *Designer inserted after Architect when task has UI/UX component)
- **Brownfield**: Prepend a `context_synthesis` step (codebase scan → "current state" doc) attached to every downstream agent's context, before BA/Architect work begins
- **CR / Fix**: Fast-path option that skips BA/Architect for small, low-risk changes — a routing decision, not a separate codebase (see §7)

---

## 3. Decomposition — Two Levels

**Level 1 — Architect decomposes the project into features** (business/domain-capability granularity):
```json
{
  "features": [
    {"id": "checkout_flow", "depends_on": [], "domain": ["frontend", "backend", "db"]},
    {"id": "user_notifications", "depends_on": [], "domain": ["backend"]},
    {"id": "admin_reporting", "depends_on": ["checkout_flow"], "domain": ["backend", "db"]}
  ]
}
```

**Level 2 — Task planner skill decomposes each feature into tasks** (mechanical granularity: `frontend_component`, `backend_endpoint`, `schema_migration`, etc.), invoked per-feature rather than reasoned over by the architect for the whole project:
```
/skills/task_planner/
  decompose(feature_spec) → task_breakdown.json   (same schema style as feature_breakdown.json)
```

The orchestrator composes both levels into one executable DAG — a feature is effectively a subgraph of tasks. Sequential vs. parallel execution is decided the same way at both levels: independence = no overlap in `depends_on`.

---

## 4. Tester — Multi-LLM Ensemble

Two generator models (cross-provider for perspective diversity) + one arbiter:

```
generators: [generator_a (claude-haiku, anthropic), generator_b (gpt-4o-mini, openai)]
arbiter: claude-sonnet   # invoked on disagreement; escalates to human on critical unresolved findings
consolidator: claude-haiku   # deduplicates, ranks by severity, produces unified test plan
```

- **Cross-provider generators**: `generator_a` on Anthropic Haiku, `generator_b` on OpenAI gpt-4o-mini. Different providers introduce perspective diversity that same-provider sampling cannot replicate.
- **Deduplication**: force structured output from every generator, not free-form text:
```json
{
  "target_function": "calculate_discount",
  "input_equivalence_class": "negative_number",
  "expected_behavior": "raises ValueError",
  "test_code": "...",
  "severity": "medium"
}
```
  Dedup on the semantic key `(target_function, input_equivalence_class, expected_behavior)`, not on text/name similarity.
- **Consolidator agent**: dedups, flags disagreements for the arbiter, ranks by severity, outputs unified `test_plan.md` + test files.
- **Arbiter escalation**: the arbiter resolves low/medium severity disagreements autonomously. For `critical` severity findings where generators disagree and the arbiter cannot confidently resolve, it escalates to a human before the finding blocks a release.
- Full ensemble runs on every task — the additional cost of `generator_b` and arbiter analysis is justified by the coverage gain.

### Automated Test → Fix Loop
Deterministic, not LLM-driven at execution:
```
developer → test_runner (actual execution)
  → fail → structured failure (traceback, assertion, code region) fed back to developer
  → fix attempt → re-run
  → repeat up to max_retries (e.g. 3)
  → still failing → escalate (human, stronger model, or architect if failure suggests design flaw)
```
Log every fix attempt into the lessons pipeline — recurring failures on the same pattern are what the KB should catch earlier next time.

---

## 5. Skills Layer

Skills are role-agnostic, composable, reused across roles. Prefer existing tooling over custom builds:

```yaml
# /skills/registry.yaml
codebase_scanner: { source: custom }
git_operations: { source: mcp, url: <github-mcp-server> }
test_runner_python: { source: cli_wrapper, tool: pytest }
schema_introspector: { source: mcp, url: <postgres-mcp-server> }
```

- Prefer MCP servers where available (GitHub, DB introspection, CI/CD, ticketing) over reimplementing.
- Language-agnosticism lives here, not in the agent layer: `/skills/lang_adapters/{python,java,dotnet,js}/` each implementing the same interface (`lint()`, `build()`, `test()`, `run_migrations()`).
- Only build custom skills for genuinely domain-specific logic (dedup/consolidation, retrospective generation) with no off-the-shelf equivalent.

---

## 6. Parallel Execution Infrastructure

### Git worktrees per feature (lazy creation)
Worktrees are created only when parallel tasks would overlap — the orchestrator checks file surfaces before deciding:
```
conflict_checker.check_overlap(feature_a, feature_b)
  → overlap detected → create worktrees
  → no overlap → shared working directory, no worktree needed
```
```
git worktree add ../worktrees/checkout_flow feature/checkout_flow
```
```
/skills/worktree_manager/
  create(feature_id, base_branch) → worktree_path
  cleanup(feature_id)   # after merge or abandonment
```

### Conflict resolution
When the conflict-checker detects overlap between parallel branches:
- **File/interface conflicts**: auto-serialize — run the conflicting branches sequentially instead of in parallel, no escalation needed.
- **DB schema conflicts** (both branches produce migrations for the same table): escalate to Architect — the feature breakdown was wrong and needs re-decomposition.

### Test environment isolation
Config-driven via `test_env.isolation` in `agent-config.yml`:

| Value | Behaviour |
|---|---|
| `auto` | Detect Docker/Podman at runtime; use `containerized` if available, fall back to `process` |
| `containerized` | Docker/Compose per feature, dynamic ports — full isolation |
| `process` | Port pool + named databases within one DB server — no containers required |
| `sequential` | No isolation; DB-touching tasks serialized |

**Process isolation (recommended default):**
```yaml
test_env:
  isolation: auto
  runtime: docker        # docker | podman | none
  port_pool:
    app: [3001, 3099]
    db: [5433, 5499]
```
Each parallel feature is assigned the next free port from the pool and a feature-scoped DB name (e.g. `test_db_checkout_flow`) within the same DB server instance. Named databases are lightweight — creating/dropping takes milliseconds, and a single Postgres instance handles 20+ concurrent named DBs without issue.

**DB setup sequence** (per feature, before tests run):
1. `test_env_manager` creates named DB
2. Runs all files in `db/migrations/` in order
3. Runs `db/seeds/base.sql` (stable reference data only)
4. Hands DB URL to test runner

Tests own their own transactional data — each test creates what it needs and tears down after. `db/seeds/base.sql` is for reference data that every feature depends on (lookup tables, config rows, etc.).

**Stale cleanup:** `test_env_manager` appends each created DB to `db/migrations/_test_envs.log`. On every new run start, orchestrator reads the log and drops any entries that did not complete cleanup.

---

## 7. Routing — Hybrid (not fully hardcoded, not fully autonomous)

Two active layers + one implicit:

1. **Deterministic backbone** — config-driven rules, not buried in code logic:
```yaml
# /config/routing_rules.yaml
- condition: "change_type == 'CR' and lines_changed < 20 and no_schema_change"
  route: [developer, tester, deployer]
- condition: "touches_database == true"
  route: [ba, architect, developer, tester_ensemble, deployer, release_documenter]
- condition: "risk_score > 0.7"
  route: [ba, architect, designer, developer, tester_ensemble, deployer, release_documenter]

parallel_failure_policy:
  cr_fix: proceed        # independent branches continue on partial failure
  full_release: halt     # all branches must succeed
```
2. **LLM routing (implicit)** — mid-flow adaptive decisions (retry loops, "test failure suggests design flaw → escalate to architect") handled by the orchestrator's own reasoning, not a separate component.
3. **Hard guardrails** — non-negotiable checks no router can override:
```yaml
# /config/guardrails.yaml
- "database-touching changes must include migration files in db/migrations/"
- "risk_score > 0.8 must include full tester ensemble"
- "release_documenter must hard-block on missing mandatory artifacts"
```
Guardrails may be informed by the lessons KB, but promotion of a lesson into a hard guardrail requires human ratification — candidates accumulate in `guardrails_candidates.md` and are reviewed on-demand, not on a forced cadence.

- Cap max-parallel-branches (cost/rate-limit control), queue the rest.
- Run `conflict_checker` on parallel outputs before merging (see §6).

---

## 8. Self-Improvement — Lessons Built on Failure, Compounding

The lessons pipeline activates only on **failures and escalations** — not on every successful run:

```
/agents/lesson_pipeline/
  observer.yaml     # consumes structured execution trace from observability log
  extractor.yaml    # LLM pass: finds causal patterns — rejections, retries, ensemble disagreements, human overrides
  validator.yaml    # filters one-off noise from genuinely generalizable patterns; flags contradictions with existing rules
  distiller.yaml    # merges validated lessons into the distilled rule set
```

Two-layer KB:
```
/knowledge_base/lessons/
  raw/         # append-only, timestamped, every retrospective as-is
  distilled/   # periodically merged/generalized rules, versioned, tagged by role/language/project_type/failure_type
```

**Retrieval at agent-start (tag-based):** orchestrator filters distilled lessons by matching tags (`role`, `language`, `failure_type`) and injects the top-K matches into the agent's context. No vector DB required — tag filtering on a bounded distilled set is sufficient.

**Guardrail promotion:** the lessons pipeline appends candidate guardrails to `guardrails_candidates.md`. Promotion to `guardrails.yaml` requires human ratification — reviewed on-demand, no forced cadence.

Distillation prevents unbounded linear growth. Lessons can freely update the advisory/distilled layer autonomously. Promotion into hard guardrails always requires human sign-off.

---

## 9. Documentation & Human Sign-Off

Dedicated role: **`release_documenter`**, positioned just before Gate 3 (the human deploy-approval gate).

```yaml
role: release_documenter
model: claude-sonnet-5
inputs: [requirements.md, architecture.md, test_plan.md, test_results, deployment_plan]
outputs: [signoff_package.md]
checks: [completeness_check]
handoff_to: human_gate_3
```

**Hard block on completeness gaps.** The Release Documenter checks which roles were activated (from `pipeline-state.md`) and verifies that every expected artifact for that flow type exists. If a mandatory artifact is missing, the pipeline halts — it does not produce a partial sign-off package and flag it for human review. The gap must be filled before Gate 3 is presented.

Mandatory artifacts by flow type:
- **Greenfield / large CR**: spec, architecture, test plan, test results, deployment plan
- **Small CR fast-path**: test results only
- **Bug fix**: spec, test plan, test results

**Human sign-off is external.** There is no End User agent — the `signoff_package.md` is handed to a human for approval outside the pipeline. The pipeline does not model or simulate this step.

---

## 10. Best Practices / Non-Negotiables

Ranked roughly by "will bite you first if skipped":

1. **Observability** — structured logging per agent call from day one:
   `timestamp, role, model, provider, handoff_from, handoff_to, action, artifact, input_tokens, output_tokens, cost, status`. Everything else (lessons pipeline, cost governance, debugging routing) depends on this existing.
2. **Checkpointing / resumability** — persist state after each stage; don't force a full restart on failure or a multi-day human sign-off delay.
3. **Cost governance** — hard budget cap per run in `agent-config.yml` under `cost_governance.max_cost_per_run`. Orchestrator checks accumulated cost before activating each role and halts + escalates if the cap would be exceeded. Prevents runaway retry loops and unexpected parallel fan-out costs.
4. **Intermediate human checkpoints**, not just final sign-off — configurable by risk level (catching a bad architecture decision is cheaper than catching it after 4 downstream roles built on it).
5. **Git/PR-based workflow** — agents never commit directly; every change goes through a real PR/diff from its feature worktree, reviewable in the sign-off package, with natural rollback via revert.
6. **Sandboxed execution** — all agent-executed code (test runs, builds) in isolated/ephemeral environments, never against production-adjacent infra.
7. **Data governance** — pre-flight secrets/PII scanner before any brownfield code/doc leaves the network to an external LLM API; decide which stages must use local/self-hosted models for sensitive codebases.
8. **Prompt/config versioning + eval set** — version every agent config; maintain a golden test set per role with automated scoring (structural + LLM-as-judge + execution-based), re-run on any prompt/model change before rollout.

---

## 11. DB Migrations

Developer owns schema changes. No separate DBA role.

**Convention:**
- Migration files live in `db/migrations/`
- Naming: `YYYYMMDD-NNN__description.sql` (e.g. `20260829-001__add_users_table.sql`)
  - Date provides human context; sequential counter within the day handles same-day parallel branches
  - Parallel branches that both generate `20260829-001__...` create a naming conflict — caught by the conflict-checker at merge time (DB schema conflict → escalate to Architect)
- Format: plain SQL — no tool dependency (Liquibase/Flyway/Alembic not required)

**Who runs migrations:**
- **Developer (Coder)**: runs pending migrations against the feature's test DB during the TDD loop, so tests run against the correct schema
- **Deployer**: runs pending migrations against the target environment after Gate 3 approval, before starting the application

**Applied tracking:** `db/migrations/_applied.log` — append-only list of applied filenames. Both Coder and Deployer consult this before running.

**Rollback strategy:** forward-only. If a migration must be undone, write a new corrective migration (e.g. `20260829-002__revert_add_column.sql`). This preserves an honest audit trail and avoids the fragility of `DOWN` scripts.

**Deprecated column cleanup:** when a column is deprecated but not yet dropped (expand/contract pattern), the Developer must add an entry to `db/migrations/_deprecated.md`:
```
| Column | Table | Deprecated in | Target cleanup date | Status |
|---|---|---|---|---|
| legacy_token | users | 20260829-003 | 2026-11-01 | pending |
```
The Deployer scans `_deprecated.md` on every run and warns if any entry is past its target cleanup date.

---

## 12. Proposed Base Project Structure

```
/agents/
  business_analyst.yaml
  architect.yaml
  designer.yaml              # optional role — UI/UX tasks only
  developer.yaml
  tester/
    generator_a.yaml         # claude-haiku (anthropic)
    generator_b.yaml         # gpt-4o-mini (openai)
    arbiter.yaml             # claude-sonnet — resolves disagreements; escalates critical to human
    consolidator.yaml        # claude-haiku — deduplicates, ranks by severity
  deployer.yaml
  release_documenter.yaml
  lesson_pipeline/           # activates on failures and escalations only
    observer.yaml
    extractor.yaml
    validator.yaml
    distiller.yaml

/orchestration/
  classifier.py          # LLM-assisted: tags risk, type, size, domains touched
  rules_router.py        # deterministic backbone routing (config-driven)
  guardrails.py          # hard-coded non-negotiable checks, overrides everything
  dag_builder.py         # dynamic graph from feature + task dependencies
  executor.py            # parallel execution engine, cap-configurable
  conflict_checker.py    # detects overlap between "independent" parallel outputs
  greenfield_flow.py
  brownfield_flow.py
  cr_fix_flow.py

/skills/
  registry.yaml              # maps skill name -> source (mcp / cli_wrapper / custom)
  codebase_scanner/
  schema_introspector/
  test_runner/
  task_planner/              # feature -> task decomposition (Level 2)
  worktree_manager/          # lazy: create worktrees only on file overlap
  test_env_manager/          # process or containerised isolation, port pool, named DBs
  lang_adapters/{python,java,dotnet,js}/
  documentation_generator/
  context_synthesis/         # brownfield "current state" builder

/knowledge_base/
  lessons/
    raw/
    distilled/               # tagged by role/language/project_type/failure_type
  adr/
  guardrails_candidates.md   # candidate guardrails awaiting human ratification

/db/
  migrations/
    _applied.log             # append-only: filenames of applied migrations
    _deprecated.md           # columns deprecated but not yet dropped
    _test_envs.log           # stale test DB cleanup tracker
  seeds/
    base.sql                 # stable reference data only (lookup tables, config rows)

/model_router.py             # LiteLLM-based, per-agent provider/model/key config
/config/
  role_model_map.yaml
  routing_rules.yaml         # deterministic backbone + parallel_failure_policy
  guardrails.yaml            # hard constraints (human-ratified only)
  risk_policy.yaml           # fast-path vs full-ensemble thresholds

/eval/
  golden_test_sets/          # per-role: input.md + golden_output.md + score.yaml
    analyst/
    architect/
    designer/
    developer/
    tester/
    deployer/
    release_documenter/
```

---

## 13. Resolved Design Decisions

All formerly open decisions (§12 in v1) are now resolved:

| Decision | Resolution |
|---|---|
| CR/fix fast-path | Skip BA/Architect when `lines_changed < 20` and `no_schema_change` — config-driven in `routing_rules.yaml` |
| Tester disagreement handling | Arbiter resolves low/medium autonomously; escalates `critical` unresolved findings to human |
| Conflict-checker overlaps | File/interface conflicts: auto-serialize. DB schema conflicts: escalate to Architect |
| Schema conflicts between parallel features | Caught by conflict-checker at merge; DB schema conflicts escalate to Architect for re-decomposition |
| Partial failure in parallel DAG | Config-driven: `cr_fix: proceed`, `full_release: halt` in `routing_rules.yaml` |
| Guardrail promotion cadence | On-demand — candidates accumulate in `guardrails_candidates.md`, no forced review schedule |
| Release Documenter completeness gaps | Hard block — pipeline halts if mandatory artifacts are missing; mandatory set varies by flow type |
| End User role | Removed — human sign-off is external, not modelled in the pipeline |
| DBA role | Merged into Developer — DB migrations follow the conventions in §11 |
| Designer role | Added as optional role, inserted between Architect and Developer |
