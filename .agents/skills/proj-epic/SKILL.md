# Epic Pipeline

Use this skill to plan and execute a Jira-style epic — a collection of related features that share a goal but are built and reviewed independently.

Read `proj-protocol` for all shared rules: blackboard protocol, logging format, gate protocol, TDD loop rules, role activation brief format, and escalation rules.

---

## Step 1: Accept Epic Description and Create Run

Ask the user for the epic description if not provided as an argument.

Slugify the description: lowercase, spaces → hyphens, keep only alphanumeric and hyphens, truncate to 40 chars. Prefix with `epic-`.

Example: "user authentication system" → `epic-user-authentication-system`

Create the epic folder: `pipeline/epic-[slug]/`
Create `pipeline/epic-[slug]/state.md` with the header:

```markdown
# Epic State: epic-[slug]

**Epic:** [original epic description]
**Started:** [date]
**Status:** in_progress
```

Read `agent-config.yml` for role configs.

---

## Step 2: Epic Spec (Gate 0)

Activate the **Analyst** → skill: `to-spec` (or `research` + `to-spec` if the domain is unfamiliar).

**Analyst brief:**
- Read the epic description
- Clarify the goal, scope boundaries, and non-goals
- Identify the high-level user needs the epic must satisfy
- Output: epic spec → `state.md#gate-0`

Write output to `state.md` under `## Gate 0: Epic Spec`.

Present to the user:
```
Epic spec ready. Review: pipeline/epic-[slug]/state.md#gate-0

Does this capture what you want? Type **yes** to proceed or describe what to change.
```

On reject: Analyst revises and re-presents.

---

## Step 3: Feature Breakdown (Gate 1)

Activate the **Architect** → skill: `to-tickets`.

**Architect brief:**
- Read the epic spec from `state.md#gate-0`
- Decompose the epic into self-contained features, each independently buildable and deployable
- For each feature, produce: name, one-line description, complexity (small / medium / large), and any blocking dependencies on other features
- Declare the recommended execution sequence (sequential or parallel where independent)
- Output: feature breakdown table → `state.md#gate-1`

Write output to `state.md` under `## Gate 1: Feature Breakdown`:

```markdown
## Gate 1: Feature Breakdown

| # | Feature | Description | Complexity | Depends On | Est. Duration | Est. Cost |
|---|---|---|---|---|---|---|
| 1 | [name] | [description] | small | — | ~8–15 min | ~$0.05–$0.12 |
| 2 | [name] | [description] | medium | 1 | ~20–38 min | ~$0.12–$0.28 |

**Execution sequence:** [sequential | parallel where noted]

**Epic totals (sequential path):** ~[sum of all durations] min | ~$[sum of all costs]
**Epic totals (parallel path):** ~[longest chain duration] min | ~$[sum of all costs]
**Combined cost cap:** $[max_cost_per_run × feature_count] (each feature run is capped independently)
```

Compute per-feature estimates using the Gate 0 Estimates rules in proj-protocol, applying each feature's complexity tier.

Present to the user:
```
Feature breakdown ready. Review: pipeline/epic-[slug]/state.md#gate-1

Does this breakdown look right? Type **yes** to proceed, add/remove features, or adjust dependencies.
```

On reject: Architect revises and re-presents.

---

## Step 4: Create Feature Runs

For each approved feature in the breakdown:

1. Slugify the feature name. Prefix with `feat-`.
2. Create `pipeline/feat-[slug]/state.md` with the header:

```markdown
# Pipeline State: feat-[slug]

**Task:** [feature description]
**Epic:** epic-[epic-slug]
**Started:** [date]
**Status:** pending
```

3. Append the feature to the epic tracking table in `pipeline/epic-[slug]/state.md` under `## Feature Runs`:

```markdown
## Feature Runs

| # | Feature | Run | Status | Worktree | PR |
|---|---|---|---|---|---|
| 1 | [feature name] | feat-[slug] | pending | — | — |
| 2 | [feature name] | feat-[slug] | pending | — | — |
```

Update `Worktree` column to `.worktrees/feat-[slug]` when created, `removed` when torn down.
Update `PR` column to the PR URL once the Coder opens it.

Log the epic plan to `pipeline/epic-[slug]/log.md`.

---

## Step 5: Execute Features in Architect-Defined Sequence

**Sequencing and dependency rules (Orchestrator's responsibility):**

Read `state.md#gate-1`. The Architect's breakdown table declares the execution order and the `Depends On` column for each feature.

Before starting any feature run:
1. Build a dependency graph from the `Depends On` column
2. A feature is **ready** when all features it depends on are `complete`
3. A feature is **blocked** when any of its dependencies are `in_progress` or `pending`
4. If `pipeline.parallel_execution: true` in `agent-config.yml`, start all ready (unblocked) features simultaneously; otherwise run one at a time in order
5. Re-evaluate readiness after each feature completes — unblock any features whose last dependency just closed

**For each ready feature run, the Orchestrator:**

1. Announces: "Starting feature [n/total]: **[feature name]** (`feat-[slug]`)"
2. Updates the feature's status to `in_progress` in the epic tracking table

3. **If `pipeline.worktree_isolation: true`** — create the worktree before activating the pipeline:
   ```bash
   git pull origin main          # ensure base is current
   git worktree add .worktrees/feat-[slug] -b feat-[slug]
   ```
   Record in `pipeline/feat-[slug]/state.md`:
   ```markdown
   ## Worktree
   **Path:** .worktrees/feat-[slug]
   **Branch:** feat-[slug]
   **Created:** [timestamp]
   **Status:** active
   ```
   For a wave of parallel features, create **all worktrees first** from the same `HEAD`, then activate the pipelines simultaneously — this guarantees they all start from an identical base:
   ```bash
   git pull origin main
   git worktree add .worktrees/feat-feature-a -b feat-feature-a
   git worktree add .worktrees/feat-feature-b -b feat-feature-b
   git worktree add .worktrees/feat-feature-c -b feat-feature-c
   # then activate all three pipelines in parallel
   ```

4. Invokes `/proj-new-feature` as a sub-skill, passing the existing run folder:
   - The pre-created `pipeline/feat-[slug]/state.md` is the run context — do not create a new one
   - Execute all `proj-new-feature` steps from Step 2 onward: Gate 0 plan → Analyst → [Designer] → Architect → Tester Ensemble → Coder → Tester Ensemble → Gate 3 → Release Documenter → Deployer
   - All gates within the feature run require the same human approval as a standalone `/proj-new-feature`

5. **Wave merge sequence** — when multiple features in the same wave complete:
   - Merge PRs one at a time, in order (lowest feature number first)
   - After each merge, run `git pull origin main` in the main checkout before merging the next
   - If a merge conflict is detected, follow the Conflict Detection rules in `proj-protocol` (Worktree Rules section)
   - Do NOT merge all PRs simultaneously — sequential merge prevents compounding conflicts

6. **Worktree teardown** — after each PR merges successfully:
   ```bash
   git worktree remove .worktrees/feat-[slug]
   ```
   Update `pipeline/feat-[slug]/state.md#worktree` status to `removed`.

7. On completion, updates the feature's status to `complete` in the epic tracking table
8. Logs the completion to `pipeline/epic-[slug]/log.md`
9. Announces: "Feature [n/total] complete. [remaining] remaining." then re-evaluates which features are now unblocked

If a feature run fails or is blocked, stop and escalate per proj-protocol escalation rules before proceeding to the next feature.

---

## Step 6: Epic Completion

When all features are `complete`:

1. Activate the **Release Documenter** with the full epic context:
   - Read all `signoff_package.md` files from each feature run
   - Compile a combined `pipeline/epic-[slug]/epic-signoff.md` summarizing all features, test results, and deploy confirmations

2. Update `pipeline/epic-[slug]/state.md` status to `complete`

3. Announce:

```
Epic complete: [epic description]

Features delivered:
[list each feature with its run name]

Epic signoff package: pipeline/epic-[slug]/epic-signoff.md
```
