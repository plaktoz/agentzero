# Eval — Prompt & Config Versioning Gate

Run eval before rolling out any change to a role's model, system prompt, or skill configuration. Prevents regressions reaching production runs.

**Role:** Orchestrator  
**When:** After any edit to `agent-config.yml` that changes `model`, `provider`, or `skills` for any role; or after editing a role's primary skill  
**Autonomous:** yes — scores deterministically; only blocks on regression (score drop > threshold)

---

## Trigger Conditions

Run this skill when **any** of the following change in `agent-config.yml`:
- A role's `model` field
- A role's `provider` field
- A role's `skills` list
- A role's primary skill file (e.g. `to-spec/SKILL.md`, `implement/SKILL.md`)
- `config_version` is incremented

Also run before the first pipeline run on a new machine to establish a baseline.

---

## Step 1: Detect Changed Roles

```
git diff HEAD -- agent-config.yml
```

Extract the set of roles whose `model`, `provider`, or `skills` changed. If a skill file changed (e.g. `analyst/to-spec/SKILL.md`), map the skill back to the roles that use it.

If no roles changed but `config_version` was bumped, run eval for all roles.

---

## Step 2: Version the Config Snapshot

Copy the current `agent-config.yml` to `eval/config-history/v[config_version].yml`:

```
cp agent-config.yml eval/config-history/v[config_version].yml
```

This creates an immutable audit trail. Never overwrite existing snapshots.

---

## Step 3: Load Golden Tests

For each changed role, read `eval/roles/[role]/golden-tests.md`.

If the file does not exist for a role, skip that role and log:
```
eval/roles/[role]/golden-tests.md not found — skipping eval for [role]. Add golden tests before this role is used in production.
```

**Golden test format** (in `golden-tests.md`):
```markdown
## Test: [test-id] — [short description]

**Input:**
[the prompt or context that would be sent to this role]

**Expected structural output:**
[required fields, format, or schema the output must contain]

**Expected behaviors:**
- [bullet list of things the output must do or avoid]

**Execution check:** [yes | no — whether to actually invoke the role and check output]
```

---

## Step 4: Run Each Test

For each golden test in the changed role's test file:

### Scoring Method A — Structural Check (deterministic, no LLM call)

Parse the role's output against the expected structural output:
- Does the output contain all required fields/sections?
- Does it match the expected format (markdown table, JSON schema, numbered list)?
- Are any prohibited patterns present (e.g. code in a spec-only role output)?

Score: `pass` (1) or `fail` (0) per test. Binary.

### Scoring Method B — LLM-as-Judge

Construct a judge prompt:

```
You are evaluating a pipeline agent's output against acceptance criteria.

Role: [role]
Task: [test description]
Input given to the agent: [input]
Agent output: [output]

Acceptance criteria:
[expected behaviors list]

Score the output 1–5 on each criterion. 5 = fully meets, 1 = does not meet.
Also provide an overall pass/fail: pass if average score >= 3.5, fail otherwise.

Return JSON: {"scores": {"[criterion]": [1-5]}, "average": [float], "verdict": "pass|fail", "rationale": "[one sentence]"}
```

Use the Orchestrator model (`claude-opus-4-8`) as judge. Parse the JSON response.

### Scoring Method C — Execution Check (only when `execution check: yes`)

If the test requires execution verification:
1. Activate the role with the test input as its context brief (using `--dry-run` label in the log)
2. Check that the output compiles / runs / passes basic smoke test depending on role:
   - `coder` output: files must be syntactically valid (run `node --check` / `python -m py_compile` / `go build`)
   - `analyst` output: must be parseable as markdown with the required sections
   - `architect` output: task table must be parseable (all required columns present)
3. Score: `pass` or `fail` (binary)

---

## Step 5: Aggregate Scores

For each role, compute:

| Metric | Threshold |
|---|---|
| Structural pass rate | ≥ 90% of tests must pass |
| LLM-as-judge average | ≥ 3.5 / 5.0 across all tests |
| Execution pass rate (if applicable) | ≥ 80% of tests must pass |

**Overall role verdict:** PASS if all three metrics meet their threshold; FAIL otherwise.

---

## Step 6: Write Results

Write scores to `eval/roles/[role]/scores.md`:

```markdown
# Eval Scores — [role]

**Config version:** [config_version]
**Date:** [YYYY-MM-DD]
**Model:** [model from agent-config.yml]
**Previous model:** [model from previous snapshot, or "—"]

## Results

| Test | Structural | LLM Judge (avg) | Execution | Verdict |
|---|---|---|---|---|
| [test-id] | pass/fail | [score]/5 | pass/fail/n/a | PASS/FAIL |

**Overall:** PASS / FAIL  
**Structural pass rate:** [n/total]  
**LLM-judge average:** [avg]  
**Execution pass rate:** [n/applicable]
```

Also append a one-line entry to `eval/scores-log.md`:
```
[YYYY-MM-DD] v[config_version] [role] [overall verdict] structural:[n/n] judge:[avg] exec:[n/n|n/a]
```

---

## Step 7: Gate the Rollout

**All changed roles PASS:** proceed. Log to `pipeline-log.md`:
```
[timestamp] | Orchestrator | eval | v[config_version] | all roles passed eval | PASS
```

**Any changed role FAILS:**
1. **HALT** — do not start the pipeline run
2. Report to the user:
   ```
   ⚠ Eval gate blocked rollout of config v[config_version]:
   
   Role: [role]
   Model: [model]
   Failed tests: [list]
   Lowest judge score: [score] ([criterion])
   
   Options:
   a) Revert the model/prompt change in agent-config.yml and decrement config_version
   b) Add/update golden tests if the new behavior is intentionally different
   c) Override (not recommended — adds a warning to pipeline-log.md)
   ```
3. Wait for explicit user choice before proceeding

---

## Adding and Updating Golden Tests

Golden tests are the ground truth for role quality. They must be maintained as roles evolve.

**When to add a golden test:**
- After a successful pipeline run produces a high-quality artifact, add it as a golden test
- When a role consistently fails in a specific way, add a test that catches that failure

**When to update a golden test:**
- When the role's spec or skill is intentionally changed and old behavior is no longer correct
- After updating, increment `config_version` and re-run eval to establish the new baseline

**File location:** `eval/roles/[role]/golden-tests.md`

See `eval/roles/orchestrator/golden-tests.md` for a worked example.

---

## Relationship to Lessons Pipeline

Eval and lessons are complementary:
- **Lessons** capture what went wrong in a real run and distill rules to prevent recurrence
- **Eval** verifies that a config change doesn't introduce regressions before a run starts

When a lessons distillation produces a new corrective action rule, add a golden test that verifies the rule is met by the current model/prompt.
