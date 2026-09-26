# Research: poteto/noodle vs mattpocock/skills — Comparative Analysis
*Generated: 2026-09-26 | Scope: tabulated feature comparison of two agent skill frameworks, pros/cons of each, and practical design patterns applicable to new projects, bug fixing, research, and learning workflows*

## Research Outline

1. What each is — origin, problem solved, target audience, core philosophy
2. Architecture & tech stack — data models, key abstractions, folder structure
3. Feature matrix — tabulated side-by-side common and unique features
4. Pros, cons, and trade-offs — where each shines, what to question
5. Practical takeaways — design patterns for new projects, bugs, research, learning

---

## 1. What Each Is

### poteto/noodle

- **Source**: https://github.com/poteto/noodle
- **Author**: Lauren Tan (poteto), Staff Software Engineer @ Meta, previously React core team
- **Summary**: A Go CLI binary that implements a **skill-based autonomous agent orchestration loop**. It reads project state, dispatches agents to isolated git worktrees to execute skills, collects results, and loops — unattended if configured for `auto` mode. Kitchen brigade metaphor: the scheduler is the head chef, agents are line cooks.
- **Problem solved**: Parallel, unattended multi-agent execution across a backlog of tasks, where agents must not step on each other's work, produce reviewable outputs, and self-improve over time.
- **Target audience**: Teams and individuals running long-horizon, unattended coding agents across large backlogs — essentially "agent CI/CD".
- **Philosophy**: Skills describe **how** to work. Orders tell agents **what** to do. Those concerns stay separate at all times. Context window is a finite shared resource — load only what's needed, when it's needed.

### mattpocock/skills

- **Source**: https://github.com/mattpocock/skills/tree/main
- **Author**: Matt Pocock, TypeScript educator (Total TypeScript), author of widely-used ts-reset and zod-error libraries
- **Summary**: A curated library of **Claude Code slash-command skills** encoding real engineering practices — grilling, TDD, bug diagnosis, code review, architecture improvement, domain modeling, teaching — as hackable Markdown files with no runtime binary.
- **Problem solved**: AI coding agents that produce misaligned, verbose, architecturally fragile, or untestable code because they lack engineering discipline. Each skill targets a specific failure mode.
- **Target audience**: Individual developers who want to raise the quality floor of their AI-assisted coding without losing control to a framework.
- **Philosophy**: Small, composable, hackable. Works with any model. "Developing real applications is hard. These skills are designed to be small, easy to adapt, and composable." You subscribe (Claude Code plugin) or fork (npx install) based on how much you want to customize.

---

## 2. Architecture & Tech Stack

### poteto/noodle

| Layer | What it is |
|-------|------------|
| **Binary** | Go CLI (`noodle`) — `brew install poteto/tap/noodle` |
| **Config** | `.noodle.toml` — provider, model, skill paths, runtime, concurrency, server |
| **Project state** | `.noodle/mise.json` — backlog, task_types, active agents, recent_events, resources |
| **Orders (next)** | `.noodle/orders-next.json` — scheduler writes this; stages pipeline per backlog item |
| **Orders (live)** | `.noodle/orders.json` — promoted atomically from orders-next; dispatched to agents |
| **Skills** | `.agents/skills/<name>/SKILL.md` — YAML frontmatter + Markdown body |
| **Worktrees** | Isolated git worktrees per agent session — no file conflicts during parallel work |
| **Runtimes** | `process` (local), `sprites` (sprites.dev cloud sandbox), `cursor` (Cursor cloud) |
| **Memory** | `brain/` vault via optional brainmaxxing add-on — reflect/meditate/ruminate skills |
| **Backlog** | `todos.md` default; adapters for GitHub Issues, Linear, Jira |
| **Server** | Optional web UI at port 3000 |

**Skill directory anatomy**:
```
skill-name/
├── SKILL.md          ← required: frontmatter + body
├── references/       ← loaded on demand (docs, guides)
├── scripts/          ← deterministic executables
└── assets/           ← output files, not loaded into context
```

**Three-level context loading** — the key budget discipline:
1. Metadata (`name`, `description`, `schedule`) — always in context (~100 words)
2. `SKILL.md` body — loaded only after the skill triggers (<5k words)
3. `references/` and `scripts/` — loaded on demand by the agent

**Orders pipeline — stage types**:
- **Sequential**: execute → quality → reflect (most common)
- **Parallel groups**: lint + test in group 1, deploy in group 2
- **Prepended stage**: debate/plan before execute
- **Standalone**: periodic/event-driven (meditate, reflect sweeps)

**Modes**: `auto` (full automation), `supervised` (human approves merges), `manual` (human triggers everything)

### mattpocock/skills

| Layer | What it is |
|-------|------------|
| **Runtime** | None — pure Claude Code slash commands |
| **Skill format** | `SKILL.md` with YAML frontmatter (`name`, `description`, optional `argument-hint`, `disable-model-invocation`) |
| **Installation** | Claude Code plugin (`claude plugins install mattpocock-skills`) or `npx skills@latest add` |
| **Domain model** | `CONTEXT.md` — shared language doc; reduces verbosity, consistent naming, fewer tokens |
| **ADRs** | Architectural Decision Records — non-obvious decisions documented inline |
| **Skill composition** | `Call the Skill tool with "X"` — user-invoked skills compose model-invoked ones |
| **State** | `CONTEXT.md` + ADRs + `learning-records/` + `NOTES.md` across sessions |
| **Teaching workspace** | `MISSION.md`, `reference/*.html`, `lessons/*.html`, `assets/` — `/teach` creates and maintains these |

**User-invoked vs model-invoked** — the key routing distinction:
- **User-invoked**: triggered by typing the slash command (e.g. `/grill-me`, `/tdd`) — they orchestrate
- **Model-invoked**: triggered by the agent automatically when the task fits (e.g. `diagnosing-bugs`, `research`, `codebase-design`) — they hold reusable discipline
- A user-invoked skill may invoke model-invoked skills, but never another user-invoked one

---

## 3. Feature Matrix

### Common features (both have)

| Feature | poteto/noodle | mattpocock/skills |
|---------|--------------|-------------------|
| **Skill format** | `SKILL.md` + YAML frontmatter + body | `SKILL.md` + YAML frontmatter + body |
| **Skill description as trigger** | `description:` field = primary routing signal | `description:` field = Claude Code routing signal |
| **Composable skills** | Stage pipelines chain skills sequentially/in parallel | `Call the Skill tool with "X"` chains skills |
| **Context budget discipline** | 3-level loading: metadata → body → references | Short SKILL.md + `references/` pattern |
| **Bug fixing workflow** | `execute` skill (implements fix) | `/diagnosing-bugs` (feedback-loop-first discipline) |
| **Code review** | `quality` skill | `/code-review` (two-axis: standards + spec) |
| **Architecture improvement** | Domain/workflow skills for codebase context | `/improve-codebase-architecture` + `/codebase-design` |
| **Research capability** | `research` background agent | `/research` model-invoked skill |
| **Domain modeling** | `domain-modeling` skill (via brainmaxxing) | `/grill-with-docs` builds CONTEXT.md + ADRs |
| **Planning / project breakdown** | `orders-next.json` stage pipeline | `/to-spec` + `/to-tickets` + `/wayfinder` |
| **Multi-agent memory** | `brain/` vault (reflect/meditate) | `CONTEXT.md` + ADRs + learning records |

### Unique to noodle

| Feature | Detail |
|---------|--------|
| **Autonomous scheduling loop** | `noodle start` — runs unattended, scheduler reads mise, writes orders |
| **Worktree isolation** | Each agent session gets its own git worktree — parallel agents can't conflict |
| **Multi-provider routing** | Per-stage `provider` + `model` — e.g. Codex executes, Claude reviews |
| **Cloud sandbox runtimes** | sprites.dev (up to 50 concurrent), Cursor cloud agents |
| **Structured order schema** | JSON schema for orders: `id`, `title`, `plan`, `rationale`, `stages[]` |
| **Backlog adapters** | GitHub Issues, Linear, Jira sync via adapter shell scripts |
| **Event system** | `noodle event emit <type>` — inject external events into the loop |
| **Web UI / server** | Optional dashboard at port 3000 |
| **Go binary** | Single binary install, fast, reproducible across machines |

### Unique to mattpocock/skills

| Feature | Detail |
|---------|--------|
| **Shared language (CONTEXT.md)** | DDD-inspired project glossary — consistent naming, fewer agent tokens |
| **TDD discipline** | Red-green-refactor with seam discipline, anti-pattern guard, vertical slices |
| **Feedback-loop-first debugging** | `/diagnosing-bugs` Phase 1 = build tight red-capable feedback loop before hypothesising |
| **Teaching workspace** | `/teach` — stateful multi-session MISSION.md + lessons + learning records |
| **Grilling primitive** | `grilling` model-invoked skill — every alignment skill delegates to this |
| **Handoff document** | `/handoff` — compact conversation for a fresh agent to continue |
| **Wait-what** | `/wait-what` — re-pitches a confusing message in plain English using CONTEXT.md vocab |
| **Questionnaire** | `/to-questionnaire` — async decision doc for a collaborator |
| **Zero install option** | Works anywhere Claude Code works via plugin marketplace |

---

## 4. Pros, Cons, and Trade-offs

### poteto/noodle

**Pros**
- **Autonomous, unattended execution** — run a backlog overnight; the loop schedules and dispatches without you
- **Worktree safety** — parallel agents work in isolation; no merge conflicts or race conditions on files
- **Multi-provider pipeline** — Codex for raw implementation, Claude for quality review in the same order pipeline; use the right model for each stage
- **Cloud execution** — sprites.dev integration means you don't need a local machine running for long jobs
- **Structured state** — `mise.json` + `orders.json` gives you a machine-readable snapshot of project state at any point; introspectable, resumable
- **Three-level context loading** — explicit discipline for staying within context budget across many concurrent agents
- **Scales horizontally** — up to 50 concurrent sprite sessions; real parallelism for large backlogs

**Cons**
- **High setup friction** — binary install, `.noodle.toml`, adapter scripts, backlog format, INSTALL.md is the onboarding, not a 30-second CLI
- **Kitchen brigade abstraction can confuse** — the mise/orders/worktree metaphor requires mental re-mapping before it becomes intuitive
- **Go dependency** — binary distribution, not a pure-JS/Python project you can inspect and hack in your primary language
- **Less engineering philosophy** — noodle is a runtime/framework; the skill content for code quality, TDD, and design is sparser than mattpocock's
- **Overkill for solo projects** — supervised/manual mode with one agent loses most of the value; designed for sustained unattended work
- **Lock-in risk** — sprites.dev, Cursor adapters, custom backlog adapters; switching runtime is non-trivial

### mattpocock/skills

**Pros**
- **Zero runtime** — install once, works everywhere Claude Code is running; no binary, no toml, no server
- **Hackable by design** — `npx skills@latest add` copies the source files; you own them, you change them
- **Richest engineering philosophy** — every skill traces to a real book (Pragmatic Programmer, DDD, XP Explained, Philosophy of Software Design); the *why* is explicit
- **Shared language is a killer feature** — CONTEXT.md reduces verbosity, builds consistent naming, and makes the agent faster because it spends fewer tokens decoding jargon
- **Feedback-loop-first debugging** — Phase 1 of `/diagnosing-bugs` is the hardest thing to internalize: build a tight, red-capable feedback loop *before* hypothesising; this alone prevents 80% of wasted debugging sessions
- **Teaching workspace** — `/teach` is a genuine learning system: MISSION.md, HTML lessons, learning records, reference docs; comparable to a mini LMS
- **Grilling as alignment primitive** — `grilling` shows up inside 5 different skills; it's not a feature, it's the foundation

**Cons**
- **No autonomous loop** — everything is user-triggered; you can't schedule a backlog run overnight
- **No worktree management** — no built-in parallel isolation; if two skills modify the same file concurrently, you manage that yourself
- **Claude Code-native** — the plugin marketplace is Claude-specific; adapting to Codex or other agents requires `npx skills@latest add` and manual rewriting
- **No multi-provider routing** — all agents run on whatever model Claude Code is configured with; no per-stage model selection
- **No structured project state** — project state lives in `CONTEXT.md`, ADRs, and issue trackers but there's no machine-readable state file; harder to resume or introspect programmatically
- **Skill discovery is implicit** — no `noodle skills list` equivalent; you learn what exists from the README

---

## 5. Practical Takeaways

### For new projects

| Pattern | Source | How to apply |
|---------|--------|--------------|
| **Start with a grilling session** | mattpocock `/grill-with-docs` | Before writing any code, run the grilling session to build alignment and create CONTEXT.md. This single file pays for itself every session. |
| **Write a CONTEXT.md on day one** | mattpocock `domain-modeling` | Document 10–20 project-specific terms. Reduces agent verbosity and ensures consistent naming across files. |
| **Create ADRs for non-obvious decisions** | mattpocock `grill-with-docs` | Every time you choose a pattern, library, or trade-off that a new reader would question, write an ADR. The agent respects these in future sessions. |
| **Structure skills as process, not tasks** | noodle skill authoring | Any recurring workflow (deploy, test, review) should be a skill file. The skill body is instructions; the order/prompt is the specific task. Never bake task details into skill bodies. |
| **Plan the MISSION before building** | mattpocock `/teach` MISSION.md | Even for non-learning projects, a MISSION.md forcing the question "what changes when this is done?" prevents scope creep. |
| **Keep SKILL.md under 500 lines** | noodle skill authoring | Split long skills into `references/` loaded on demand. The three-level loading pattern is valid for any context-aware agent system. |
| **Design a stage pipeline for complex work** | noodle orders schema | For any work that benefits from: implementation → review → reflection, design it as an explicit stage pipeline up front. Name the stages; make them composable. |

### For bug fixing

| Pattern | Source | How to apply |
|---------|--------|--------------|
| **Build the feedback loop first** | mattpocock `/diagnosing-bugs` Phase 1 | Before reading code or forming hypotheses, build one tight, deterministic, agent-runnable command that goes red on this specific bug. No red-capable command = no Phase 2. |
| **Tighten the loop** | mattpocock `/diagnosing-bugs` | Once you have a loop, reduce runtime to seconds, sharpen the assertion, eliminate flakiness. A 2-second deterministic loop is a debugging superpower. |
| **Minimize to the smallest repro** | mattpocock `/diagnosing-bugs` Phase 2 | Cut inputs, callers, config, data one at a time. Each cut reduces noise. The minimal repro is where the fix becomes obvious. |
| **Prepend a debate/plan stage for hard bugs** | noodle orders schema | For complex bugs with multiple plausible causes, add a `debate` stage before `execute` — the agent argues competing hypotheses before picking one. |
| **Regression-test before closing** | mattpocock `/diagnosing-bugs` | The feedback loop you built to find the bug becomes the regression test. Write it as a permanent test at the appropriate seam. |

### For researching a topic

| Pattern | Source | How to apply |
|---------|--------|--------------|
| **Spin up a background research agent** | mattpocock `research` model-invoked | The `research` skill runs as a background agent against primary sources (docs, source code, specs) — not secondary summaries. Every claim cites its source. |
| **Use grilling to sharpen the question** | mattpocock `grilling` | Vague research questions produce vague answers. The `grilling` skill — running inside research scoping — forces every branch of the question to resolve before fetching. |
| **Store findings in the repo** | mattpocock `research` | Research findings live in the repo alongside the code they inform — not in a Notion page you'll lose track of. |
| **Use brainmaxxing `reflect` for retention** | noodle brainmaxxing | After a research cycle, a `reflect` skill captures learnings into the `brain/` vault — compress what you learned before the session context closes. |

### For learning

| Pattern | Source | How to apply |
|---------|--------|--------------|
| **Write a MISSION.md before the first lesson** | mattpocock `/teach` | Ground all lessons in the outcome you want. "To understand X" is weak. "To build Y by doing Z" is a mission. Every lesson maps to the mission. |
| **Generate HTML lessons, not notes** | mattpocock `/teach` | Lessons should be beautiful, self-contained, and completable quickly. A lesson is not a note dump — it's a single tangible win per session. |
| **Build a reference library alongside lessons** | mattpocock `/teach` | `reference/*.html` = cheat sheets, glossaries, syntax references. These are the compressed permanent output; lessons are the active learning; references are what you reach for later. |
| **Keep learning records** | mattpocock `/teach` | `learning-records/` capture non-obvious insights and revised mental models. Equivalent to ADRs for learning — the things that changed your understanding, not just summaries. |
| **Space practice and use retrieval** | mattpocock `/teach` philosophy | Design lessons for storage strength (long-term retention) not fluency (in-the-moment recall). Retrieval practice + spacing > re-reading. |

---

## Summary Comparison

| Dimension | poteto/noodle | mattpocock/skills |
|-----------|--------------|-------------------|
| **Core value** | Autonomous multi-agent orchestration | Engineering discipline for AI-assisted coding |
| **Best for** | Sustained unattended work across large backlogs | Daily coding sessions with quality guardrails |
| **Skill format** | SKILL.md + frontmatter (same idea) | SKILL.md + frontmatter (same idea) |
| **Composition model** | Stage pipelines in `orders-next.json` | `Call the Skill tool with "X"` |
| **State** | Machine-readable `mise.json` | Human-readable `CONTEXT.md` + ADRs |
| **Parallelism** | Worktree-isolated, up to 50 concurrent | None built-in |
| **Memory** | `brain/` vault (brainmaxxing add-on) | `CONTEXT.md` + ADRs + learning records |
| **Install** | Go binary + config | Claude Code plugin or npx |
| **Hackability** | Low (binary runtime) | High (own the source files) |
| **Engineering philosophy depth** | Low (framework) | High (books cited, principles named) |
| **Learning/teaching support** | None | Full teaching workspace (`/teach`) |
| **Autonomous execution** | Yes | No |

**When to reach for noodle**: large ongoing project, want unattended overnight runs, parallel agents on different tickets, multi-model pipeline (Codex implements, Claude reviews).

**When to reach for mattpocock/skills**: daily coding sessions, want alignment before every change, need TDD discipline or a bug-fixing framework, building a learning system alongside the code.

**Steal from both**: the three-level context loading pattern (metadata → body → references) from noodle is universally applicable. The shared language (CONTEXT.md) + grilling + feedback-loop-first debugging from mattpocock are the three highest-ROI skills for any AI-assisted project.

---

## Articles to Ingest

URLs ready for `/kb-scrapecontent` → `/kb-ingest`:

- https://github.com/poteto/noodle
- https://raw.githubusercontent.com/poteto/noodle/main/INSTALL.md
- https://github.com/mattpocock/skills/tree/main
