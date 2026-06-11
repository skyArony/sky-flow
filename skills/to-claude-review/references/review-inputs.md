# Review Inputs

Use this reference when the review needs a tighter scope than “look at the
current working tree”.

## Working Tree Review

```bash
python3 <skill-dir>/scripts/claude_review.py \
  --working-tree \
  --focus regression-risk
```

## Targeted File Review

```bash
python3 <skill-dir>/scripts/claude_review.py \
  --path README.md \
  --path skill-mgr/SKILL.md \
  --brief "Check whether the review-first positioning is consistent across these docs." \
  --focus docs-consistency
```

## Design Review

```bash
python3 <skill-dir>/scripts/claude_review.py \
  --brief-file review-brief.md \
  --path docs/spec/skill-suite-design.md \
  --focus design-risk \
  --focus open-questions
```

## Screenshot Review

```bash
python3 <skill-dir>/scripts/claude_review.py \
  --image-file screenshot.png \
  --brief "Describe the broken state and call out the most likely UI regression."
```

## Detached Review

```bash
python3 <skill-dir>/scripts/claude_review.py \
  --working-tree \
  --brief "Focus on correctness, migration risk, and missing tests." \
  --detach
```

Poll a detached review later:

```bash
python3 <skill-dir>/scripts/claude_review.py job-status latest
python3 <skill-dir>/scripts/claude_review.py job-wait <job-id>
```

## Notes

- Keep briefs concrete; a smaller question usually yields a stronger review.
- `--path` is additive: use it to highlight the files or directories Claude should prioritize.
- `--working-tree` and `--path` can be combined.
- Detached jobs default to `~/.codex/to-claude-review/jobs`; override with `TO_CLAUDE_REVIEW_JOB_ROOT` when needed.
