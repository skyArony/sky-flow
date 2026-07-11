# Sky Flow Dependencies

Sky Flow ships a small install and readiness manager through `./install.sh`.

## Runtime

The core validator is written in TypeScript and runs directly on Node.js.

Default requirement:

- Node.js 24 or newer.

Quick check from the repository root:

```bash
node --version
node ./scripts/validate_flow.ts --root . "${SKY_FLOW_ROOT:-docs}/spec/tooling/sky-flow.md"
```

After installation, the same validator is also available under
`~/.agents/skills/sky-flow/scripts/validate_flow.ts`.

If your local `node` build cannot execute `.ts` entrypoints directly, use the
`tsx` fallback in the Optional Tooling section below.

## Install And Update

Use the repository root installer:

```bash
./install.sh
./install.sh --dry-run
./install.sh list
./install.sh doctor
./install.sh update
./install.sh to-claude-review
```

Installation layout:

- Claude reads `~/.claude/skills`.
- Codex reads `~/.agents/skills`.
- A separate `~/.codex/skills` directory is not required.
- Because Claude does not discover nested skills, it receives the suite entry
  and each callable child skill as direct links.
- Codex receives the suite entry once and discovers callable children through
  that root. `doctor` accepts current nested content through the suite symlink
  and compares each nested `SKILL.md` when the suite was installed by copy.
- Install/update removes redundant Codex child symlinks only when they point to
  the current checkout. Copied or foreign child paths fail readiness until the
  user explicitly replaces them with `--force`.
- Skill-level `install_targets` still apply. For example, `to-claude-review`
  installs only for Codex.
- Historical skills under `archive/skills/` use `SKILL.archived.md` and are not
  part of discovery, installation, update, or readiness checks.
- Root `--copy` installs omit `.git` and `archive`. Root symlink installs still
  expose the checkout as a filesystem tree, but archived files remain
  non-discoverable because they are not named `SKILL.md`.

After upgrading from a legacy release, run `./install.sh update` and then
`./install.sh doctor`. Install/update removes a retired symlink only when its
target proves that this checkout owns it. Retired copied directories or foreign
symlinks make readiness fail and are reported with exact paths and cleanup
commands; they are never deleted implicitly because ownership cannot be proven
safely.

`doctor` also compares copied active `SKILL.md` files with current source. A
`stale-copy` result is repaired explicitly with the command printed by doctor,
for example `./install.sh to-implement --copy --force --no-deps`.

## Runtime Config

Sky Flow keeps project-level runtime config small and environment-driven.

Supported variables:

- `SKY_FLOW_ROOT`: artifact root directory. Defaults to `docs`.
- `SKY_FLOW_LANG`: default artifact and skill output language.

Example:

```toml
[shell_environment_policy.set]
SKY_FLOW_ROOT = "docs"
SKY_FLOW_LANG = "简体中文"
```

## Optional Tooling

If a project must stay on an older Node runtime, you can run the validator
through `tsx` instead:

```bash
pnpm add -D tsx typescript
pnpm exec tsx ./scripts/validate_flow.ts --root . "${SKY_FLOW_ROOT:-docs}/spec/tooling/sky-flow.md"
```

## Project Adapter Slot

`to-infra` is still a project-provided adapter slot. Sky Flow core does not ship
project-specific infrastructure access, credentials, or observability queries.
Projects that need infra access should provide their own `to-infra` skill and
let it route into the project's approved tooling.
