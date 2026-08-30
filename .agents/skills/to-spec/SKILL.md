---
name: to-spec
description: Turn the current conversation into a spec and publish it to the project issue tracker — no interview, just synthesis of what you've already discussed.
disable-model-invocation: true
---

This skill takes the current conversation context and codebase understanding and produces a spec (you may know this document as a PRD). Do NOT interview the user — just synthesize what you already know.

The issue tracker and triage label vocabulary should have been provided to you — run `/setup-matt-pocock-skills` if not.

## Process

1. Explore the repo to understand the current state of the codebase, if you haven't already. Use the project's domain glossary vocabulary throughout the spec, and respect any ADRs in the area you're touching.

2. Sketch out the seams at which you're going to test the feature. Existing seams should be preferred to new ones. Use the highest seam possible. If new seams are needed, propose them at the highest point you can. The fewer seams across the codebase, the better - the ideal number is one.

Check with the user that these seams match their expectations.

3. Write the spec using the template below, then publish it to the project issue tracker. Apply the `ready-for-agent` triage label - no need for additional triage.

<spec-template>

## Business Context

Why this work matters to the business or product. One short paragraph. Include:
- The strategic goal or business driver behind this feature/change
- The cost of not doing it (lost revenue, user churn, compliance risk, technical debt, etc.)
- Any deadline or external forcing function (regulatory date, launch date, partner dependency)

Omit if there is genuinely no business context beyond "developer quality-of-life".

## User Personas

A brief description of each distinct user type affected by this feature. One bullet per persona.
Format: **[Persona name]** — [one sentence describing who they are and their relevant context]

Example:
- **Guest shopper** — unauthenticated user browsing the storefront; cannot save a cart between sessions
- **Returning customer** — authenticated user with order history; expects a personalised experience

Use these persona names consistently in User Stories.

## Problem Statement

The problem that each persona is facing, from their perspective. Reference personas by name.
If all personas share the same problem, a single paragraph is fine.

## Solution

The proposed solution, from the user's perspective. No implementation detail — describe what users can do, not how the system does it.

## Success Metrics

How we will know this feature succeeded. List 2–5 measurable outcomes.
Format: **[Metric]** — [current baseline if known] → [target]

Examples:
- **Password reset completion rate** — unknown baseline → ≥ 80% of initiated resets completed within 30 min
- **Support tickets tagged "can't log in"** — 120/month → < 40/month within 60 days of launch
- **Time to reset** — n/a → p95 < 2 minutes end-to-end

If metrics cannot be defined yet, list the instrumentation that must be in place at launch (so they can be measured later).

## User Stories

A LONG, numbered list of user stories. Each user story should be in the format of:

1. As a <persona>, I want <feature>, so that <benefit>

<user-story-example>
1. As a returning customer, I want to reset my password without contacting support, so that I can regain access to my account immediately
</user-story-example>

Use persona names from the User Personas section. This list should be extensive and cover the happy path, error states, and edge cases.

## Acceptance Criteria

A numbered list of testable pass/fail conditions that define "done" for this spec. Each criterion must be independently verifiable.

Format: **[n].** Given [context], when [action], then [outcome].

These are the criteria the Tester Ensemble will write tests against. Be specific enough that a developer who has not read the rest of the spec could write a test from the criterion alone.

## Implementation Decisions

A list of implementation decisions that were made. This can include:

- The modules that will be built/modified
- The interfaces of those modules that will be modified
- Technical clarifications from the developer
- Architectural decisions
- Schema changes
- API contracts
- Specific interactions

Do NOT include specific file paths or code snippets. They may end up being outdated very quickly.

Exception: if a prototype produced a snippet that encodes a decision more precisely than prose can (state machine, reducer, schema, type shape), inline it within the relevant decision and note briefly that it came from a prototype. Trim to the decision-rich parts — not a working demo, just the important bits.

## Testing Decisions

A list of testing decisions that were made. Include:

- A description of what makes a good test (only test external behavior, not implementation details)
- Which modules will be tested
- Prior art for the tests (i.e. similar types of tests in the codebase)

## Assumptions & Risks

**Assumptions** — things we are treating as true without verification. If any assumption turns out to be wrong, the spec may need revision.

**Risks** — things that could prevent successful delivery or adoption. Include mitigation where known.

Format:
- **Assumption:** [statement]
- **Risk:** [what could go wrong] — Mitigation: [how we reduce the probability or impact]

## Out of Scope

A description of the things that are explicitly out of scope for this spec. Be specific — "social login" not "other auth methods".

## Further Notes

Any further notes about the feature.

</spec-template>
