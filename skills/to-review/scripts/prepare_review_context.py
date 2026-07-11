#!/usr/bin/env python3
"""Prepare a reusable, file-based review context for large or repeated reviews."""

from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path


def git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args], check=True, text=True, capture_output=True
    )
    return result.stdout


def untracked_diff(root: Path, paths: list[str]) -> str:
    chunks: list[str] = []
    for path in paths:
        result = subprocess.run(
            ["git", "-C", str(root), "diff", "--no-index", "--", os.devnull, path],
            check=False,
            text=True,
            capture_output=True,
        )
        if result.returncode not in (0, 1):
            raise subprocess.CalledProcessError(
                result.returncode, result.args, result.stdout, result.stderr
            )
        chunks.append(result.stdout)
    return "".join(chunks)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True, type=Path)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--spec", help="Source spec path")
    source.add_argument("--goal", help="Portable runtime-goal summary")
    parser.add_argument("--base", help="Base revision for a committed range")
    parser.add_argument("--head", default="HEAD", help="Head revision; default HEAD")
    parser.add_argument("--known-deviation", action="append", default=[])
    parser.add_argument("--non-goal", action="append", default=[])
    parser.add_argument("--evidence", action="append", default=[])
    return parser.parse_args()


def bullets(values: list[str]) -> str:
    return "\n".join(f"- {value}" for value in values) if values else "- none"


def main() -> None:
    args = parse_args()
    root = Path(git("rev-parse", "--show-toplevel").strip())
    output_dir = args.output_dir.resolve()
    if output_dir == root or root in output_dir.parents:
        raise SystemExit("--output-dir must be outside the repository")

    if args.base:
        scope = f"{args.base}..{args.head}"
        diff = git("diff", args.base, args.head)
        status = git("diff", "--name-status", args.base, args.head)
    else:
        scope = "pending worktree against HEAD"
        diff = git("diff", "HEAD")
        status = git("status", "--short")
        untracked = git("ls-files", "--others", "--exclude-standard").splitlines()
        diff += untracked_diff(root, untracked)

    output_dir.mkdir(parents=True, exist_ok=True)
    source = args.spec or args.goal
    context = f"""# Review Context

- Repository: {root}
- Scope: {scope}
- Source spec / runtime goal: {source}
- Diff file: {output_dir / 'changes.diff'}

## Changed Paths

```text
{status.rstrip() or 'none'}
```

## Known Deviations

{bullets(args.known_deviation)}

## Non-goals

{bullets(args.non_goal)}

## Existing Evidence

{bullets(args.evidence)}

## Reviewer Contract

- Read the source spec / runtime goal and changed files; do not infer intent from the diff alone.
- Return both design / spec compliance and code-quality conclusions.
- Report findings first, with trigger path, impact, evidence, repair cost, and confidence.
- State what could not be verified.
"""

    (output_dir / "changes.diff").write_text(diff, encoding="utf-8")
    (output_dir / "review-context.md").write_text(context, encoding="utf-8")


if __name__ == "__main__":
    main()
