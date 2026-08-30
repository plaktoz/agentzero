# Pipeline Cleanup

Use this skill to remove completed runs, abandon stale runs, and clean up orphaned git branches.

Read `proj-protocol` for shared rules.

---

## Step 1: Show Cleanup Menu

Ask: "What would you like to clean up?"

Options:
1. **Remove a completed run** — delete a `pipeline/[run-name]/` folder after deployment is confirmed
2. **Abandon a stale run** — discard a run that was started but never completed; closes its PR and deletes its branch
3. **Clean up orphaned branches** — list and optionally delete git branches with no active pipeline run
4. **All completed + stale** — run options 1 and 2 in sequence

Wait for the user's choice.

---

## Before Any Deletion: Show Cost Summary

For any run about to be deleted, first read its `log.md` and show:
```
Run: [run-name]
Status: [complete | in_progress | pending]
Total cost: $[sum of Cost (USD) column in log.md]  (cap was: $[max_cost_per_run])
Last checkpoint: [value from state.md]
PR: [URL from state.md#pr, or "none"]
Branch: [branch name from state.md#pr, or "none"]
```
Then ask for confirmation.

---

## Option 1: Remove a Completed Run

List all subdirectories in `pipeline/` where `state.md` contains `**Status:** complete`. Group epics above their child feature runs (identified by the `**Epic:**` field in each feature run's `state.md`).

Show the list with cost summaries and ask: "Which completed run would you like to remove?"

On confirmation:

**Check the worktree first (if worktree_isolation: true):**
1. Read `state.md#worktree` for the worktree path and status
2. If status is `active`: the worktree should have been removed after merge, but may linger
   - Check: `git worktree list | grep [run-name]`
   - If found: `git worktree remove .worktrees/[run-name]` (use `--force` only if confirmed by user)
3. If status is `removed` or `state.md#worktree` is absent: skip

**Check the PR/branch:**
1. Read `state.md#pr` for the PR URL and branch name
2. If a branch exists: check whether it has been merged — `git branch --merged main | grep [branch-name]`
   - If merged: delete the remote branch: `git push origin --delete [branch-name]`
   - If NOT merged: warn "Branch [branch-name] has not been merged into main. Deleting the folder will not remove the code. Delete the branch anyway?" — wait for confirmation before deleting

**Delete the folder:**
- **Epic run:** delete `pipeline/epic-[slug]/` and all child feature run folders listed in its `## Feature Runs` table. Report each deletion.
- **Standalone run:** delete `pipeline/[run-name]/` (including `state.md`, `log.md`, `design-preview.html`, `signoff_package.md` if present).

Report: "Removed [run-name] (branch deleted, $[cost] spent)."

**Do NOT delete:**
- `knowledge_base/` — permanent audit trail; never deleted by cleanup
- `eval/` — version history and scores; never deleted by cleanup
- `pipeline-log.md` — cross-run audit trail at project root; append a cleanup entry instead:
  ```
  | [timestamp] | cleanup | removed [run-name] | cost: $[sum] | branch: deleted |
  ```

---

## Option 2: Abandon a Stale Run

List all subdirectories in `pipeline/` where `state.md` contains `**Status:** in_progress` or `**Status:** pending`. Group epics above their child feature runs.

Show the list with cost summaries and ask: "Which run do you want to abandon?"

Warn:
```
⚠ Abandoning [run-name]:
  - pipeline/[run-name]/ will be permanently deleted
  - Worktree .worktrees/[run-name] will be force-removed (if active)
  - PR [url] will be closed (not merged)
  - Branch [branch-name] will be deleted
  - $[cost] spent on this run will not be recovered
  - Any uncommitted code on the branch will be lost

Type yes to confirm.
```

On confirmation:

1. **Remove the worktree** (if `worktree_isolation: true` and worktree is active):
   ```bash
   git worktree remove --force .worktrees/[run-name]
   ```
   Skip if `state.md#worktree` is absent or status is `removed`.
2. **Close the PR** (if open): `gh pr close [pr-url] --comment "Abandoned by proj-cleanup"`
3. **Delete the branch**: `git push origin --delete [branch-name]`
   - If branch does not exist remotely: skip silently
5. **Delete the folder:**
   - Epic run: delete `pipeline/epic-[slug]/` and all child feature run folders
   - Standalone run: delete `pipeline/[run-name]/`
6. **Invoke the `lessons` skill** — an abandoned run is a failure event. The Orchestrator runs Observe → Extract → Validate → Distill against the run's `log.md` and `state.md` before deleting them (read first, then delete).
7. **Log to `pipeline-log.md`**:
   ```
   | [timestamp] | cleanup | abandoned [run-name] | cost: $[cost] | branch: deleted | pr: closed |
   ```

Report: "Abandoned [run-name] (PR closed, branch deleted, lessons extracted)."

---

## Option 3: Clean Up Orphaned Branches and Worktrees

**Orphaned worktrees** — worktrees in `.worktrees/` with no active pipeline run:

```bash
git worktree list --porcelain | grep worktree | sed 's/worktree //'
```

For each `.worktrees/[name]` found, check whether `pipeline/[name]/state.md` exists and has `**Status:** in_progress`. If not found or status is `complete`/`pending`, it is orphaned.

Show orphaned worktrees and ask: "Remove all orphaned worktrees?"
On confirmation: `git worktree remove .worktrees/[name]` for each (use `--force` if uncommitted changes and user confirms).

**Orphaned branches** — git branches matching the pipeline naming pattern (`feat-*`, `fix-*`, `refactor-*`, `epic-*`) but with no corresponding folder in `pipeline/`.

1. List branches: `git branch -r | grep -E 'feat-|fix-|refactor-|epic-'`
2. For each branch, check whether `pipeline/[branch-name]/` exists
3. Show orphaned branches:
   ```
   Orphaned branches (no pipeline folder):
     origin/feat-old-experiment    (last commit: [date])
     origin/fix-unused-work        (last commit: [date])
   ```
4. Ask: "Delete all orphaned branches? (yes / list specific ones to keep)"
5. On confirmation: `git push origin --delete [branch-name]` for each

Also check for merged branches:
```
git branch -r --merged main | grep -E 'feat-|fix-|refactor-|epic-'
```
Offer to delete any merged pipeline branches that still exist remotely.

---

## Option 4: All Completed + Stale

Run Option 1 then Option 2 in sequence. For each, if there is nothing to clean up, skip it and report "Nothing to clean up for this step."
