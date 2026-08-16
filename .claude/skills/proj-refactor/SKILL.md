# Refactor Pipeline

Use this skill to refactor existing code. No Designer. Architect uses `codebase-design` only.

Read `proj-protocol` for all shared rules: blackboard protocol, logging format, gate protocol, TDD loop rules, role activation brief format, and escalation rules.

---

## Step 1: Accept Refactor Description and Create Run

Ask the user for the refactor description if not provided as an argument.

Slugify the description: lowercase, spaces → hyphens, keep only alphanumeric and hyphens, truncate to 40 chars. Prefix with `refactor-`.

Example: "extract auth middleware into its own module" → `refactor-extract-auth-middleware`

Create the run folder: `pipeline/refactor-[slug]/`
Create `pipeline/refactor-[slug]/state.md` with the header:

```markdown
# Pipeline State: refactor-[slug]

**Task:** [original refactor description]
**Started:** [date]
**Status:** in_progress
```

Read `agent-config.yml` for role configs.

---

## Step 2: Classify and Plan (Gate 0)

Write the execution plan to `state.md` under `## Gate 0: Execution Plan`:

```
**Classification:** refactor

**Roles Activated:** Analyst, Architect, Tester, Coder, Deployer

**Designer Activated:** no

**Execution Sequence:**
1. Analyst → skill: to-spec
   Output: refactor scope + acceptance criteria (no regressions) → state.md#gate-1
   [GATE 1: human approval required]
2. Architect → skill: codebase-design
   Reads: Gate 1 spec
   Output: target architecture + seam definitions → state.md#feature-task-breakdown
3. Tester Phase 1 → skill: code-review
   Reads: spec + existing source files
   Output: regression test suite covering current behaviour → state.md#tests
4. Coder → skill: implement
   Reads: spec + target architecture + regression tests from state.md
   Output: refactored source files → state.md#code-artifacts
5. Tester Phase 2 → skill: code-review
   Reads: state.md#tests + all source files
   Output: test results — all prior tests must still pass → state.md#test-results
   Max retries: [pipeline.max_tester_retries]
   [GATE 3: human approval required before deploying]
6. Deployer → skill: proj-deploy
```

Present Gate 0 per the gate protocol. Wait for approval.

---

## Step 3: Execute Pipeline

Follow the approved execution sequence:
1. Give each role its full context brief
2. Copy role output into the correct section of `state.md`
3. Log each action to `pipeline/[run-name]/log.md`
4. Stop at each gate

On TDD failure: increment retry counter, send failure report back to Coder. If retry limit reached, escalate.

---

## Step 4: Gate 3 — Await Deploy Approval

Present test results. Wait for "yes" before invoking `/proj-deploy`.
