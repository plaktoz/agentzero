# Golden Tests — analyst

Baseline tests for the analyst role. Run eval against these whenever the analyst model or `to-spec` skill changes.

---

## Test: analyst-01 — Spec contains all mandatory sections

**Input:**
```
You are the Analyst. Convert this requirement into a spec using the to-spec skill:

"Add a password reset flow. Users should be able to click 'Forgot password?' on the login page, enter their email, receive a reset link, and set a new password."
```

**Expected structural output:**
Output must contain all of these sections (in any order):
- `## Business Context`
- `## User Personas`
- `## Problem Statement`
- `## Solution`
- `## Success Metrics`
- `## User Stories`
- `## Acceptance Criteria`
- `## Implementation Decisions`
- `## Testing Decisions`
- `## Assumptions & Risks`
- `## Out of Scope`

**Expected behaviors:**
- User Stories use persona names defined in the User Personas section (not generic "user")
- Acceptance Criteria are in Given/When/Then format and are independently testable
- Success Metrics include at least one measurable outcome or instrumentation requirement
- Implementation Decisions do not include specific file paths or code snippets
- Out of Scope is non-empty and names at least one excluded capability
- Assumptions & Risks contains at least one assumption and one risk

**Execution check:** no

---

## Test: analyst-02 — Out-of-scope items are correctly redirected

**Input:**
```
You are the Analyst. A developer asked: "Can you add social login (Google/GitHub OAuth) to the spec while you're at it?"

You are currently writing the spec for: "Add a password reset flow."

What do you do?
```

**Expected structural output:**
- Output explicitly rejects adding social login to this spec
- Social login appears in `## Out of Scope`, not `## User Stories` or `## Acceptance Criteria`
- Output suggests social login as a separate feature request

**Expected behaviors:**
- Does not silently ignore the request
- Does not add social login acceptance criteria
- Acknowledges and redirects with a clear reason (separate scope, separate spec)

**Execution check:** no

---

## Test: analyst-03 — Success metrics include instrumentation when baseline unknown

**Input:**
```
You are the Analyst. Write the Success Metrics section for a new onboarding flow feature.

No analytics data is currently collected on the onboarding funnel. There is no current baseline.
```

**Expected structural output:**
- `## Success Metrics` section is present
- Because no baseline exists, output lists instrumentation requirements (what events must be tracked at launch)
- Does not fabricate baseline numbers

**Expected behaviors:**
- Does not leave Success Metrics empty
- Does not invent metrics ("currently 50% completion rate") when told no data exists
- Specifies concrete events to instrument (e.g. "onboarding_started", "onboarding_step_2_completed")

**Execution check:** no

---

## Test: analyst-04 — Acceptance criteria are independently testable

**Input:**
```
You are the Analyst. Write the Acceptance Criteria section for this requirement:

"Users should receive a password reset email within 2 minutes of requesting it."
```

**Expected structural output:**
- At least one criterion in Given/When/Then format
- Criteria are specific enough to write a test from without reading the rest of the spec

**Expected behaviors:**
- Criteria are not vague ("system works correctly")
- Criteria do not reference implementation details ("the Redis queue processes the job")
- At least one criterion covers the failure case (e.g. invalid email address, expired token)

**Execution check:** no
