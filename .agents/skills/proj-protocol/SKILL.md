# Pipeline Protocol Reference

This is the shared protocol reference for all `proj-*` skills. Read this once per session before executing any pipeline skill.

---

## Pre-flight Checks

Run these **before activating the first role** on every pipeline run.

**1. Data governance scan** — invoke the `data-governance` skill against all source files the pipeline will touch. Do not proceed until it returns clean or the user approves findings.

**2. Cost check** — read `cost_governance.max_cost_per_run` from `agent-config.yml`. Confirm the run budget is non-zero before starting. See Cost Governance section for per-role checks.

**3. Eval gate** — if `agent-config.yml` was modified since the last pipeline run (check via `git diff HEAD -- agent-config.yml`), invoke the `eval` skill before starting. Do not start a pipeline run with an unvalidated config change.

---

## Pipeline Folder Structure

Each pipeline run owns its own folder:

```
pipeline/
  feat-dark-mode/
    state.md
    design-preview.html   ← only if Designer was activated
  fix-auth-bug/
    state.md
pipeline-log.md           ← cross-run audit trail, project root
```

Run name conventions:
- Feature: `feat-[slug]` (e.g. `feat-dark-mode`)
- Bug fix: `fix-[slug]` (e.g. `fix-null-pointer`)
- Refactor: `refactor-[slug]` (e.g. `refactor-api-layer`)

Slugify by lowercasing the task description, replacing spaces with hyphens, keeping only alphanumeric and hyphens, truncating to 40 chars.

---

## Git/PR Workflow Rules

Agents never commit directly to the main branch. Every code change goes through a feature branch and PR.

**Coder (on first activation for a run):**
1. Create a feature branch from the current default branch:
   `git checkout -b [run-name]` (e.g. `git checkout -b feat-dark-mode`)
2. All commits go to this branch — never to `main` or `master`
3. Commit message format: `[run-name]: [what changed]`
4. After writing code: `git push -u origin [run-name]`
5. Open a PR: `gh pr create --title "[run-name]" --body "Pipeline run: pipeline/[run-name]/state.md"`
6. Write the PR URL to `state.md` under `## PR`:
   ```markdown
   ## PR
   **URL:** [pr url]
   **Branch:** [run-name]
   **Status:** open
   ```

**On Coder retry:** commit each attempt as a new commit on the same branch — do not amend or force-push.

**Release Documenter:** include the PR URL and diff summary in `signoff_package.md`. The PR diff is the reviewable artifact.

**Deployer:** after Gate 3 approval, merge the PR via `gh pr merge [pr-url] --squash --delete-branch`, then run deploy steps. Do not merge before Gate 3.

**Rollback:** if a deployment must be reverted, use `git revert` — never `git reset`. Write the revert commit to a new `fix-revert-[run-name]` run.

---

## Blackboard Protocol

`pipeline/[run-name]/state.md` is **append-only** with one exception:
- Never overwrite or delete prior sections
- After a role completes, copy its output into the correct section of `state.md`
- **Exception — status fields only:** Gate status fields and task table status columns may be updated in-place. All other content is append-only.

Always read `state.md` before activating any role. Always pass the relevant sections in the role's context brief.

---

## Logging Protocol

After every agent action, append one row to `pipeline/[run-name]/log.md`. This is the structured observability record — the cost governance check, lessons pipeline, and debugging all read from it.

**Log format:**
```
| Timestamp | Role | Model | Provider | Handoff From | Handoff To | Action | Artifact | Input Tokens | Output Tokens | Cost (USD) | Status |
```

**Field rules:**
- `Timestamp` — `YYYY-MM-DD HH:MM`
- `Role` — exact role name from `agent-config.yml`
- `Model` — from `agent-config.yml roles.[role].model`
- `Provider` — from `agent-config.yml roles.[role].provider`
- `Handoff From` — role that completed immediately before this one (`—` for Orchestrator at run start)
- `Handoff To` — role that will be activated next (`—` if pending gate or run end)
- `Action` — what the role did
- `Artifact` — `state.md#section` or file path written
- `Input Tokens` — reported by the API response if available; otherwise use the model estimate from the Cost Reference table below
- `Output Tokens` — reported by the API response if available; otherwise use the model estimate
- `Cost (USD)` — `(input_tokens / 1_000_000 × input_price) + (output_tokens / 1_000_000 × output_price)` — use Cost Reference table for prices
- `Status` — `complete | failed | escalated | skipped`

**Example:**
```
| 2026-08-16 09:12 | Orchestrator | claude-opus-4-8 | anthropic | — | analyst | Created execution plan | pipeline/feat-dark-mode/state.md#gate-0 | 1200 | 340 | 0.03 | complete |
| 2026-08-16 09:15 | Analyst | claude-sonnet-5 | anthropic | orchestrator | architect | Wrote spec via to-spec | pipeline/feat-dark-mode/state.md#gate-1 | 4800 | 1200 | 0.03 | complete |
| 2026-08-16 09:45 | Tester Ensemble | claude-haiku-4-5 | anthropic | coder | orchestrator | Ran tests (retry 2/3) | pipeline/feat-dark-mode/state.md#test-results | 3200 | 800 | 0.004 | failed |
```

Create `log.md` with a header row when the run folder is first created:
```markdown
# Pipeline Log: [run-name]

| Timestamp | Role | Model | Provider | Handoff From | Handoff To | Action | Artifact | Input Tokens | Output Tokens | Cost (USD) | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|
```

---

## Cost Reference Table

Use these prices when API-reported token counts are unavailable. Values are per 1M tokens.

| Model | Input ($/MTok) | Output ($/MTok) |
|---|---|---|
| claude-opus-4-8 | 15.00 | 75.00 |
| claude-sonnet-5 | 3.00 | 15.00 |
| claude-haiku-4-5 | 0.80 | 4.00 |
| gpt-4o-mini | 0.15 | 0.60 |
| gpt-5.4 | 2.00 | 10.00 |

Update this table whenever models or pricing change in `agent-config.yml`.

---

## Cost Governance

Read `cost_governance.max_cost_per_run` from `agent-config.yml` at the start of every pipeline run.

**Before activating any role**, the Orchestrator must:

1. Sum the `Cost (USD)` column in `pipeline/[run-name]/log.md` to get `accumulated_cost`
2. Estimate the cost of the role about to be activated:
   - Use the model's output price from the Cost Reference table
   - Conservative estimate: 2000 input tokens + 1000 output tokens per activation
   - `estimated_cost = (2000 / 1_000_000 × input_price) + (1000 / 1_000_000 × output_price)`
3. If `accumulated_cost + estimated_cost > max_cost_per_run`:
   - **HALT** — do not activate the role
   - Invoke the `lessons` skill (log the cost-cap escalation as a failure event)
   - Report to the user: "Cost cap reached ($[accumulated_cost] of $[max_cost_per_run] used). Next role: [role] (~$[estimated_cost]). Approve to continue or adjust the cap in agent-config.yml."
   - Wait for explicit approval before proceeding

**Parallel fan-out:** when activating multiple roles simultaneously (e.g. tester_generator_a + tester_generator_b), sum all their estimated costs before checking the cap.

---

## Gate Protocol

At each gate, **STOP** and present the following. Do not proceed until you receive explicit approval.

### Gate 0 — Execution Plan
Present: The full execution plan from `state.md#gate-0`, including the **Run Estimates** block (see Gate 0 Estimates section below).
Ask: "Does this plan look right? Type **yes** to proceed or tell me what to change."
On reject: revise the plan and re-present.

### Gate 1 — Spec Approval
Present: The spec and acceptance criteria from `state.md#gate-1`
Show: Current spec revision count vs cap (e.g. "Revision 1 of max 2")
Ask: "Does this spec capture what you want? Type **yes** to proceed or tell me what to change."
On reject: Analyst revises and re-presents. Increment the spec revision counter.
**Cap:** read `pipeline.max_spec_revisions` from `agent-config.yml`. When reached: STOP, invoke `lessons` skill, report to user — "Spec revision limit reached ([n]/[max]). Proceeding with current spec or provide final direction."

### Gate 2 — Design Approval (only when Designer is activated)
Present: "Open `pipeline/[run-name]/design-preview.html` in your browser to review the mockup."
Show: The design notes from `state.md#gate-2` + current revision count (e.g. "Revision 1 of max 2")
Ask: "Does the design look right? Type **yes** to proceed or describe what to change."
On reject: Designer revises and re-presents. Increment the design revision counter.
**Cap:** read `pipeline.max_design_revisions` from `agent-config.yml`. When reached: STOP, report to user — "Design revision limit reached ([n]/[max]). Proceeding with current design or provide final direction."

### Gate 3 — Test Sign-Off
Present: Test results from `state.md#test-results`
Show: X/Y unit tests passed, X/Y integration tests passed, any failure details
Ask: "Tests complete. Type **yes** to deploy or **no** to hold."
On reject: do not deploy, await further instructions.

---

## Role Activation Brief Format

When activating a role, provide this context brief:

```
**Role:** [role name]
**Skill to invoke:** /[skill name]
**Read from state.md:** [exact sections]
**Write to state.md:** [exact section]
**Your output:** [what you must produce — be specific]
**Model:** [from agent-config.yml roles.[role].model]
**Tools available:** [from agent-config.yml roles.[role].tools]
**Lessons from prior runs:** [top-5 distilled lessons matching role:[role] filtered from knowledge_base/lessons/distilled/ — omit if KB is empty]
```

Roles have no persistent memory between activations. Always give the full context brief.

**How to populate lessons:** before activating any role, read `knowledge_base/index.md`. Filter `knowledge_base/lessons/distilled/` for files tagged with the role's name and the current run's `project_type` and `failure_type`. Inject the top-5 as bullets. If the KB is empty, omit the field entirely.

---

## Quality Gate Rules

The quality gate runs autonomously after Tester Ensemble Phase 2, before Gate 3. It is run by `tester_arbiter` using the `quality` skill. The Orchestrator never skips it.

1. **Autonomous** — tester_arbiter runs all checks without asking the user.
2. **On PASS** — write verdict to `state.md#quality-gate` and proceed to Gate 3.
3. **On FAIL** — write blocking findings to `state.md#quality-gate`, send report to Coder, increment the retry counter (shared with the TDD loop counter).
4. **Retry limit** — quality gate failures count against `pipeline.max_tester_retries`. When the limit is reached, escalate to the user.
5. **Bug-first rule** — for bug fixes, the quality gate verifies that a failing test was committed before the fix. If not, this is a blocking finding.

---

## TDD Loop Rules

1. **Tester Ensemble Phase 1 runs BEFORE Coder.** Tests are written from the spec, not from the code.
2. **Coder reads tests first.** Coder's job is to make the tests pass.
3. **Tester Ensemble Phase 2 runs AFTER Coder.** The ensemble runs all tests and reports results.
4. **Ensemble order (both phases):** tester_generator_a + tester_generator_b run in parallel → tester_consolidator deduplicates and merges → tester_arbiter resolves disagreements. Escalate critical unresolved conflicts to the user.
5. **On failure:** tester_consolidator writes a structured failure report to `state.md#test-results`. Before re-activating Coder, the Orchestrator refreshes the KB injection: filter `knowledge_base/lessons/distilled/` for `role:coder` and `failure_type:tdd-retry-limit`, inject top-5 into the retry brief alongside the failure report.
6. **Retry limit:** Read `pipeline.max_tester_retries` from `agent-config.yml`. When reached: STOP, invoke the `lessons` skill, then report to the user — "Tester retry limit reached ([n]/[max]). Human intervention required. Failures: [list]"
7. **Test types required:** Both unit tests (per function/method) and integration tests (cross-component flows) must exist before Coder starts.

---

## Review Cycle Rules

Code review runs after Coder completes (`code-review` skill, invoked by `tester_arbiter`). If the review produces blocking findings, Coder must fix and re-submit — this is one review cycle.

1. **Counter:** maintain `review_cycles` in `state.md#review-status`, starting at 0. Increment on each Coder re-submission.
2. **Retry limit:** read `pipeline.max_review_cycles` from `agent-config.yml`. When reached: STOP, invoke `lessons` skill, report to user:
   ```
   Code review cycle limit reached ([n]/[max]).
   Unresolved findings:
   - [list blocking findings]
   Options: a) Accept current state and proceed  b) Provide specific guidance for Coder  c) Abort run
   ```
3. **Non-blocking findings** (warnings, style): always proceed — do not count against the cycle limit.
4. **Review status in state.md:**
   ```markdown
   ## Review Status
   **Cycle:** [n] of [max]
   **Last verdict:** [pass | fail]
   **Open findings:** [count]
   ```

---

## Gate 0 Estimates

Every Gate 0 execution plan must include a **Run Estimates** block. Compute it as follows.

**Complexity:** classify the task as `small`, `medium`, or `large` based on scope:
- `small` — single endpoint, single component, isolated change
- `medium` — multiple components, cross-layer change, 3–8 acceptance criteria
- `large` — new subsystem, schema change, 9+ acceptance criteria or unknown domain

**Duration estimate:**
1. Read `pipeline.eta_minutes` from `agent-config.yml`
2. Sum ETA for each activated role at the classified complexity tier
3. Add retry buffer: `(max_tester_retries + max_review_cycles) × coder_eta × retry_time_factor`
4. If Designer activated: add designer ETA
5. Report as a range: `[base_sum] – [base_sum + retry_buffer]` minutes

**Cost estimate:**
1. For each activated role, compute: `(2000 input + 1000 output tokens) × model price` (from Cost Reference table)
2. Low estimate: no retries — sum all role activations once
3. High estimate: assume `max_tester_retries` Coder+Tester activations — multiply those roles' costs
4. Report as: `~$[low] – $[high]`

**Token estimate:**
1. Low: sum of `(2000 + 1000) × number_of_roles` tokens
2. High: low × (1 + max_tester_retries × 0.5)
3. Report as: `~[low]K – [high]K tokens`

**Retry budgets:** list each cap from `agent-config.yml`:

```markdown
## Run Estimates

**Complexity:** [small | medium | large]
**Duration:** ~[low]–[high] min  (no retries: ~[base] min)
**Cost:** ~$[low]–$[high]  (cap: $[max_cost_per_run])
**Tokens:** ~[low]K–[high]K

**Retry budgets:**
- TDD + quality gate: [max_tester_retries] rounds
- Spec revision: [max_spec_revisions] rounds
- Design revision: [max_design_revisions] rounds (n/a if Designer not activated)
- Code review: [max_review_cycles] rounds
```

Present this block at Gate 0. If any estimate exceeds the cost cap, warn the user before they approve.

---

## Token / Context Exhaustion Rules

The Orchestrator's context window can fill before a run completes. These rules ensure no work is lost and the run can always be resumed.

### Proactive checkpointing

After **each role completes**, before activating the next:
1. Verify `state.md` is fully written — the role's output section exists and is non-empty
2. Verify `log.md` has a row for the completed role
3. Write a checkpoint line to `state.md` at the bottom:
   ```
   **Last checkpoint:** [role just completed] at [timestamp]
   ```
This means the run can always resume from the last completed role, not from scratch.

### When context pressure is detected

Signs of context pressure (long run, many retries, epic with multiple features):
- After Gate 1 approval on a large run
- After each feature completes in an epic
- When the retry counter is > 1

At these points, proactively tell the user:
```
Context checkpoint: [role] complete. State saved to pipeline/[run-name]/state.md.

If this session runs out of context before the run finishes, type:
  /proj-resume pipeline/[run-name]
to pick up from here.
```

### When context is exhausted mid-role

If a role runs out of context window mid-task (the model stops responding or the session dies):
- The run is not lost — `state.md` has everything up to the last checkpoint
- The role's output for the interrupted step will be incomplete or absent
- The user will need to start a new session and type `/proj-resume pipeline/[run-name]`

`proj-resume` reads `state.md`, finds the last checkpoint, and restarts from the next incomplete step.

### When the API returns a quota or rate-limit error

If a provider returns a 429 (rate limit) or quota exhaustion error:
1. **STOP** — do not retry automatically (retrying immediately will fail again)
2. Write the error to `log.md` with status `escalated`
3. Report to the user:
   ```
   ⚠ Provider [provider] returned a rate-limit/quota error for role [role].

   Options:
   a) Wait and retry — the provider quota resets on a schedule (usually hourly or daily)
   b) Switch this role to a different provider — edit agent-config.yml roles.[role].provider
   c) Abort this run
   ```
4. Wait for user choice. The run state is fully preserved — resume once the user decides.

---

## Task Dependency Rules

Read the `## Feature & Task Breakdown` table in `state.md`:

1. **Independent tasks** (no dependencies): start immediately. If `pipeline.parallel_execution: true` in `agent-config.yml`, activate Coder for all independent tasks simultaneously.
2. **Blocked tasks**: mark as `⛔ BLOCKED`, queue until all listed dependencies are `closed`.
3. **Status transitions:** `open` → `in_progress` → `closed`.
4. **On parallel completion:** when a task closes, unblock tasks whose only dependency was that task.

---

## Designer Output Requirements

`pipeline/[run-name]/design-preview.html` must:
- Be a single self-contained HTML file (all CSS inline or from Bootstrap CDN)
- Use Bootstrap 5.3: `https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css`
- Show realistic component layouts — not placeholder boxes
- Include all UI states from the acceptance criteria
- Be openable by double-clicking in Finder (no build step)

---

## Escalation Rules

Stop and report to the user when:
- TDD retry limit is reached
- Quality gate retry limit is reached
- A deploy command fails
- A role cannot complete its task after two attempts
- A blocked task's dependency is `closed` but the task still cannot start
- The task is ambiguous and no skill covers it

Always include: what happened, what was tried, what the user needs to decide.

**After every escalation:** invoke the `lessons` skill. The Orchestrator runs the full Observe → Extract → Validate → Distill pipeline against the failed run before handing off to the user.

---

## Human Intervention Guide

Every situation where the pipeline stops and waits for a human, what they see, and what they need to do.

### Planned stops (expected — pipeline is healthy)

| Situation | What the human sees | What to type |
|---|---|---|
| **Gate 0** — execution plan ready | Plan, complexity, cost/duration estimate, retry budgets | `yes` to proceed; or describe changes |
| **Gate 1** — spec ready | Full PRD with all sections; revision count shown | `yes` to proceed; or describe what to change |
| **Gate 2** — design ready | Path to open `design-preview.html` in browser; design notes | `yes` to proceed; or describe what to change |
| **Gate 3** — tests passed | Test result summary (X/Y passed), quality gate verdict | `yes` to deploy; or `no` to hold |

### Limit hits (run is paused — human decides direction)

| Situation | What the human sees | Options to type |
|---|---|---|
| **Spec revision cap** hit | "Spec revision limit reached (2/2). Unresolved issues: [list]" | `accept` to proceed with current spec; or provide final direction in plain text |
| **Design revision cap** hit | "Design revision limit reached (2/2). Last version: design-preview.html" | `accept` to proceed with current design; or provide final direction |
| **TDD retry cap** hit | "Tester retry limit reached (3/3). Failures: [list]" | Paste specific fix guidance for Coder; or `abort` |
| **Review cycle cap** hit | "Code review cycle limit reached (2/2). Open findings: [list]" | `accept` current state; or provide specific guidance; or `abort` |

### Budget stops (run is paused — action required before continuing)

| Situation | What the human sees | Options to type |
|---|---|---|
| **Cost cap reached** | "Cost cap reached ($X.XX of $Y.YY used). Next role: [role] (~$Z). Approve to continue or adjust cap." | `approve` to continue; or `abort`; or update `cost_governance.max_cost_per_run` in `agent-config.yml` then type `approve` |
| **Provider rate limit / quota** | "Provider [X] returned rate-limit error for role [role]." | `retry` once quota resets; or `switch` — edit `agent-config.yml roles.[role].provider` then type `resume`; or `abort` |

### Blocking findings (action required before run can continue)

| Situation | What the human sees | Options to type |
|---|---|---|
| **Secrets found** in source files | "Pre-flight scan found secrets in [file:line]: [pattern]" | `redact` — replace value with placeholder; `false-positive` — proceed anyway; `abort` |
| **Container runtime unavailable** (`isolation: containerized`) | "No container runtime available (tried docker, podman)" | Install Docker/Podman and type `retry`; or update `test_env.isolation: process` in `agent-config.yml` and type `resume` |
| **Podman machine not running** (macOS) | "Podman machine not running. Run: podman machine start" | `! podman machine start` then type `retry` |
| **No deploy command found** | "No build command detected (checked Makefile, package.json, pyproject.toml)" | Type the build/start command to use |

### Context / session management

| Situation | What the human sees | What to do |
|---|---|---|
| **Context checkpoint** (proactive) | "Context checkpoint: [role] complete. If context runs out, type: /proj-resume pipeline/[run-name]" | Nothing required — informational only |
| **Session ended mid-run** | New session, no active pipeline | Type `/proj-resume pipeline/[run-name]` |
| **Guardrail candidates pending** | "There are [n] guardrail candidates awaiting your review: knowledge_base/guardrails_candidates.md" | Open the file, review candidates, move approved ones to `guardrails.yaml` |

---

## Lessons Retrieval at Pipeline Start

At the start of every pipeline run, before activating the first role, the Orchestrator:

1. Reads `knowledge_base/index.md`
2. Filters `knowledge_base/lessons/distilled/` by tags matching the current run (`role`, `failure_type`, `language`, `project_type`)
3. Injects the top-5 matching lessons into each role's context brief under `## Lessons from prior runs`
4. If `knowledge_base/guardrails_candidates.md` is non-empty, surface a reminder: "There are [n] guardrail candidates awaiting your review: `knowledge_base/guardrails_candidates.md`"

Skip retrieval if `knowledge_base/lessons/distilled/` is empty.

---

## Sandboxed Execution Rules

All agent-executed code (test runs, builds) runs in an isolated environment. Agents never run tests or builds directly against the host machine or any production-adjacent infrastructure.

**How isolation mode is determined** (read `test_env.isolation` from `agent-config.yml`):

| `isolation` value | Behavior |
|---|---|
| `auto` | Auto-detect container runtime; fall back to process isolation |
| `containerized` | Always use a container runtime — fail if none available |
| `process` | Run in a subprocess with `PORT` overrides from `test_env.port_pool` |
| `sequential` | Run tests sequentially in the current process (CI/CD with external sandboxing) |

**Container runtime selection** (read `test_env.runtime`):

| `runtime` value | How to check | CLI prefix |
|---|---|---|
| `docker` | `docker info > /dev/null 2>&1` | `docker` |
| `podman` | `podman info > /dev/null 2>&1` | `podman` |
| `none` | skip container isolation | — |

When `isolation: auto` and `runtime` is not set or is `docker`, try Docker first, then Podman:
```
docker info > /dev/null 2>&1 && RUNTIME=docker \
  || podman info > /dev/null 2>&1 && RUNTIME=podman \
  || RUNTIME=none
```
When `runtime` is set explicitly, use only that runtime — do not fall back to another.

**Container run command** (substitute `$RUNTIME` with `docker` or `podman`):

```
$RUNTIME run --rm \
  -v $(pwd):/workspace:ro \
  -w /workspace \
  [image] \
  [test-or-build command]
```
- `--rm` — container removed after run (ephemeral)
- `:ro` mount for test runs; omit for builds that write output files
- `[image]` — use project `Dockerfile` if present; otherwise fall back by language:
  `node:20-alpine` / `python:3.12-slim` / `golang:1.23-alpine`

**Podman-specific notes:**
- Podman is daemonless — no `sudo` or daemon startup required
- On macOS, Podman requires a Podman machine: `podman machine start` (user must have done this; do not start it automatically)
- `podman compose` is the equivalent of `docker compose` — substitute identically in deploy steps

**When container runtime is unavailable:**
- `isolation: auto` → fall back to process isolation; log a warning to `log.md` with status `escalated`
- `isolation: containerized` → **STOP**: report "No container runtime available (tried docker, podman)" to the user and wait

**Process isolation** (fallback or `isolation: process`):
- Assign a port from `test_env.port_pool.app` — do not use a port already in use
- Set `TEST_PORT=[assigned port]` in the subprocess environment
- Ensure test DB URL points to a local/ephemeral instance, never a shared or staging DB

**Absolute constraints:**
- Never run `npm test`, `pytest`, `go test`, or any build command directly on the host without isolation when `isolation` is not `sequential`
- Never connect to a production or staging database from within a test run
- Never write files outside the project directory or `/tmp/` from within a test or build

**The Coder role** must document the runtime and image used in `state.md#test-env` after first use in a run:
```markdown
## Test Environment
**Isolation:** containerized
**Runtime:** podman
**Image:** python:3.12-slim
**Run command:** podman run --rm -v $(pwd):/workspace:ro -w /workspace python:3.12-slim pytest
```

---

## Skill Selection Guide

| Classification | Analyst | Architect | Coder | Tester Ensemble | Quality Gate |
|---|---|---|---|---|---|
| New feature | `to-spec` | `to-tickets` + `codebase-design` | `implement` | `tdd` + `code-review` | `quality` |
| Bug fix | `to-spec` | *(skip)* | `diagnosing-bugs` | `tdd` | `quality` |
| Refactor | `to-spec` | `codebase-design` | `implement` | `code-review` | `quality` |
| UI / design | `to-spec` | `to-tickets` | `implement` | `tdd` + `code-review` | `quality` |
| Research needed | `research` + `to-spec` | `domain-modeling` + `to-tickets` | `implement` | `tdd` | `quality` |

**Orchestrator-only skills (not per-classification):**

| Skill | When |
|---|---|
| `data-governance` | Pre-flight: before any role reads source files |
| `eval` | Pre-flight: after any model or skill change in `agent-config.yml` |
| `lessons` | Post-failure: after any escalation or retry-limit hit |
