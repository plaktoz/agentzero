# Project Start

Run this skill when setting up this project for the first time.

---

## Step 1: Check Configuration

Read `agent-config.yml`. Look at the `deploy` section. If all values are still at their defaults (`none` / `local`), the project has not been configured yet — run Step 2. Otherwise skip to Step 3.

---

## Step 2: Run Configuration Wizard

Announce: "Starting project setup. I'll ask you a few questions to configure deployment, then you can start your first task."

Run the same wizard as `/proj-config` (ask the 5 questions, write the answers to `agent-config.yml`).

---

## Step 3: Confirm Ready

After configuration is confirmed (or if already configured), announce:

"Project is configured. What would you like to work on first?

- `/proj-new-feature [description]` — build a new feature
- `/proj-fix-bug [description]` — fix a bug
- `/proj-refactor [description]` — refactor existing code"

Do not start a pipeline run from this skill. The user invokes the appropriate skill for their first task.
