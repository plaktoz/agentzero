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
| 2026-08-16 09:45 | Tester | Ran tests (retry 2/3) | pipeline/feat-dark-mode/state.md#test-results | failed |
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
```

Roles have no persistent memory between activations. Always give the full context brief.

---

## TDD Loop Rules

1. **Tester Phase 1 runs BEFORE Coder.** Tests are written from the spec, not from the code.
2. **Coder reads tests first.** Coder's job is to make the tests pass.
3. **Tester Phase 2 runs AFTER Coder.** Tester runs all tests and reports results.
4. **On failure:** Tester writes a structured failure report to `state.md#test-results`. Orchestrator sends the report to Coder and increments the retry counter.
5. **Retry limit:** Read `pipeline.max_tester_retries` from `agent-config.yml`. When reached: STOP and report to the user — "Tester retry limit reached ([n]/[max]). Human intervention required. Failures: [list]"
6. **Test types required:** Both unit tests (per function/method) and integration tests (cross-component flows) must exist before Coder starts.

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
- A deploy command fails
- A role cannot complete its task after two attempts
- A blocked task's dependency is `closed` but the task still cannot start
- The task is ambiguous and no skill covers it

Always include: what happened, what was tried, what the user needs to decide.

---

## Skill Selection Guide

| Classification | Analyst | Architect | Coder | Tester |
|---|---|---|---|---|
| New feature | `to-spec` | `to-tickets` + `codebase-design` | `implement` | `tdd` + `code-review` |
| Bug fix | `to-spec` | *(skip)* | `diagnosing-bugs` | `tdd` |
| Refactor | `to-spec` | `codebase-design` | `implement` | `code-review` |
| UI / design | `to-spec` | `to-tickets` | `implement` | `tdd` + `code-review` |
| Research needed | `research` + `to-spec` | `domain-modeling` + `to-tickets` | `implement` | `tdd` |
