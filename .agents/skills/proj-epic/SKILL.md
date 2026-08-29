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

## Step 2: Feature Decomposition (Gate 0)

Activate the **Analyst** to break the epic into individual features.

**Analyst brief:**
- Read the epic description
- Produce a feature breakdown: a numbered list of self-contained features, each with a one-line description and an estimated complexity (small / medium / large)
- Features must be independently buildable and deployable
- Output: feature breakdown → `state.md#feature-breakdown`

Write the breakdown to `state.md` under `## Gate 0: Feature Breakdown`.

Present to the user:

```
Epic: [epic description]

Proposed features:
1. [feature name] — [one-line description] ([complexity])
2. [feature name] — [one-line description] ([complexity])
...

Does this breakdown look right? Type **yes** to proceed, add/remove features, or rename any item.
```

On reject: Analyst revises and re-presents. Repeat until approved.

---

## Step 3: Create Feature Runs

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

## Step 4: Execute Features Sequentially

Work through the feature runs one at a time, in the order approved at Gate 0.

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

## Step 5: Epic Completion

When all features are `complete`:

1. Activate the **Release Documenter** with the full epic context:
   - Read all `signoff_package.md` files from each feature run
   - Compile a combined `pipeline/epic-[slug]/epic-signoff.md` summarising all features, test results, and deploy confirmations

2. Update `pipeline/epic-[slug]/state.md` status to `complete`

3. Announce:

```
Epic complete: [epic description]

Features delivered:
[list each feature with its run name]

Epic signoff package: pipeline/epic-[slug]/epic-signoff.md
```
