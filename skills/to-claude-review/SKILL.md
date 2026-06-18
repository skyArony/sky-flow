---
name: to-claude-review
description: >
  Codex-only review-first bridge into Claude Code through `claude-agent-acp`.
  Use when Codex wants a synchronous or detached second-opinion review with
  findings-first output while Codex keeps implementation ownership.
install_targets: [codex]
required:
  commands: [python3, claude, claude-agent-acp]
guidance:
  readiness:
    missing_required_commands:
      - Run `./install.sh {skill}` to auto-install supported runtime dependencies, then rerun `./install.sh doctor {skill}`.
      - If the `claude` command is missing, install and authenticate Claude Code, then rerun `./install.sh doctor {skill}`.
      - If `claude-agent-acp` is still missing after install, run `npm install -g @agentclientprotocol/claude-agent-acp`; if that fails due to permissions, try `npm install -g --prefix ~/.local @agentclientprotocol/claude-agent-acp` and add `~/.local/bin` to your `PATH`, or use a release binary, then rerun `./install.sh doctor {skill}`.
---

# To-Claude-Review

Use this skill from Codex when Claude Code should act as a review-only /
second-opinion bridge instead of a general implementation delegate.

`./install.sh to-claude-review` should auto-install the npm-backed
`claude-agent-acp` runtime when the machine already has npm, or a supported
package manager can install npm first.

## Good Fits

- review the current working tree and call out regression risk
- review one file or a small set of files before Codex changes them
- ask for a design critique, edge-case scan, or missing-test pass
- attach screenshots or artifacts for a read-only second opinion
- run a long review in the background and poll it by stable job id

## Avoid

- handing Claude direct implementation ownership
- treating this as a generic ACP session manager
- using it for broad autonomous migration work instead of review

## Quick Path

1. Use `<skill-dir>/scripts/claude_review.py`.
2. Default to `review`; `python3 .../claude_review.py --working-tree` works without an explicit subcommand.
3. Keep the review brief small and concrete: risk, question, or target area.
4. Prefer `--path` and `--working-tree` to keep the review scope explicit.
5. For long reviews, use `--detach` and manage them with `jobs`, `job-status`, `job-wait`, and `job-cancel`.
6. Keep Codex responsible for triage, code changes, and final decisions.

Read [review-inputs.md](references/review-inputs.md) only when you need a quick
reference for files, images, or detached-job examples.

## Common Commands

Review the current working tree:

```bash
python3 <skill-dir>/scripts/claude_review.py \
  --working-tree \
  --focus regression-risk
```

Review specific files with a tighter brief:

```bash
python3 <skill-dir>/scripts/claude_review.py \
  --path README.md \
  --path skill-mgr/SKILL.md \
  --brief "Check whether the review-first positioning is consistent across these docs." \
  --focus docs-consistency \
  --output-format json
```

Run a detached design review:

```bash
python3 <skill-dir>/scripts/claude_review.py \
  --brief-file review-brief.md \
  --path docs/spec/skill-suite-design.md \
  --detach
```

Inspect detached review jobs:

```bash
python3 <skill-dir>/scripts/claude_review.py jobs
python3 <skill-dir>/scripts/claude_review.py job-status latest
python3 <skill-dir>/scripts/claude_review.py job-wait <job-id>
python3 <skill-dir>/scripts/claude_review.py job-cancel <job-id>
```

## Output Contract

The default review prompt asks Claude to stay in review-only mode and respond in
this order:

1. Findings
2. Risks / Missing Tests
3. Open Questions
4. Recommendation

If Claude finds no material issue, it should say so explicitly and still note
residual risk.

## Important Boundaries

- This skill is review-first, not ACP-first.
- Codex stays responsible for whether Claude output is trusted, applied, or ignored.
- Default permission handling is conservative: `--permission-strategy plan`.
- Detached jobs remain a first-class path because they keep long reviews from blocking the main Codex session.
- Detached jobs default to `~/.codex/to-claude-review/jobs`; override with `TO_CLAUDE_REVIEW_JOB_ROOT` when needed.
