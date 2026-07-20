# Sky Flow

Sky Flow is a lightweight workflow skill suite centered on durable specs,
optional thin plans for long-running implementation, compact recovery
snapshots, and native runtime execution. File-backed artifacts are specs,
plans, issues, acceptance, backlog, and handoff.

## Setup

Install the suite and its callable child skills with:

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
- A separate `~/.codex/skills` layer is not needed.
- Claude receives the suite entry and each callable child as direct links
  because it does not discover nested skills.
- Codex receives the suite entry once and discovers callable children through
  that root; `doctor` validates nested symlink and copy-mode content through the
  same route instead of requiring redundant child links.
- Install/update removes a redundant Codex child symlink when it points to the
  current checkout. Copied or foreign child paths require explicit `--force`.
- Nested `install_targets` are still respected, so Codex-only skills such as
  `to-claude-review` stay out of Claude installs.
- Internal reviewer profiles use `PROFILE.md` and are loaded only by
  `to-review`; they are not exposed as top-level callable skills.
- Retired workflow skills live under `archive/skills/` as
  `SKILL.archived.md`; they are not discovered or installed.
- Root copy-mode installs omit `.git` and `archive`; source-mode symlinks can
  still see the checkout, but archived files remain non-discoverable because
  they are not named `SKILL.md`.

## Execution Model

- Simple work runs directly in the native runtime.
- Long-lived work starts from a ready spec.
- Spec alignment first establishes the foundation, classifies decision
  authority, closes the current decision frontier, and proves readiness. Only
  stable conclusions are persisted; the question tree stays in conversation.
- `$pick-goal` derives a portable runtime goal without creating an artifact.
  An explicit start hands a ready goal to `to-implement`, an alignment goal to
  `to-spec`, and leaves a blocked goal unstarted.
- `to-implement` dynamically executes a ready spec or its derived ready goal.
- Simple work, and complex work that remains continuous with cheap recovery,
  stays runtime-only. A runtime checklist is sufficient in those cases.
- When implementation is likely to span sessions or compaction, depends on
  costly-to-rediscover code facts, or must resume from concrete checkpoints,
  `to-implement` may create or continue one source-linked thin plan. It may
  materialize midway when those conditions appear.
- A directly supplied active plan is only a resume locator: `to-implement`
  resolves and validates its ready, unfinished source spec before continuing.
  Completed or abandoned plans are background, not resumable goals.
- A thin plan records only the current slice, useful code context, approach,
  local reversible decisions, compact progress, and reusable verification
  entry points. It is not authoritative and does not contain task graphs,
  owners, dependencies, parallel lanes, or agent/tool history.
- Only semantic outcomes, decisions, blockers, evidence, residual risk, and a
  goal-level resume target are written back to the spec `Progress` snapshot;
  code line numbers, per-file diffs, command/tool/agent history, and timelines
  stay out.
- Human gates, long-term blockers, and volatile transfer state use acceptance,
  backlog, and handoff only when those boundaries genuinely apply.
- Durable authoring and selection paths are explicit: use `$to-spec`,
  `$pick-goal`, `$to-issue`, `$to-backlog`, or `$to-handoff`; the runtime does
  not create those artifacts opportunistically. Thin plan materialization is
  the narrow exception owned by `to-implement` because it is execution working
  memory, not a new authoring workflow.
- Routine verification and test design stay in the native runtime: test ROI,
  stable seams, tests, static checks, builds, focused behavior checks, and diff
  sanity do not require workflow skills. Incident regressions stay inside
  `to-debug`. Review, review loops, consolidation, knowledge capture,
  second-opinion review, multi-agent work, and durable acceptance remain
  explicit `$skill` capabilities.
- A source spec can still require independent review or a human gate. The
  runtime satisfies that constraint with the smallest sufficient path instead
  of multiplying reviewers or repeating clean gates.

This release keeps the legacy file-backed execution topology retired while
reintroducing only a thin `plan` artifact as optional implementation working
memory. The old `to-plan`, task/step graph, owner/dependency/parallel topology,
and `plan/done` lifecycle remain retired.
`install` / `update` remove stale retired symlinks only when they provably point
to this checkout. `doctor` and update readiness also detect retired copied or
foreign installs and print their exact paths; those require explicit removal
because the installer cannot prove ownership safely.
For active copy-mode installs, `doctor` compares each managed skill subtree,
including referenced guidance and scripts, and reports `stale-copy` rather than
accepting incomplete or legacy instructions as ready.

The design spec lives at `docs/spec/tooling/sky-flow.md`.
