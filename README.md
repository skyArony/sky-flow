# Sky Flow

Sky Flow is a reusable workflow skill suite for file-backed specs, issues,
plans, tasks, acceptance, backlog, handoff, validation, and implementation
coordination.

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
- The installer links the suite entry skill and each callable child skill
  separately, because Claude does not discover nested skills.
- Nested `install_targets` are still respected, so Codex-only skills such as
  `to-claude-review` stay out of Claude installs.

The design spec lives at `docs/spec/tooling/sky-flow.md`.
