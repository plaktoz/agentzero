# Pipeline Cleanup

Use this skill to clean up pipeline runs and maintain the project. Handles three cleanup types.

---

## Step 1: Show Cleanup Menu

Ask: "What would you like to clean up?"

Options:
1. **Remove a completed run** — delete a `pipeline/[run-name]/` folder after deployment is confirmed
2. **Abandon a stale run** — discard a pipeline run that was started but never completed
3. **All of the above** — run both cleanup types in sequence

Wait for the user's choice.

---

## Option 1: Remove Completed Run

List all subdirectories in `pipeline/` where `state.md` contains `**Status:** complete`. Group epics above their child feature runs (identified by the `**Epic:**` field in each feature run's `state.md`).

Show the list and ask: "Which completed run would you like to remove?"

On confirmation:
- **Epic run:** delete `pipeline/epic-[slug]/` and all child feature run folders listed in its `## Feature Runs` table. Report each deletion.
- **Standalone run:** delete `pipeline/[run-name]/` (including `state.md`, `log.md`, `design-preview.html`, and `signoff_package.md` if present).

Report: "Removed [run-name] (and [n] child feature runs)" or "Removed [run-name]".

---

## Option 2: Abandon a Stale Run

List all subdirectories in `pipeline/` where `state.md` contains `**Status:** in_progress` or `**Status:** pending`. Group epics above their child feature runs.

Show the list and ask: "Which run do you want to abandon?"

Warn: "This will permanently delete `pipeline/[run-name]/`[and all its child feature runs if epic]. Any uncommitted work will be lost. Type **yes** to confirm."

On confirmation:
- **Epic run:** delete `pipeline/epic-[slug]/` and all child feature run folders.
- **Standalone run:** delete `pipeline/[run-name]/`.

Report: "Abandoned [run-name]."

---

## Option 3: All of the Above

Run Options 1 and 2 in sequence. For each, if there is nothing to clean up, skip it and report "Nothing to clean up for this step."
