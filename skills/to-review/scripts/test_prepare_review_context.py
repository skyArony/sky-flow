#!/usr/bin/env python3

from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("prepare_review_context.py")


class PrepareReviewContextTest(unittest.TestCase):
    def run_cmd(self, cwd: Path, *args: str) -> None:
        subprocess.run(args, cwd=cwd, check=True, text=True, capture_output=True)

    def test_pending_worktree_context(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            base = Path(raw)
            repo = base / "repo"
            repo.mkdir()
            self.run_cmd(repo, "git", "init", "-q")
            self.run_cmd(repo, "git", "config", "user.name", "Sky Flow Test")
            self.run_cmd(repo, "git", "config", "user.email", "sky-flow@example.test")
            (repo / "source.md").write_text("before\n", encoding="utf-8")
            self.run_cmd(repo, "git", "add", "source.md")
            self.run_cmd(repo, "git", "commit", "-qm", "initial")
            (repo / "source.md").write_text("after\n", encoding="utf-8")
            (repo / "new.md").write_text("new file\n", encoding="utf-8")

            output = base / "review"
            self.run_cmd(
                repo,
                "python3",
                str(SCRIPT),
                "--output-dir",
                str(output),
                "--spec",
                "docs/spec/example.md",
                "--evidence",
                "unit tests pass",
            )

            context = (output / "review-context.md").read_text(encoding="utf-8")
            diff = (output / "changes.diff").read_text(encoding="utf-8")
            self.assertIn("docs/spec/example.md", context)
            self.assertIn("source.md", context)
            self.assertIn("unit tests pass", context)
            self.assertIn("-before", diff)
            self.assertIn("+after", diff)
            self.assertIn("new.md", diff)
            self.assertIn("+new file", diff)
            self.assertNotIn("?? review", context)


if __name__ == "__main__":
    unittest.main()
