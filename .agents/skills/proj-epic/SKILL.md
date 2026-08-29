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

| # | Feature | Description | Complexity | Depends On |
|---|---|---|---|---|
| 1 | [name] | [description] | small | — |
| 2 | [name] | [description] | medium | 1 |

**Execution sequence:** [sequential | parallel where noted]
```

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

| # | Feature | Run | Status |
|---|---|---|---|
| 1 | [feature name] | feat-[slug] | pending |
| 2 | [feature name] | feat-[slug] | pending |
```

Log the epic plan to `pipeline/epic-[slug]/log.md`.

---

## Step 5: Execute Features in Architect-Defined Sequence

Work through the feature runs in the order and sequence declared by the Architect in `state.md#gate-1`. Respect blocking dependencies — do not start a feature until all its declared dependencies are `complete`.

For each feature run:

1. Announce: "Starting feature [n/total]: **[feature name]** (`feat-[slug]`)"
2. Update the feature's status to `in_progress` in the epic tracking table
3. Execute the full `proj-new-feature` pipeline for this feature:
   - Gate 1: spec approval
   - Gate 2: design approval (if UI/UX)
   - Gate 3: test sign-off
   - Release Documenter → signoff_package.md
   - Deployer
4. On completion, update the feature's status to `complete` in the epic tracking table
5. Log the completion to `pipeline/epic-[slug]/log.md`
6. Announce: "Feature [n/total] complete. [remaining] remaining."

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
