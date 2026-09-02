# New Feature Pipeline

Use this skill to build a new feature or implement a change request on an existing project.

Read `proj-protocol` for all shared rules: blackboard protocol, logging format, gate protocol, TDD loop rules, role activation brief format, and escalation rules.

---

## Step 0: Worktree Setup (if worktree_isolation: true)

Read `pipeline.worktree_isolation` from `agent-config.yml`.

If `true` and no worktree exists yet for this run:
```bash
git pull origin main
git worktree add .worktrees/[run-name] -b [run-name]
```

Record in `state.md` under `## Worktree`:
```markdown
## Worktree
**Path:** .worktrees/[run-name]
**Branch:** [run-name]
**Created:** [timestamp]
**Status:** active
```

If a worktree already exists for this run (resume case), skip creation — the existing worktree is re-used.

If `worktree_isolation: false`, skip this step entirely. The Coder will use `git checkout -b [run-name]` in the main checkout instead.

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
**Complexity:** [small | medium | large]

**Roles Activated:** Analyst, [Designer — if task has UI/UX], Architect, Tester Ensemble, Coder, Release Documenter, Deployer
**Designer Activated:** [yes | no]

**Execution Sequence:**
1. Analyst → skill: to-spec (or research + to-spec if domain is unfamiliar)
   Output: spec + acceptance criteria → state.md#gate-1
   [GATE 1: human approval required — revision cap: pipeline.max_spec_revisions]
2. Designer → skill: prototype    ← only if Designer: yes
   Output: design-preview.html + notes → state.md#gate-2
   [GATE 2: human approval required — revision cap: pipeline.max_design_revisions]
3. Architect → skill: to-tickets + codebase-design
   Reads: Gate 1 spec (+ Gate 2 design if present)
   Output: feature/task breakdown table → state.md#feature-task-breakdown
4. Tester Ensemble Phase 1 → skill: tdd
   Reads: spec + acceptance criteria
   4a. tester_generator_a + tester_generator_b in parallel → each generates test cases
   4b. tester_consolidator → deduplicates, produces test_plan.md → state.md#tests
   4c. tester_arbiter → resolves any generator disagreements before finalizing
   Output: unit tests + integration tests → state.md#tests
5. Coder → skill: implement
   Reads: spec + tests from state.md
   Working directory: .worktrees/[run-name]  (if worktree_isolation: true; else main checkout)
   Output: source files → state.md#code-artifacts
   Parallel execution: [per pipeline.parallel_execution in agent-config.yml]
6. Tester Ensemble Phase 2 → skill: tdd + code-review
   Reads: state.md#tests + all source files
   6a. tester_generator_a + tester_generator_b in parallel → each runs tests and reports
   6b. tester_consolidator → merges results → state.md#test-results
   6c. tester_arbiter → resolves disagreements; escalates critical failures to human
   Output: test results → state.md#test-results
   Retry cap: pipeline.max_tester_retries | Review cap: pipeline.max_review_cycles
7. Quality Gate → skill: quality (tester_arbiter, autonomous)
   Reads: state.md#tests + state.md#test-results + state.md#code-artifacts + git diff
   Output: pass/fail verdict → state.md#quality-gate
   On fail: findings sent back to Coder (increments retry counter); on pass: proceed
   [GATE 3: human approval required before deploying]
8. Release Documenter → skill: proj-deploy
   Reads: state.md in full
   Output: signoff_package.md → pipeline/[run-name]/signoff_package.md
9. Deployer → skill: proj-deploy

## Run Estimates

**Complexity:** [small | medium | large]
**Duration:** ~[low]–[high] min  (no retries: ~[base] min)
**Cost:** ~$[low]–$[high]  (cap: $[max_cost_per_run])
**Tokens:** ~[low]K–[high]K tokens

**Retry budgets:**
- TDD + quality gate: [max_tester_retries] rounds
- Spec revision: [max_spec_revisions] rounds
- Design revision: [max_design_revisions] rounds ([n/a if Designer not activated])
- Code review: [max_review_cycles] rounds

Compute estimates using the Gate 0 Estimates rules in proj-protocol.
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

## Step 3.5: Build Verification (after Quality Gate PASS, before Gate 3)

Activate `build_verifier` role immediately after the Quality Gate passes. Do not wait for user input — this runs autonomously like the Quality Gate.

**Context brief to provide:**
- Working directory / worktree path
- List of new or modified source files from `state.md#code-artifacts`
- Language/stack detected from the repo (check for `requirements.txt`, `package.json`, `pyproject.toml`, `Makefile`, `Dockerfile`)

**What the build verifier must do:**

1. **Dependency check** — confirm all dependencies introduced by this run are declared in the project manifest:
   - Python: `requirements.txt` or `pyproject.toml`
   - Node: `package.json`
   - If a new import exists in changed files but is absent from the manifest, this is a **blocking finding**

2. **Install check** — verify deps are installable:
   - Python: `pip install -r requirements.txt --dry-run` (or `pip check` if already installed)
   - Node: `npm install --dry-run`
   - If `deploy.build_tool` is `none` and no manifest exists, log as `skipped`

3. **Smoke test** — verify new entry points load and parse cleanly:
   - For each new Python script: `python3 -c "import [module]"` and `python3 [script] --help` (if CLI)
   - For each new Node entry: `node -e "require('./[file]')"` 
   - A non-zero exit from any smoke test is a **blocking finding**

4. **Lint** (if `lint` is in `deploy.pre_deploy_checks`):
   - Python: `python3 -m py_compile [file]` for each changed file (syntax check without external linter dep)

**Output contract** — write `pipeline/[run]/build_check.md`:

```markdown
# Build Check: [run-name]

**Verdict:** PASS | FAIL
**Timestamp:** [ISO 8601]

## Dependency check
[manifest file found | not found | skipped]
[list of new imports vs manifest — OK or MISSING]

## Install check
[command run + exit code + output summary]

## Smoke tests
| Script | Import | CLI (--help) | Result |
|---|---|---|---|
| scripts/foo.py | OK | OK | PASS |

## Lint
[files checked + result]

## Blocking findings
[none | list]
```

Also append to `state.md`:
```markdown
## Build Check
**Verdict:** [PASS | FAIL]
**Manifest:** [file found]
**Smoke tests:** [N/N passed]
**Blocking findings:** [count]
```

**On PASS** — proceed to Gate 3.
**On FAIL** — send blocking findings to Coder (same retry loop as Quality Gate failure). Increment the tester retry counter. If retry limit reached, escalate per proj-protocol escalation rules.

---

## Step 4: Dist Review (before Gate 3)

Before presenting Gate 3 to the user, review `dist/` and update any files that are stale relative to the changes in this run.

Check each dist file for references to:
- Scripts in `scripts/` — any new or renamed scripts must be listed
- Pipeline diagram — any new autonomous roles (e.g. Build Verifier) must appear
- Architecture notes — any new architectural patterns introduced must be described
- Install/validate steps — any new CLI flags or entry points must be documented

Files to check: `dist/README.md`, `dist/install.sh`, `dist/uninstall.sh`

Update as needed. If no changes are required, note "dist/ — no updates required" in log.md.
This step runs autonomously — do not ask the user for approval.

---

## Step 5: Gate 3 — Await Deploy Approval

Present test results **and build check verdict**. Wait for "yes" before invoking `/proj-deploy`.
