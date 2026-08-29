# Pipeline Protocol Reference

This is the shared protocol reference for all `proj-*` skills. Read this once per session before executing any pipeline skill.

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

## Blackboard Protocol

`pipeline/[run-name]/state.md` is **append-only** with one exception:
- Never overwrite or delete prior sections
- After a role completes, copy its output into the correct section of `state.md`
- **Exception — status fields only:** Gate status fields and task table status columns may be updated in-place. All other content is append-only.

Always read `state.md` before activating any role. Always pass the relevant sections in the role's context brief.

---

## Logging Protocol

After every agent action, append one row to `pipeline/[run-name]/log.md` (the log lives inside the run folder alongside `state.md`):

```
| YYYY-MM-DD HH:MM | [Role] | [action taken] | [artifact or section] | [complete | failed | escalated] |
```

Example:
```
| 2026-08-16 09:12 | Orchestrator | Created execution plan | pipeline/feat-dark-mode/state.md#gate-0 | complete |
| 2026-08-16 09:15 | Analyst | Wrote spec via to-spec | pipeline/feat-dark-mode/state.md#gate-1 | complete |
| 2026-08-16 09:45 | Tester Ensemble | Ran tests (retry 2/3) | pipeline/feat-dark-mode/state.md#test-results | failed |
```

Create `log.md` with a header row when the run folder is first created:
```markdown
# Pipeline Log: [run-name]

| Timestamp | Role | Action | Artifact | Status |
|---|---|---|---|---|
```

---

## Gate Protocol

At each gate, **STOP** and present the following. Do not proceed until you receive explicit approval.

### Gate 0 — Execution Plan
Present: The full execution plan from `state.md#gate-0`
Ask: "Does this plan look right? Type **yes** to proceed or tell me what to change."
On reject: revise the plan and re-present.

### Gate 1 — Spec Approval
Present: The spec and acceptance criteria from `state.md#gate-1`
Ask: "Does this spec capture what you want? Type **yes** to proceed or tell me what to change."
On reject: Analyst revises and re-presents.

### Gate 2 — Design Approval (only when Designer is activated)
Present: "Open `pipeline/[run-name]/design-preview.html` in your browser to review the mockup."
Show: The design notes from `state.md#gate-2`
Ask: "Does the design look right? Type **yes** to proceed or describe what to change."
On reject: Designer revises and re-presents.

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

## Lessons Retrieval at Pipeline Start

At the start of every pipeline run, before activating the first role, the Orchestrator:

1. Reads `knowledge_base/index.md`
2. Filters `knowledge_base/lessons/distilled/` by tags matching the current run (`role`, `failure_type`, `language`, `project_type`)
3. Injects the top-5 matching lessons into each role's context brief under `## Lessons from prior runs`
4. If `knowledge_base/guardrails_candidates.md` is non-empty, surface a reminder: "There are [n] guardrail candidates awaiting your review: `knowledge_base/guardrails_candidates.md`"

Skip retrieval if `knowledge_base/lessons/distilled/` is empty.

---

## Skill Selection Guide

| Classification | Analyst | Architect | Coder | Tester Ensemble | Quality Gate |
|---|---|---|---|---|---|
| New feature | `to-spec` | `to-tickets` + `codebase-design` | `implement` | `tdd` + `code-review` | `quality` |
| Bug fix | `to-spec` | *(skip)* | `diagnosing-bugs` | `tdd` | `quality` |
| Refactor | `to-spec` | `codebase-design` | `implement` | `code-review` | `quality` |
| UI / design | `to-spec` | `to-tickets` | `implement` | `tdd` + `code-review` | `quality` |
| Research needed | `research` + `to-spec` | `domain-modeling` + `to-tickets` | `implement` | `tdd` | `quality` |
