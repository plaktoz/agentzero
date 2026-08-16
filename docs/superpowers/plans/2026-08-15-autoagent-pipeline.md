# Autonomous Multi-Agent Pipeline — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reusable, copy-into-any-project set of configuration files and custom skills that turns Claude Code into a dynamic multi-agent software development pipeline.

**Architecture:** A `CLAUDE.md` meta-orchestrator reads `agent-config.yml` at session start to configure seven roles (Orchestrator, Analyst, Designer, Architect, Coder, Tester, Deployer). The LLM-as-orchestrator decides which roles and skills activate per task, routing work through a shared `pipeline-state.md` blackboard with four human approval gates. Two custom skills (`deploy`, `project-init`) handle deployment and first-time project setup.

**Tech Stack:** CLAUDE.md (Claude Code instructions), YAML (agent-config.yml), Markdown (pipeline-state.md, pipeline-log.md), custom Claude Code skills (.claude/skills/), Python (validation script), Matt Pocock's engineering skills (already installed globally).

**Spec:** `research.md` (project root)

## Global Constraints

- Matt Pocock's skills are installed globally at `~/.claude/skills/` — reference them by name, do not copy them
- Model IDs must use exact strings: `claude-opus-4-8`, `claude-sonnet-5`, `claude-haiku-4-5-20251001`
- pipeline-state.md is append-only — never overwrite prior sections
- All configurable values live in `agent-config.yml` — no hardcoded values in CLAUDE.md or skills
- Human gates block forward progress — the pipeline pauses until explicit approval is received
- Tester writes tests before Coder writes code (TDD: tests from spec, not from implementation)

---

## File Map

| File | Purpose |
|---|---|
| `agent-config.yml` | Single source of truth for all configurable settings |
| `pipeline-state.md` | Shared blackboard — artifacts pass between agents via this file |
| `pipeline-log.md` | Structured execution log — one entry per agent action |
| `CLAUDE.md` | Meta-orchestrator instructions — how to run the full pipeline |
| `.claude/skills/deploy/SKILL.md` | Custom deploy skill — branches on docker/podman/none |
| `.claude/skills/project-init/SKILL.md` | Project initiation wizard — grills user, writes deploy config |
| `scripts/validate_config.py` | Validation script — confirms agent-config.yml is schema-complete |

---

## Task 1: Validation Script

Write a Python validation script first so we have a way to test `agent-config.yml` as we build it.

**Files:**
- Create: `scripts/validate_config.py`

**Interfaces:**
- Consumes: `agent-config.yml` (read from project root)
- Produces: stdout pass/fail report, exits 1 on any missing key

- [ ] **Step 1: Create the scripts directory and write the validator**

```python
# scripts/validate_config.py
import yaml
import sys
from pathlib import Path

REQUIRED_PIPELINE = ['parallel_execution', 'max_tester_retries']
REQUIRED_ROLES = ['orchestrator', 'analyst', 'designer', 'architect', 'coder', 'tester', 'deployer']
REQUIRED_ROLE_KEYS = ['model', 'tools', 'skills']
REQUIRED_DEPLOY = ['container_runtime', 'registry', 'target_environment', 'build_tool', 'pre_deploy_checks']

VALID_RUNTIMES = ['docker', 'podman', 'none']
VALID_ENVIRONMENTS = ['local', 'staging', 'production']

def validate(config_path: str) -> list[str]:
    errors = []
    path = Path(config_path)

    if not path.exists():
        return [f"File not found: {config_path}"]

    with open(path) as f:
        config = yaml.safe_load(f)

    if not isinstance(config, dict):
        return ["agent-config.yml must be a YAML mapping at the top level"]

    # pipeline section
    pipeline = config.get('pipeline', {})
    for key in REQUIRED_PIPELINE:
        if key not in pipeline:
            errors.append(f"Missing: pipeline.{key}")

    if 'max_tester_retries' in pipeline and not isinstance(pipeline['max_tester_retries'], int):
        errors.append("pipeline.max_tester_retries must be an integer")

    if 'parallel_execution' in pipeline and not isinstance(pipeline['parallel_execution'], bool):
        errors.append("pipeline.parallel_execution must be a boolean")

    # roles section
    roles = config.get('roles', {})
    for role in REQUIRED_ROLES:
        if role not in roles:
            errors.append(f"Missing role: {role}")
            continue
        role_cfg = roles[role]
        for key in REQUIRED_ROLE_KEYS:
            if key not in role_cfg:
                errors.append(f"Missing: roles.{role}.{key}")
        if 'tools' in role_cfg and not isinstance(role_cfg['tools'], list):
            errors.append(f"roles.{role}.tools must be a list")
        if 'skills' in role_cfg and not isinstance(role_cfg['skills'], list):
            errors.append(f"roles.{role}.skills must be a list")
        if role == 'designer' and 'optional' not in role_cfg:
            errors.append("roles.designer must have an 'optional' field set to true")

    # deploy section
    deploy = config.get('deploy', {})
    for key in REQUIRED_DEPLOY:
        if key not in deploy:
            errors.append(f"Missing: deploy.{key}")

    if 'container_runtime' in deploy and deploy['container_runtime'] not in VALID_RUNTIMES:
        errors.append(f"deploy.container_runtime must be one of: {VALID_RUNTIMES}")

    if 'target_environment' in deploy and deploy['target_environment'] not in VALID_ENVIRONMENTS:
        errors.append(f"deploy.target_environment must be one of: {VALID_ENVIRONMENTS}")

    return errors


if __name__ == '__main__':
    config_path = sys.argv[1] if len(sys.argv) > 1 else 'agent-config.yml'
    errors = validate(config_path)
    if errors:
        print("VALIDATION FAILED:")
        for e in errors:
            print(f"  ✗ {e}")
        sys.exit(1)
    else:
        print("✓ agent-config.yml is valid")
```

- [ ] **Step 2: Run the validator — expect it to fail (no agent-config.yml yet)**

```bash
cd /path/to/project && python scripts/validate_config.py
```

Expected: `File not found: agent-config.yml`

- [ ] **Step 3: Commit**

```bash
git add scripts/validate_config.py
git commit -m "feat: add agent-config.yml validator script"
```

---

## Task 2: agent-config.yml

Create the single source of truth for all pipeline settings — models, tools, skills, parallel execution, TDD retries, deploy config.

**Files:**
- Create: `agent-config.yml`

**Interfaces:**
- Consumes: nothing (root config)
- Produces: configuration read by CLAUDE.md, deploy skill, project-init skill, and validate_config.py

- [ ] **Step 1: Write agent-config.yml**

```yaml
# agent-config.yml
# Central configuration for the autonomous multi-agent pipeline.
# Edit this file to change models, skills, and runtime behaviour.
# Run `python scripts/validate_config.py` after editing.

pipeline:
  parallel_execution: true      # Run independent tasks concurrently
  max_tester_retries: 3         # Tester→Coder loop limit before human escalation

roles:
  orchestrator:
    model: claude-opus-4-8
    tools:
      - read_files
      - task_planning
    skills:
      - ask-matt                # Routes orchestrator to the right skill per situation

  analyst:
    model: claude-sonnet-5
    tools:
      - read_files
      - web_search
    skills:
      - to-spec                 # Converts requirements into a published spec
      - domain-modeling         # Pins down terminology and ubiquitous language
      - research                # Investigates questions against primary sources

  designer:
    model: claude-sonnet-5
    optional: true              # Only activated when task has a UI/UX component
    tools:
      - read_files
      - write_files
    skills:
      - prototype               # Throwaway single-file HTML prototype
      - frontend-design         # Full design system work

  architect:
    model: claude-opus-4-8
    tools:
      - read_files
      - write_files
    skills:
      - to-tickets              # Breaks spec into tasks with blocking-edge declarations
      - codebase-design         # Enforces small interfaces and clean seams

  coder:
    model: claude-sonnet-5
    tools:
      - read_files
      - write_files
      - terminal
    skills:
      - implement               # Builds from spec/tickets with TDD at seams
      - diagnosing-bugs         # Disciplined red→minimise→fix→regression loop

  tester:
    model: claude-haiku-4-5-20251001
    tools:
      - read_files
      - terminal
    skills:
      - tdd                     # Red-green-refactor loop, one vertical slice at a time
      - code-review             # Parallel sub-agent review across coding standards + spec

  deployer:
    model: claude-haiku-4-5-20251001
    tools:
      - terminal
      - git
    skills:
      - deploy                  # Custom skill: reads deploy section below

deploy:
  container_runtime: none       # docker | podman | none
  registry: none                # docker.io | ghcr.io | local | none
  target_environment: local     # local | staging | production
  build_tool: none              # dockerfile | compose | none
  pre_deploy_checks:
    - tests
    - lint
```

- [ ] **Step 2: Run the validator — expect it to pass**

```bash
python scripts/validate_config.py
```

Expected: `✓ agent-config.yml is valid`

- [ ] **Step 3: Commit**

```bash
git add agent-config.yml
git commit -m "feat: add agent-config.yml with all role and deploy settings"
```

---

## Task 3: pipeline-state.md Template

Create the shared blackboard template. Every new project copies this file and agents append to it throughout a session.

**Files:**
- Create: `pipeline-state.md`

**Interfaces:**
- Consumes: written by all roles in sequence
- Produces: structured state read by each downstream role and the orchestrator

- [ ] **Step 1: Write pipeline-state.md**

```markdown
# Pipeline State

<!-- This file is the shared blackboard for the multi-agent pipeline.
     Agents READ what came before them. Agents APPEND their output.
     Never overwrite or delete prior sections. -->

## Session Info

- Started: <!-- orchestrator fills this in -->
- Task: <!-- orchestrator fills this in -->
- Config: agent-config.yml

---

## Gate 0: Execution Plan

**Status:** `pending` <!-- orchestrator updates to: approved | rejected -->

**Classification:** <!-- feature | bug | refactor | design | deployment -->

**Roles Activated:** <!-- list -->

**Designer Activated:** <!-- yes | no -->

**Execution Sequence:**

<!-- Orchestrator writes the step-by-step plan here before Gate 0 is presented to the human. -->

---

## Gate 1: Spec & Acceptance Criteria

**Status:** `pending` <!-- analyst/orchestrator updates to: approved | rejected -->

**Analyst Output:**

<!-- Analyst writes the spec here after invoking their assigned skill. -->

**Acceptance Criteria:**

<!-- Analyst writes numbered acceptance criteria here. -->

---

## Gate 2: Design Approval

**Status:** `pending` <!-- only present when Designer is activated -->

**Designer Output:**

- Preview: `design-preview.html` (open in browser to review)
- Notes: <!-- Designer writes design decisions, component list, UX notes -->

---

## Feature & Task Breakdown

<!-- Architect writes this table after reading Gate 1 spec (and Gate 2 design if present). -->

| ID | Feature | Task | Dependencies | Status |
|---|---|---|---|---|
| F1.T1 | | | none | `open` |

**Legend:** Status values: `open` → `in_progress` → `closed` | `⛔ BLOCKED` = has unresolved dependencies

---

## Tests

<!-- Tester Phase 1 writes here BEFORE Coder writes any code. -->

**Unit Tests:**

```
<!-- test function names and what each tests -->
```

**Integration Tests:**

```
<!-- integration test names and what flows they cover -->
```

**Test File Locations:**
<!-- list of test file paths -->

---

## Code Artifacts

<!-- Coder writes source file locations here after implementation. -->

| File | Purpose | Task ID |
|---|---|---|
| | | |

---

## Test Results

<!-- Tester Phase 2 writes here after running tests against Coder's output. -->

**Gate 3 Status:** `pending` <!-- orchestrator updates to: approved | rejected -->

**Retry Count:** 0 / <!-- max_tester_retries from agent-config.yml -->

**Unit Tests:** <!-- X/Y passed -->

**Integration Tests:** <!-- X/Y passed -->

**Failures:**

```
<!-- test name, failure reason, line number -->
```

**Tester Recommendation:** <!-- deploy | do not deploy | escalate to human -->

---

## Deployment

<!-- Deployer writes here after Gate 3 approval. -->

**Status:** <!-- pending | complete | failed -->

**Deploy Log:**

```
<!-- shell output from deploy commands -->
```
```

- [ ] **Step 2: Commit**

```bash
git add pipeline-state.md
git commit -m "feat: add pipeline-state.md shared blackboard template"
```

---

## Task 4: pipeline-log.md Template

Create the structured execution log. Every agent action appends one row.

**Files:**
- Create: `pipeline-log.md`

**Interfaces:**
- Consumes: written by orchestrator after each agent completes
- Produces: audit trail readable by human and orchestrator

- [ ] **Step 1: Write pipeline-log.md**

```markdown
# Pipeline Log

<!-- Append one row per agent action. Never edit prior rows.
     Timestamp format: YYYY-MM-DD HH:MM -->

| Timestamp | Role | Action | Artifact | Status |
|---|---|---|---|---|
| <!-- --> | <!-- --> | <!-- --> | <!-- --> | <!-- --> |
```

- [ ] **Step 2: Commit**

```bash
git add pipeline-log.md
git commit -m "feat: add pipeline-log.md execution log template"
```

---

## Task 5: Custom Deploy Skill

Create the deploy skill that reads `agent-config.yml` and branches on `container_runtime`. This skill lives in the project's `.claude/skills/` so it is project-local and can be customised per project.

**Files:**
- Create: `.claude/skills/deploy/SKILL.md`

**Interfaces:**
- Consumes: `agent-config.yml` (deploy section), project source files
- Produces: running/deployed application, deploy log entry in `pipeline-state.md`

- [ ] **Step 1: Create the skills directory**

```bash
mkdir -p .claude/skills/deploy
```

- [ ] **Step 2: Write the deploy skill**

```markdown
# Deploy Skill

You are the Deployer agent. Follow these steps exactly.

## Step 1: Read Configuration

Read `agent-config.yml` and extract the `deploy` section:
- `container_runtime` — docker | podman | none
- `registry` — docker.io | ghcr.io | local | none
- `target_environment` — local | staging | production
- `build_tool` — dockerfile | compose | none
- `pre_deploy_checks` — list of checks to run before deploying

## Step 2: Run Pre-Deploy Checks

For each item in `pre_deploy_checks`:

**tests:**
Read `pipeline-state.md` — confirm Gate 3 status is `approved`. If not approved, STOP and tell the user Gate 3 must be approved before deploying.

**lint:**
Run the project's lint command. Find it by checking:
1. `package.json` scripts section for a `lint` key
2. `Makefile` for a `lint` target
3. `pyproject.toml` or `setup.cfg` for a linter config
If no lint command is found, log `lint: skipped (no lint command found)` and continue.

## Step 3: Build & Deploy

Branch on `container_runtime`:

### container_runtime: none

Run the project's standard build/start commands:
1. Check for `Makefile` → run `make build` then `make start` if targets exist
2. Check for `package.json` → run `npm run build` then `npm start`
3. Check for `pyproject.toml` → run `python -m build` or `pip install -e .`
4. If none found: tell the user no build command was detected and ask them to specify one.

### container_runtime: docker

1. Build: `docker build -t <project-name>:<git-short-sha> .`
   - `<project-name>` = basename of the project directory
   - `<git-short-sha>` = output of `git rev-parse --short HEAD`
2. If `registry` is not `none`: tag and push
   - `docker tag <project-name>:<git-short-sha> <registry>/<project-name>:<git-short-sha>`
   - `docker push <registry>/<project-name>:<git-short-sha>`
3. If `build_tool: compose`: run `docker compose up -d --build` instead of steps 1-2
4. Run: `docker run -d --name <project-name> <project-name>:<git-short-sha>`

### container_runtime: podman

Same steps as docker, replacing `docker` with `podman` in every command.
`docker compose` becomes `podman compose`.

## Step 4: Write to pipeline-state.md

Append to the `## Deployment` section:

```markdown
**Status:** complete

**Deploy Log:**
\```
[paste actual shell output from deploy commands]
\```
```

## Step 5: Write to pipeline-log.md

Append one row:
```
| [timestamp] | Deployer | Deployed [container_runtime] to [target_environment] | pipeline-state.md#deployment | complete |
```

## On Any Error

If any command fails:
1. Paste the full error output
2. Write `**Status:** failed` to `pipeline-state.md#deployment`
3. Do NOT attempt to retry automatically — report the error to the user and wait
```

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/deploy/SKILL.md
git commit -m "feat: add custom deploy skill with docker/podman/none branching"
```

---

## Task 6: Project Init Wizard Skill

Create the project-init skill that grills the user about deployment config and writes the answers to `agent-config.yml`. Run this once per new project.

**Files:**
- Create: `.claude/skills/project-init/SKILL.md`

**Interfaces:**
- Consumes: user answers (interactive)
- Produces: updated `deploy` section in `agent-config.yml`

- [ ] **Step 1: Create the directory**

```bash
mkdir -p .claude/skills/project-init
```

- [ ] **Step 2: Write the project-init skill**

```markdown
# Project Init Wizard

You are setting up this project for the autonomous multi-agent pipeline. Ask the questions below one at a time, waiting for each answer before continuing. After all answers, write them to `agent-config.yml`.

**Announce:** "Starting project-init wizard. I'll ask you 5 questions about deployment. Answer each one and I'll configure agent-config.yml for you."

---

## Question 1: Container Runtime

Ask: "What container runtime will you use for this project?"

Options (present these):
- `none` — run the app directly without containers (default for new projects)
- `docker` — use Docker to build and run
- `podman` — use Podman (rootless Docker alternative)

My recommendation: `none` for local development unless the app has external service dependencies.

Wait for answer. Save as `container_runtime`.

---

## Question 2: Container Registry

Only ask this if `container_runtime` is `docker` or `podman`.

Ask: "Where will you push container images?"

Options:
- `none` — build locally, don't push
- `docker.io` — Docker Hub
- `ghcr.io` — GitHub Container Registry
- `local` — local registry at localhost:5000

My recommendation: `none` for local-only development.

Wait for answer. Save as `registry`.

If `container_runtime` is `none`, set `registry: none` automatically without asking.

---

## Question 3: Build Tool

Only ask this if `container_runtime` is `docker` or `podman`.

Ask: "How will you define the container build?"

Options:
- `dockerfile` — single Dockerfile
- `compose` — docker-compose.yml / compose.yaml

My recommendation: `dockerfile` for single-service apps, `compose` if you have multiple services (database, cache, etc).

Wait for answer. Save as `build_tool`.

If `container_runtime` is `none`, set `build_tool: none` automatically without asking.

---

## Question 4: Target Environment

Ask: "What is the target environment for this project?"

Options:
- `local` — running on your machine only
- `staging` — a shared test environment
- `production` — live environment

My recommendation: `local` to start.

Wait for answer. Save as `target_environment`.

---

## Question 5: Pre-Deploy Checks

Ask: "Which checks should run before every deploy?"

Options (user can pick multiple — list them and ask which to include):
- `tests` — confirm Gate 3 approved before deploying
- `lint` — run the project's lint command

My recommendation: both.

Wait for answer. Save as `pre_deploy_checks` (a YAML list).

---

## Write to agent-config.yml

After all 5 answers, update the `deploy` section of `agent-config.yml`:

1. Read the current `agent-config.yml`
2. Replace the `deploy` section with the user's answers:

```yaml
deploy:
  container_runtime: <answer 1>
  registry: <answer 2>
  target_environment: <answer 4>
  build_tool: <answer 3>
  pre_deploy_checks:
    <answer 5 — one item per line with leading dash>
```

3. Write the updated file back
4. Run `python scripts/validate_config.py` to confirm the result is valid
5. Report the result to the user:

"Project init complete. Here is your deploy configuration:

```yaml
[show the deploy section]
```

Run `/deploy` when you're ready to ship."
```

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/project-init/SKILL.md
git commit -m "feat: add project-init wizard skill for deploy configuration"
```

---

## Task 7: CLAUDE.md — Meta-Orchestrator

The main instruction file. This is what Claude reads at the start of every session. It defines all roles, gates, protocols, and routing logic.

**Files:**
- Create: `CLAUDE.md`

**Interfaces:**
- Consumes: `agent-config.yml` (read at session start), `pipeline-state.md` (if resuming)
- Produces: orchestrated pipeline execution across all roles

- [ ] **Step 1: Write CLAUDE.md**

```markdown
# Autonomous Multi-Agent Development Pipeline

You are the **Orchestrator** for this project. This file governs how you operate.

---

## Session Start Protocol

Run these steps at the start of every session, in order:

1. Read `agent-config.yml` — load all role configs, models, tools, skill menus, pipeline settings, and deploy config
2. Check if `pipeline-state.md` exists with a status other than `complete` — if so, announce "Resuming pipeline from: [last completed step]" and offer to continue
3. Read `pipeline-log.md` if it exists — use it for context only, do not re-run completed steps
4. Await the user's task input

---

## Your Role: Orchestrator

You do not write code. You do not write specs. You coordinate agents.

Your job:
1. Receive a task from the user
2. Classify it and produce an execution plan
3. Present the plan at **Gate 0** for human approval
4. Activate roles in the approved sequence
5. Manage all human gates — STOP at each one, present the artifact, wait for approval
6. Track task statuses in `pipeline-state.md`
7. Log every agent action to `pipeline-log.md`
8. Escalate to the user when the TDD retry limit is hit

---

## Step 1: Classify and Plan

When you receive a task, reason through it and produce an execution plan in this format. Write it to the `## Gate 0: Execution Plan` section of `pipeline-state.md`:

```
**Classification:** [feature | bug | refactor | design | deployment]

**Roles Activated:** [list]

**Designer Activated:** [yes — task has a UI/UX component | no]

**Execution Sequence:**
1. Analyst → skill: [chosen from analyst.skills in agent-config.yml]
   Output: spec + acceptance criteria → pipeline-state.md#gate-1
   [GATE 1: human approval required before proceeding]
2. Designer → skill: prototype          ← only include if Designer: yes
   Output: design-preview.html + notes → pipeline-state.md#gate-2
   [GATE 2: human approval required before proceeding]
3. Architect → skill: [chosen from architect.skills]
   Reads: Gate 1 spec (+ Gate 2 design if present)
   Output: feature/task breakdown table → pipeline-state.md#feature-task-breakdown
4. Tester Phase 1 → skill: [chosen from tester.skills]
   Reads: Gate 1 spec + acceptance criteria
   Output: unit tests + integration tests → pipeline-state.md#tests
   Note: tests are written BEFORE any code. Coder does not start until this is done.
5. Coder → skill: [chosen from coder.skills]
   Reads: spec + tests from pipeline-state.md
   Output: source files → listed in pipeline-state.md#code-artifacts
   Parallel execution: [yes | no — per pipeline.parallel_execution in agent-config.yml]
   Independent tasks: [list]
   Blocked tasks (with dependencies): [list with ⛔ flag]
6. Tester Phase 2 → skill: [chosen from tester.skills]
   Reads: pipeline-state.md#tests + all source files
   Output: test results + failure report → pipeline-state.md#test-results
   Max retries: [pipeline.max_tester_retries from agent-config.yml]
   [GATE 3: human approval required before deploying]
7. Deployer → skill: deploy
   Reads: agent-config.yml#deploy + source files
   Waits for: Gate 3 approval
```

---

## Human Gate Protocol

At each gate, **STOP** and present the following to the user. Do not proceed until you receive explicit approval.

### Gate 0 — Execution Plan
Present: The full execution plan from `pipeline-state.md#gate-0`
Ask: "Does this plan look right? Type **yes** to proceed or tell me what to change."
On reject: revise the plan and re-present.

### Gate 1 — Spec Approval
Present: The spec and acceptance criteria from `pipeline-state.md#gate-1`
Ask: "Does this spec capture what you want? Type **yes** to proceed or tell me what to change."
On reject: Analyst revises the spec and re-presents.

### Gate 2 — Design Approval (only when Designer is activated)
Present: "Open `design-preview.html` in your browser to review the mockup."
Show: The design notes from `pipeline-state.md#gate-2`
Ask: "Does the design look right? Type **yes** to proceed or describe what to change."
On reject: Designer revises `design-preview.html` and re-presents.

### Gate 3 — Test Sign-Off
Present: Test results from `pipeline-state.md#test-results`
Show: X/Y unit tests passed, X/Y integration tests passed, any failure details
Ask: "Tests complete. Type **yes** to deploy or **no** to hold."
On reject: do not deploy, await further instructions.

---

## Role Activation Protocol

When activating a role, you must provide it with a context brief. Use this format:

```
**Role:** [role name]
**Skill to invoke:** /[skill name]
**Read from pipeline-state.md:** [exact sections]
**Write to pipeline-state.md:** [exact section]
**Your output:** [what you must produce — be specific]
**Model:** [from agent-config.yml roles.[role].model]
**Tools available:** [from agent-config.yml roles.[role].tools]
```

Roles do not have persistent memory between activations. Always give the full context brief.

---

## Skill Selection Guide

The orchestrator selects one skill per role per task based on classification:

| Classification | Analyst | Architect | Coder | Tester |
|---|---|---|---|---|
| New feature | `to-spec` | `to-tickets` + `codebase-design` | `implement` | `tdd` + `code-review` |
| Bug fix | `to-spec` | *(skip Architect)* | `diagnosing-bugs` | `tdd` |
| Refactor | `to-spec` | `codebase-design` | `implement` | `code-review` |
| UI / design | `to-spec` | `to-tickets` | `implement` | `tdd` + `code-review` |
| Research needed first | `research` + `to-spec` | `domain-modeling` + `to-tickets` | `implement` | `tdd` |
| Deployment only | *(skip to Deployer)* | *(skip)* | *(skip)* | *(skip)* |

For edge cases not covered above, use `ask-matt` to route to the right skill.

---

## TDD Loop Rules

1. **Tester Phase 1 runs BEFORE Coder.** Tests are written from the spec, not from the code.
2. **Coder reads tests first.** Coder's job is to write code that makes the tests pass.
3. **Tester Phase 2 runs AFTER Coder.** Tester runs all tests and reports results.
4. **On failure:** Tester writes a structured failure report to `pipeline-state.md#test-results`. Orchestrator sends the failure report to Coder and increments the retry counter.
5. **Retry limit:** Read `pipeline.max_tester_retries` from `agent-config.yml`. When the retry count reaches this limit: **STOP**, report to the user: "Tester retry limit reached ([n]/[max]). Human intervention required. Failures: [list]"
6. **Test types required:** Both unit tests (per function/method) and integration tests (cross-component flows) must be present before Coder starts.

---

## Task Dependency Rules

Read the `## Feature & Task Breakdown` table in `pipeline-state.md`:

1. **Independent tasks** (no dependencies): start immediately. If `pipeline.parallel_execution: true` in `agent-config.yml`, activate Coder for all independent tasks simultaneously.
2. **Blocked tasks** (has dependencies in the Dependencies column): mark as `⛔ BLOCKED`, queue until all listed task IDs are `closed`.
3. **Status transitions:** `open` → `in_progress` → `closed`. Update the table after each task completes.
4. **On parallel completion:** when a task closes, scan the table for tasks whose only dependency was that task. If all their dependencies are now `closed`, unblock them and activate Coder.

---

## Blackboard Protocol

`pipeline-state.md` is append-only. Rules:
- Read the file before activating any role — always pass the relevant sections in the context brief
- After a role completes, copy its output into the correct section of `pipeline-state.md`
- Never overwrite or delete prior sections
- Update status fields (Gate 0/1/2/3 status, task table status) in place — these are the only fields that change

---

## Logging Protocol

After every agent action, append one row to `pipeline-log.md`:

```
| YYYY-MM-DD HH:MM | [Role] | [action taken] | [artifact or section in pipeline-state.md] | [complete | failed | escalated] |
```

Examples:
```
| 2026-08-15 09:12 | Orchestrator | Created execution plan | pipeline-state.md#gate-0 | complete |
| 2026-08-15 09:15 | Analyst | Wrote spec via to-spec | pipeline-state.md#gate-1 | complete |
| 2026-08-15 09:22 | Designer | Generated HTML mockup | design-preview.html | complete |
| 2026-08-15 09:45 | Tester | Ran tests (retry 2/3) | pipeline-state.md#test-results | failed |
```

---

## Designer Output Requirements

When Designer is activated, the output `design-preview.html` must:
- Be a single self-contained HTML file (all CSS inline or from Bootstrap CDN)
- Use Bootstrap 5.3 from CDN: `https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css`
- Show realistic component layouts — not placeholder boxes
- Include all UI states visible in the acceptance criteria
- Be openable by double-clicking in Finder (no build step required)

Reference style: https://getbootstrap.com/docs/5.3/examples/

---

## Escalation Rules

Escalate to the user (stop and report) when:
- TDD retry limit is reached
- A deploy command fails
- A role cannot complete its task after two attempts
- A blocked task's dependency has been `closed` but the blocked task cannot start (dependency conflict)
- The user's task is ambiguous and no skill covers it

Always include: what happened, what was tried, what the user needs to decide.

---

## Project Init

If this is a new project (no `pipeline-state.md` and no prior log entries), run `/project-init` before taking any task. This configures the deploy section of `agent-config.yml` for this specific project.
```

- [ ] **Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "feat: add CLAUDE.md meta-orchestrator for multi-agent pipeline"
```

---

## Task 8: End-to-End Validation

Verify the full system is self-consistent before declaring done.

**Files:**
- No new files — this is a manual verification pass

- [ ] **Step 1: Run the YAML validator**

```bash
python scripts/validate_config.py
```

Expected: `✓ agent-config.yml is valid`

- [ ] **Step 2: Check CLAUDE.md references all 4 gates**

```bash
grep -c "Gate [0-3]" CLAUDE.md
```

Expected: at least 8 (each gate appears multiple times)

- [ ] **Step 3: Check CLAUDE.md references agent-config.yml**

```bash
grep -c "agent-config.yml" CLAUDE.md
```

Expected: 5 or more

- [ ] **Step 4: Check deploy skill references agent-config.yml**

```bash
grep -c "agent-config.yml" .claude/skills/deploy/SKILL.md
```

Expected: 1 or more

- [ ] **Step 5: Check project-init skill writes to agent-config.yml**

```bash
grep -c "agent-config.yml" .claude/skills/project-init/SKILL.md
```

Expected: 1 or more

- [ ] **Step 6: Verify all 7 roles are defined in both agent-config.yml and CLAUDE.md**

```bash
for role in orchestrator analyst designer architect coder tester deployer; do
  echo -n "$role in agent-config.yml: "
  grep -c "^  $role:" agent-config.yml
  echo -n "$role in CLAUDE.md: "
  grep -ci "$role" CLAUDE.md
done
```

Expected: each role appears at least once in each file.

- [ ] **Step 7: Dry-run scenario check — trace a bug fix task through the pipeline**

Read `CLAUDE.md` and mentally walk through this task:

> "The login button submits the form twice on mobile."

Verify:
- Orchestrator classifies as `bug`
- Architect is skipped (bug classification skips Architect per Skill Selection Guide)
- Designer is skipped (no UI design change needed for a bug fix)
- Analyst invokes `to-spec`
- Tester Phase 1 writes tests before Coder starts
- Coder invokes `diagnosing-bugs`
- Gate 3 appears before Deployer runs
- All 4 gates are present in the pipeline-state.md sections

If any of these fail: fix the relevant file and re-run the check.

- [ ] **Step 8: Final commit**

```bash
git add -A
git status   # confirm only expected files are staged
git commit -m "feat: complete autonomous multi-agent pipeline setup"
```

---

## Post-Setup: Using This System

Copy these files into any new project:
```
CLAUDE.md
agent-config.yml
pipeline-state.md
pipeline-log.md
.claude/skills/deploy/SKILL.md
.claude/skills/project-init/SKILL.md
scripts/validate_config.py
```

Then in a new Claude Code session:
1. Claude reads `CLAUDE.md` and `agent-config.yml` automatically
2. Run `/project-init` to configure the deploy section for this project
3. Give Claude a task — the pipeline starts at Gate 0
