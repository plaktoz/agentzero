# Product

## What this is

A reusable, copy-into-any-project template that turns a single Claude Code session into a structured, multi-role software development pipeline with human approval gates at every critical step.

## Goals

- Codify a repeatable SDLC process as configuration, not convention
- Prevent premature code by enforcing spec → design → tests → code order
- Make every pipeline run reviewable: all agent outputs are committed to git
- Self-improve over time: failures feed the knowledge base; the knowledge base constrains future runs

## Non-goals

- Does not manage infrastructure or provision environments
- Does not replace CI/CD — it hands off to existing deploy tooling
- Does not write project-specific business logic
- Does not operate without human gates — autonomous deployment is explicitly out of scope

## Success criteria

A user copies this template into a new project, runs `/proj-start`, gives a task, and the pipeline produces reviewed, tested, deployable code with no out-of-band coordination required.
