# Fix Bug Pipeline

Use this skill to diagnose and fix a bug. This pipeline skips the Architect and uses the `diagnosing-bugs` skill for Coder.

Read `proj-protocol` for all shared rules: blackboard protocol, logging format, gate protocol, TDD loop rules, role activation brief format, and escalation rules.

---

## Step 1: Accept Bug Description and Create Run

Ask the user for the bug description if not provided as an argument.

Slugify the description: lowercase, spaces → hyphens, keep only alphanumeric and hyphens, truncate to 40 chars. Prefix with `fix-`.

Example: "auth token null pointer on logout" → `fix-auth-token-null-pointer-on-logout`

Create the run folder: `pipeline/fix-[slug]/`
Create `pipeline/fix-[slug]/state.md` with the header:

```markdown
# Pipeline State: fix-[slug]

**Task:** [original bug description]
**Started:** [date]
**Status:** in_progress
```

Read `agent-config.yml` for role configs.

---

## Step 2: Classify and Plan (Gate 0)

Write the execution plan to `state.md` under `## Gate 0: Execution Plan`:

```
**Classification:** bug

**Roles Activated:** Analyst, Tester, Coder, Deployer

**Designer Activated:** no

**Execution Sequence:**
1. Analyst → skill: to-spec
   Output: bug spec + reproduction steps + acceptance criteria → state.md#gate-1
   [GATE 1: human approval required]
2. Tester Phase 1 → skill: tdd
   Reads: bug spec + acceptance criteria
   Output: failing tests that reproduce the bug → state.md#tests
3. Coder → skill: diagnosing-bugs
   Reads: bug spec + failing tests from state.md
   Output: fix + source files → state.md#code-artifacts
4. Tester Phase 2 → skill: tdd
   Reads: state.md#tests + all source files
   Output: test results → state.md#test-results
   Max retries: [pipeline.max_tester_retries]
   [GATE 3: human approval required before deploying]
5. Deployer → skill: proj-deploy
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
