# Project Start

Run this skill when setting up this project for the first time.

---

## Step 1: Check Configuration

Read `agent-config.yml`. Look at the `deploy` section. If all values are still at their defaults (`none` / `local`), the project has not been configured yet — run Step 2. Otherwise skip to Step 2b.

---

## Step 2: Run Configuration Wizard

Announce: "Starting project setup. I'll ask you a few questions to configure deployment, then we'll finish setup."

Run the same wizard as `/proj-config` (ask the 5 questions, write the answers to `agent-config.yml`).

---

## Step 2b: Verify API Keys

Run `python scripts/check_providers.py`. If any configured provider returns an error, stop and tell the user:

"Provider [name] is not reachable. Set the environment variable [VAR_NAME] before running the pipeline."

Do not proceed past this step until all configured providers are reachable.

---

## Step 3: Verify Skill Dependencies

For every skill listed under each role in `agent-config.yml`, check that a matching directory or file exists in `.claude/skills/`. Report any missing skills:

"The following skills are listed in agent-config.yml but not installed: [list]. Install them with `npx skills@latest add [name]` or remove them from agent-config.yml before running the pipeline."

Do not block on this — surface the warning and continue.

---

## Step 4: Scaffold Project Vocabulary

Read `CONTEXT.md`. Check whether the `## Project Vocabulary` section still contains only the placeholder comment.

If yes, say:

"Let's define 5–10 key terms for this project. I'll add them to CONTEXT.md so every agent uses consistent names throughout the pipeline.

What are the main entities or concepts in this project? (e.g., the things your code creates, manages, or acts on)"

For each term the user provides, add an entry to the `## Project Vocabulary` section of `CONTEXT.md`:
```
**[term]** — [one sentence definition].
```

If the section is already populated, skip this step.

---

## Step 5: Confirm Ready

Announce:

"Setup complete. What would you like to work on first?

- `/proj-new-feature [description]` — build a new feature
- `/proj-fix-bug [description]` — fix a bug
- `/proj-refactor [description]` — refactor existing code"

Do not start a pipeline run from this skill. The user invokes the appropriate skill for their first task.
