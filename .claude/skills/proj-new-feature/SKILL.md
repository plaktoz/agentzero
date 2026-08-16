# New Feature Pipeline

Use this skill to build a new feature or implement a change request on an existing project.

Read `proj-protocol` for all shared rules: blackboard protocol, logging format, gate protocol, TDD loop rules, role activation brief format, and escalation rules.

---

## Step 1: Accept Task and Create Run

Ask the user for the feature description if not provided as an argument.

Slugify the description: lowercase, spaces → hyphens, keep only alphanumeric and hyphens, truncate to 40 chars. Prefix with `feat-`.

Example: "add dark mode to dashboard" → `feat-add-dark-mode-to-dashboard`

Create the run folder: `pipeline/feat-[slug]/`
Create `pipeline/feat-[slug]/state.md` with the header:

```markdown
# Pipeline State: feat-[slug]

**Task:** [original task description]
**Started:** [date]
**Status:** in_progress
```

Read `agent-config.yml` for role configs.

---

## Step 2: Classify and Plan (Gate 0)

Reason through the task and produce an execution plan. Write it to `state.md` under `## Gate 0: Execution Plan`:

```
**Classification:** feature

**Roles Activated:** Analyst, [Designer — if task has UI/UX], Architect, Tester, Coder, Deployer

**Designer Activated:** [yes | no]

**Execution Sequence:**
1. Analyst → skill: to-spec (or research + to-spec if domain is unfamiliar)
   Output: spec + acceptance criteria → state.md#gate-1
   [GATE 1: human approval required]
2. Designer → skill: prototype    ← only if Designer: yes
   Output: design-preview.html + notes → state.md#gate-2
   [GATE 2: human approval required]
3. Architect → skill: to-tickets + codebase-design
   Reads: Gate 1 spec (+ Gate 2 design if present)
   Output: feature/task breakdown table → state.md#feature-task-breakdown
4. Tester Phase 1 → skill: tdd
   Reads: spec + acceptance criteria
   Output: unit tests + integration tests → state.md#tests
5. Coder → skill: implement
   Reads: spec + tests from state.md
   Output: source files → state.md#code-artifacts
   Parallel execution: [per pipeline.parallel_execution in agent-config.yml]
6. Tester Phase 2 → skill: tdd + code-review
   Reads: state.md#tests + all source files
   Output: test results → state.md#test-results
   Max retries: [pipeline.max_tester_retries]
   [GATE 3: human approval required before deploying]
7. Deployer → skill: proj-deploy
```

Present Gate 0 per the gate protocol. Wait for approval before proceeding.

---

## Step 3: Execute Pipeline

Follow the approved execution sequence. At each step:
1. Give the role its full context brief (format in proj-protocol)
2. Copy the role's output into the correct section of `state.md`
3. Log the action to `pipeline/[run-name]/log.md`
4. Stop at each gate per the gate protocol

For parallel Coder tasks: activate all independent tasks simultaneously if `parallel_execution: true`.

On TDD failure: increment retry counter, send failure report back to Coder. If retry limit reached, escalate per proj-protocol escalation rules.

---

## Step 4: Gate 3 — Await Deploy Approval

Present test results. Wait for "yes" before invoking `/proj-deploy`.
