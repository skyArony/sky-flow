# Sky Flow

Sky Flow is a lightweight, runtime-first workflow skill suite for durable specs, progressively elaborated milestones, optional implementation working memory, and real collaboration boundaries.

## Setup

```bash
./install.sh
```

Useful commands:

```bash
./install.sh --dry-run
./install.sh list
./install.sh doctor
./install.sh update
./install.sh to-claude-review
```

## Install Model

- Claude installs live under `~/.claude/skills`.
- Codex installs live under `~/.agents/skills`.
- Claude receives the suite entry and each callable child as direct links because it does not discover nested skills.
- Codex receives the suite entry once and discovers callable children through that root; `to-milestone` and `show-me` also get direct links for standalone invocation.
- Copy-mode freshness compares the complete managed subtree, including references and scripts.
- Skill-level `install_targets` remain effective; Codex-only skills stay out of Claude installs.
- Historical skills under `archive/skills/` are not discovered or installed.
- Retired symlinks are removed only when they provably belong to this checkout. Copied or foreign paths require explicit user cleanup.

## Execution Model

- Simple work runs directly in the native runtime.
- `$to-align` owns sustained, multi-round alignment before coding and delegates stable conclusions to `$to-spec`.
- `$to-spec` owns durable design, readiness, normative decisions, and the goal-level Progress snapshot.
- `$to-milestone` turns a large stable spec into a human-reviewed milestone tree. It creates only the current level, deepens selected branches, and stops at independently acceptable executable leaves.
- Invoke `/show-me <topic>` in Claude or `$show-me <topic>` in Codex for a standalone visual explanation; no spec or milestone is required.
- Sky Flow embeds HumanLayer’s `show-me` under `skills/show-me/`; `to-milestone` uses it to explain each approved leaf with a focused visual before implementation, choosing inline diagrams or HTML as appropriate.
- `$pick-goal` derives a portable runtime goal without creating a new document.
- `to-implement` executes a ready spec, derived goal, approved executable milestone, or active thin-plan resume locator.
- Simple and continuous work stays runtime-only. Long-running work may materialize a thin plan when cross-session recovery value exceeds maintenance cost.
- Tests, static checks, builds, real-path checks, and diff sanity remain native runtime responsibilities.
- Review, review loops, consolidation, knowledge capture, second-opinion review, multi-agent work, and durable acceptance remain explicit capabilities.

## Durable Documents

Sky Flow uses Skill-owned durable documents, not a central artifact registry or schema.

- Spec owns long-term intent, scope, requirements, external behavior, data semantics, authority, acceptance, architecture, and semantic Progress.
- Milestone owns staged outcomes, hierarchy, hard dependencies, review state, delivery status, and completion evidence.
- Thin plan owns optional cross-session implementation context and remains subordinate to its source spec.
- Issue, acceptance, backlog, and handoff are created only when their real collaboration boundaries apply.

Document metadata such as `artifact_type`, `status`, and source fields may be used by an owning Skill, but Sky Flow does not impose a global type whitelist, shared status enum, filename rule, reserved-field list, or repository-wide relationship graph. There is no mandatory central document validator; each Skill checks its own semantic contract at the point of use.

## Milestone Model

```text
stable spec
  ↓
first-level milestone proposal
  ↓ human approval
selected branch → direct children only
  ↓ human approval
executable leaf
  ↓ approved runtime plan
implementation + evidence
  ↓ human acceptance
leaf complete → parent roll-up → next frontier
```

Only hard dependencies are durable. The absence of a hard dependency makes a leaf eligible for parallel execution, but runtime still decides actual concurrency after checking shared contracts and write conflicts.

The design spec lives at `docs/spec/tooling/sky-flow.md`.
