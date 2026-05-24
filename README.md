# Sky Flow

Sky Flow is a reusable workflow skill suite for file-backed specs, issues,
plans, tasks, acceptance, backlog, handoff, validation, and implementation
coordination.

The canonical source checkout lives here. Install it into common local runtimes
with:

```bash
bash scripts/install_user_symlinks.sh
```

That script keeps this repository as the source and creates user-level symlinks:

- `~/.agents/skills/sky-flow -> ~/Developer/Harness/sky-flow`
- `~/.claude/skills/sky-flow -> ~/.agents/skills/sky-flow`
- `~/.codex/skills/sky-flow -> ~/.agents/skills/sky-flow`

The copied design spec is available at `docs/spec/tooling/sky-flow.md`.
