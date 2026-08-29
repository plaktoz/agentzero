# Quality Gate

Autonomous post-code quality gate. Runs after Tester Ensemble Phase 2, before Gate 3. Never asks the user — emits a pass or fail verdict that the pipeline acts on automatically.

**Role:** tester_arbiter  
**Model:** claude-sonnet-5  
**Triggered by:** Orchestrator after Tester Ensemble Phase 2 completes

---

## Assessment Pipeline

Run all checks in order. Stop and emit a blocking verdict on the first high-severity finding.

### 1. Scope Check

Run `git diff --stat HEAD` against the base branch.

- Flag any file changed that is not referenced in `state.md#code-artifacts`
- Flag deletions of files not mentioned in the spec
- Flag changes outside the directories implied by the feature/bug/refactor scope

Severity: **high** if out-of-scope changes touch core modules or shared infrastructure; **low** if trivial (comments, whitespace).

---

### 2. Test Evidence

Read the test files from `state.md#tests`.

- Every acceptance criterion in the spec must have at least one corresponding test
- Tests must assert **outcomes**, not implementation details (no assertions on private internals or mock call counts unless the spec requires it)
- For bug fixes: a **failing test committed before the fix** must exist (bug-first rule — see Testing Rules below)
- Unit tests and integration tests must both be present

Severity: **high** if a spec requirement has no test coverage; **medium** if tests assert implementation details.

---

### 3. Code Quality

Read `test_env.isolation` from `agent-config.yml`. Run the linter and test suite inside an isolated environment per the **Sandboxed Execution Rules** in `proj-protocol`. Never run tests directly on the host when `isolation` is not `sequential`.

Read the linter and test commands from `agent-config.yml` under `deploy.pre_deploy_checks`.

- All tests must pass
- No linter errors (warnings are allowed)
- Error paths must be handled — no silent swallows (`catch {}`, `_ =`, unhandled promise rejections)

Severity: **high** if tests fail or linter errors exist.

---

### 4. Principle Compliance

Read `state.md#gate-1` (spec + acceptance criteria).

Check each changed file against the base principles:
- No scope creep — changes implement what the spec says, nothing more
- No bolted-on changes — if a design flaw was found, it should be redesigned, not patched around
- No dead code introduced
- Interfaces stay small — new public API surface must be justified by the spec

Then read `knowledge_base/lessons/distilled/` and filter for lessons tagged `role:coder` or `role:tester_ensemble` for the current `project_type`. Treat each distilled lesson's **Corrective action** bullets as additional compliance rules for this check. If a changed file violates a distilled lesson's corrective action, that is a principle compliance finding.

Severity: **high** if scope creep or bolted-on changes detected, or if a distilled lesson's corrective action is violated; **medium** otherwise.

---

### 5. Runtime Verification

"It compiles" is not verification.

- The changed code must have been exercised by the test suite (covered)
- Integration tests must have run against a real runtime (not fully mocked)
- If the feature has a UI: the component must render without errors in at least one test

Severity: **high** if no runtime exercise exists for the changed paths.

---

## Verdict

After all checks, emit one of:

**PASS** — write to `state.md#quality-gate`:
```
## Quality Gate

**Verdict:** PASS
**Checked by:** tester_arbiter
**Findings:** [none | list of low/medium findings with no action required]
```
Pipeline proceeds to Gate 3.

**FAIL** — write to `state.md#quality-gate`:
```
## Quality Gate

**Verdict:** FAIL
**Checked by:** tester_arbiter
**Blocking findings:**
- [check name]: [description of finding]
- ...
**Required actions:** [specific fixes Coder must make]
```
Orchestrator sends the failure report back to Coder and increments the retry counter (same counter as the TDD loop). If `max_tester_retries` is reached, escalate to the user.

---

## Testing Rules (enforced at check 2)

These rules apply to all pipeline types. The quality gate verifies they were followed:

**Bug fixes:**
1. A failing test reproducing the bug must be committed separately, before the fix commit
2. The fix commit must not include test changes (tests were written first)
3. The test must assert the correct output, not that a specific function was called

**Features and refactors:**
1. Tests are written from the spec before code (verified by commit order in `git log`)
2. Fixture-based test data lives in a `testdata/` directory when applicable
3. Each acceptance criterion maps to at least one named test case
