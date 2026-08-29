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

List all subdirectories in `pipeline/` where `state.md` contains `**Status:** complete`.

Show the list and ask: "Which completed run would you like to remove?"

On confirmation:
1. Delete `pipeline/[run-name]/` (including `state.md`, `log.md`, and `design-preview.html` if present)
2. Report: "Removed pipeline/[run-name]/"

---

## Option 2: Abandon a Stale Run

List all subdirectories in `pipeline/` where `state.md` contains `**Status:** in_progress`.

Show the list and ask: "Which in-progress run do you want to abandon?"

Warn: "This will permanently delete `pipeline/[run-name]/`. Any uncommitted work in this run will be lost. Type **yes** to confirm."

On confirmation:
1. Delete `pipeline/[run-name]/`
2. Report: "Abandoned pipeline/[run-name]/"

---

## Option 3: All of the Above

Run Options 1 and 2 in sequence. For each, if there is nothing to clean up, skip it and report "Nothing to clean up for this step."
