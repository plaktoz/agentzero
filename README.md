# Autonomous Multi-Agent Development Pipeline

A Claude Code project template that turns a single AI session into a structured, multi-role development pipeline — with human approval gates at every critical step.

---

## What It Does

You describe a task. The **Orchestrator** (Claude Code, guided by `CLAUDE.md`) routes it through specialized roles:

```
User Task → Orchestrator → Analyst → Designer* → Architect → Tester → Coder → Tester → Deployer
                                    (* only for UI tasks)
```

Human approval gates pause the pipeline at the spec, design, and test stages before any irreversible step proceeds.

---

## Prerequisites

- [Claude Code](https://claude.ai/code) CLI installed
- Python 3.9+ (for config validation)
- An Anthropic API key

---

## Setup

**1. Set your API key**

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

**2. Install Python dependencies**

```bash
pip install pyyaml
```

**3. Validate the config**

```bash
python scripts/validate_config.py
```

You should see: `✓ agent-config.yml is valid`

**4. Open Claude Code in this directory**

```bash
claude
```

---

## First-Time Setup

Run the setup wizard to configure deployment settings:

```
/proj-start
```

This configures the `deploy` section of `agent-config.yml` for your project (container runtime, registry, target environment, etc.).

---

## Commands

| Command | When to use |
|---|---|
| `/proj-start` | First-time project setup |
| `/proj-new-feature [description]` | Add a feature or implement a change request |
| `/proj-fix-bug [description]` | Fix a bug |
| `/proj-refactor [description]` | Refactor existing code |
| `/proj-resume [run-name]` | Resume an in-progress pipeline run |
| `/proj-deploy` | Deploy the project |
| `/proj-cleanup` | Remove completed or abandoned pipeline runs |
| `/proj-config` | Reconfigure deployment settings |

---

## The Pipeline Gates

| Gate | What you review | Prompt |
|---|---|---|
| **Gate 0** | Execution plan — roles, sequence, parallel tasks | `yes` to proceed |
| **Gate 1** | Spec and acceptance criteria from the Analyst | `yes` to proceed |
| **Gate 2** | UI mockup in `design-preview.html` *(UI tasks only)* | `yes` to proceed |
| **Gate 3** | Test results — unit + integration pass/fail counts | `yes` to deploy |

Type `yes` to advance, or describe what to change and the relevant role will revise and re-present.

---

## Pipeline State

Each run stores its state in its own folder, tracked in git:

```
pipeline/
  feat-dark-mode/
    state.md          ← shared blackboard for all agent outputs
    log.md            ← append-only log of every agent action
    design-preview.html  ← generated UI mockup (UI tasks only)
  fix-auth-bug/
    state.md
    log.md
```

State is committed to git so pipelines survive across sessions and machines.

---

## Key Files

| File | Purpose |
|---|---|
| `agent-config.yml` | Central config — models, roles, tools, skills, deploy settings |
| `CLAUDE.md` | Orchestrator identity and command reference |
| `scripts/validate_config.py` | Validates `agent-config.yml` structure |

---

## Configuring `agent-config.yml`

### Change a role's model

```yaml
roles:
  coder:
    model: claude-opus-4-8
```

### Enable/disable parallel task execution

```yaml
pipeline:
  parallel_execution: true
```

### Set the TDD retry limit

```yaml
pipeline:
  max_tester_retries: 3
```

### Configure deployment

```yaml
deploy:
  container_runtime: docker
  registry: ghcr.io
  target_environment: staging
  build_tool: dockerfile
  pre_deploy_checks:
    - tests
    - lint
```

After editing, re-run:

```bash
python scripts/validate_config.py
```

---

## How the TDD Loop Works

Tests are written **before** any code:

1. **Tester Phase 1** reads the spec and writes unit + integration tests
2. **Coder** reads the tests and writes code to make them pass
3. **Tester Phase 2** runs all tests and reports results
4. On failure, the failure report goes back to Coder (retry counter increments)
5. If retries hit `max_tester_retries`, the Orchestrator escalates to you

---

## Resuming Across Sessions or Machines

```bash
git pull
claude
/proj-resume
```

`proj-resume` lists all in-progress runs and picks up from the last completed step.

---

## Roles Reference

| Role | Model (default) | Activated for |
|---|---|---|
| Orchestrator | claude-opus-4-8 | Every task |
| Analyst | claude-sonnet-5 | Every task |
| Designer | claude-sonnet-5 | UI/UX tasks only |
| Architect | claude-opus-4-8 | Features, refactors |
| Coder | claude-sonnet-5 | Every task with code |
| Tester | claude-haiku-4-5 | Every task with code |
| Deployer | claude-haiku-4-5 | After Gate 3 approval |

Models can be changed per-role in `agent-config.yml`.
