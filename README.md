# Sky Flow

Sky Flow is a lightweight workflow skill suite centered on durable specs with
compact Progress snapshots and native runtime execution. File-backed artifacts
are limited to specs, issues, acceptance, backlog, and handoff.

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
- `pick-goal` derives a portable runtime goal without creating an artifact.
  An explicit start hands a ready goal to `to-implement`, an alignment goal to
  `to-spec`, and leaves a blocked goal unstarted.
- `to-implement` dynamically executes a ready spec or its derived ready goal.
- Only semantic outcomes, decisions, blockers, evidence, residual risk, and a
  goal-level resume target are written back to the spec `Progress` snapshot;
  code line numbers, per-file diffs, command/tool/agent history, and timelines
  stay out.
- Human gates, long-term blockers, and volatile transfer state use acceptance,
  backlog, and handoff only when those boundaries genuinely apply.

This release intentionally removes the legacy file-backed execution topology.
`install` / `update` remove stale retired symlinks only when they provably point
to this checkout. `doctor` and update readiness also detect retired copied or
foreign installs and print their exact paths; those require explicit removal
because the installer cannot prove ownership safely.
For active copy-mode installs, `doctor` compares each installed `SKILL.md` with
the current source and reports `stale-copy` instead of accepting legacy
instructions as ready.

The design spec lives at `docs/spec/tooling/sky-flow.md`.
