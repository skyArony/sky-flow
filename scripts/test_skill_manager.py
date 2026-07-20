from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import skill_manager


class RetiredInstallTests(unittest.TestCase):
    @staticmethod
    def skill(
        name: str,
        path: Path,
        relative_dir: Path,
        *,
        is_suite_entry: bool = False,
        install_targets: list[str] | None = None,
    ) -> skill_manager.SkillMeta:
        return skill_manager.SkillMeta(
            name=name,
            path=path,
            skill_doc=path / "SKILL.md",
            relative_dir=relative_dir,
            install_targets=install_targets or ["claude", "codex"],
            commands=[],
            python_packages=[],
            required_skills=[],
            guidance={},
            is_suite_entry=is_suite_entry,
        )

    def test_cleanup_removes_only_owned_legacy_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            root = Path(raw_tmp)
            repo = root / "checkout"
            claude = root / "claude"
            codex = root / "codex"
            claude.mkdir()
            codex.mkdir()

            owned = claude / "to-plan"
            owned.symlink_to(repo / "skills" / "to-plan", target_is_directory=True)

            owned_profile = codex / "review-by-somestay"
            owned_profile.symlink_to(
                repo / "skills" / "to-review" / "reviewers" / "review-by-somestay",
                target_is_directory=True,
            )

            owned_test = claude / "to-test"
            owned_test.symlink_to(repo / "skills" / "to-test", target_is_directory=True)

            owned_bdd = codex / "to-bdd-regression"
            owned_bdd.symlink_to(
                repo / "skills" / "to-debug" / "skills" / "to-bdd-regression",
                target_is_directory=True,
            )

            copied = codex / "to-task"
            copied.mkdir()
            (copied / "SKILL.md").write_text("---\nname: to-task\n---\n", encoding="utf-8")

            foreign = codex / "pick-plan"
            foreign.symlink_to(root / "another-checkout" / "skills" / "pick-plan", target_is_directory=True)

            with (
                mock.patch.object(skill_manager, "REPO_ROOT", repo),
                mock.patch.object(
                    skill_manager,
                    "TARGET_DIRS",
                    {"claude": claude, "codex": codex},
                ),
            ):
                result = skill_manager.inspect_retired_installations(
                    remove_owned_symlinks=True,
                )

            self.assertFalse(owned.is_symlink())
            self.assertFalse(owned_profile.is_symlink())
            self.assertFalse(owned_test.is_symlink())
            self.assertFalse(owned_bdd.is_symlink())
            self.assertTrue((copied / "SKILL.md").is_file())
            self.assertTrue(foreign.is_symlink())
            self.assertEqual(
                {"review-by-somestay", "to-bdd-regression", "to-plan", "to-test"},
                {item["name"] for item in result["cleaned"]},
            )
            self.assertEqual(
                {("pick-plan", "foreign-symlink"), ("to-task", "copied")},
                {(item["name"], item["state"]) for item in result["needs_attention"]},
            )
            self.assertFalse(result["ok"])

    def test_dry_run_reports_owned_symlink_without_removing_it(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            root = Path(raw_tmp)
            repo = root / "checkout"
            claude = root / "claude"
            codex = root / "codex"
            claude.mkdir()
            codex.mkdir()

            owned = claude / "to-archive"
            owned.symlink_to(repo / "skills" / "to-archive", target_is_directory=True)

            with (
                mock.patch.object(skill_manager, "REPO_ROOT", repo),
                mock.patch.object(
                    skill_manager,
                    "TARGET_DIRS",
                    {"claude": claude, "codex": codex},
                ),
            ):
                result = skill_manager.inspect_retired_installations(
                    remove_owned_symlinks=True,
                    dry_run=True,
                )

            self.assertTrue(owned.is_symlink())
            self.assertEqual("would-remove", result["cleaned"][0]["state"])
            self.assertTrue(result["ok"])

    def test_doctor_state_rejects_stale_active_copy(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            root = Path(raw_tmp)
            source = root / "source" / "to-implement"
            source.mkdir(parents=True)
            source_doc = source / "SKILL.md"
            source_doc.write_text("current spec executor\n", encoding="utf-8")

            claude = root / "claude"
            copied = claude / "to-implement"
            copied.mkdir(parents=True)
            (copied / "SKILL.md").write_text("legacy topology executor\n", encoding="utf-8")

            skill = skill_manager.SkillMeta(
                name="to-implement",
                path=source,
                skill_doc=source_doc,
                relative_dir=Path("skills/to-implement"),
                install_targets=["claude"],
                commands=[],
                python_packages=[],
                required_skills=[],
                guidance={},
                is_suite_entry=False,
            )

            with mock.patch.object(
                skill_manager,
                "TARGET_DIRS",
                {"claude": claude, "codex": root / "codex"},
            ):
                state = skill_manager.inspect_install_state(skill)

            self.assertEqual("stale-copy", state["targets"]["claude"])
            self.assertEqual("broken", state["status"])
            with mock.patch.object(
                skill_manager,
                "TARGET_DIRS",
                {"claude": claude, "codex": root / "codex"},
            ):
                rows = skill_manager.summarize_skill_statuses(
                    [skill],
                    {skill.name: skill},
                )
            self.assertIn("--copy --force --no-deps", rows[0]["next_steps"][0])

            (copied / "SKILL.md").write_text("current spec executor\n", encoding="utf-8")
            with mock.patch.object(
                skill_manager,
                "TARGET_DIRS",
                {"claude": claude, "codex": root / "codex"},
            ):
                current_state = skill_manager.inspect_install_state(skill)
            self.assertEqual("copied", current_state["targets"]["claude"])
            self.assertEqual("ready", current_state["status"])

            source_reference = source / "references" / "thin-plan.md"
            source_reference.parent.mkdir()
            source_reference.write_text("current plan contract\n", encoding="utf-8")
            with mock.patch.object(
                skill_manager,
                "TARGET_DIRS",
                {"claude": claude, "codex": root / "codex"},
            ):
                missing_reference_state = skill_manager.inspect_install_state(skill)
            self.assertEqual("stale-copy", missing_reference_state["targets"]["claude"])

            installed_reference = copied / "references" / "thin-plan.md"
            installed_reference.parent.mkdir()
            installed_reference.write_text("current plan contract\n", encoding="utf-8")
            with mock.patch.object(
                skill_manager,
                "TARGET_DIRS",
                {"claude": claude, "codex": root / "codex"},
            ):
                current_reference_state = skill_manager.inspect_install_state(skill)
            self.assertEqual("copied", current_reference_state["targets"]["claude"])

            installed_reference.write_text("stale plan contract\n", encoding="utf-8")
            with mock.patch.object(
                skill_manager,
                "TARGET_DIRS",
                {"claude": claude, "codex": root / "codex"},
            ):
                stale_reference_state = skill_manager.inspect_install_state(skill)
            self.assertEqual("stale-copy", stale_reference_state["targets"]["claude"])

    def test_root_copy_omits_repository_and_archive_history(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            root = Path(raw_tmp)
            repo = root / "checkout"
            repo.mkdir()
            (repo / "SKILL.md").write_text("suite\n", encoding="utf-8")
            (repo / "scripts").mkdir()
            (repo / "scripts" / "validator.ts").write_text("export {};\n", encoding="utf-8")
            explicit_metadata = repo / "skills" / "to-review" / "agents" / "openai.yaml"
            explicit_metadata.parent.mkdir(parents=True)
            explicit_metadata.write_text(
                "policy:\n  allow_implicit_invocation: false\n",
                encoding="utf-8",
            )
            (repo / "archive").mkdir()
            (repo / "archive" / "SKILL.archived.md").write_text("history\n", encoding="utf-8")
            (repo / ".git").mkdir()
            (repo / ".git" / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
            dest = root / "installed" / "sky-flow"
            dest.parent.mkdir()

            with mock.patch.object(skill_manager, "REPO_ROOT", repo):
                result = skill_manager.link_or_copy_skill(
                    repo,
                    dest,
                    copy_mode=True,
                    force=False,
                    dry_run=False,
                )

            self.assertEqual("copied", result)
            self.assertTrue((dest / "SKILL.md").is_file())
            self.assertTrue((dest / "scripts" / "validator.ts").is_file())
            self.assertTrue(
                (dest / "skills" / "to-review" / "agents" / "openai.yaml").is_file()
            )
            self.assertFalse((dest / "archive").exists())
            self.assertFalse((dest / ".git").exists())

    def test_codex_installs_children_through_suite_root(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            root = Path(raw_tmp)
            repo = root / "checkout"
            child_path = repo / "skills" / "to-implement"
            child_path.mkdir(parents=True)
            (repo / "SKILL.md").write_text("suite\n", encoding="utf-8")
            (child_path / "SKILL.md").write_text("executor\n", encoding="utf-8")

            suite = self.skill("sky-flow", repo, Path("."), is_suite_entry=True)
            child = self.skill("to-implement", child_path, Path("skills/to-implement"))
            registry = {suite.name: suite, child.name: child}
            claude = root / "claude"
            codex = root / "codex"
            codex.mkdir()
            redundant_child = codex / "to-implement"
            redundant_child.symlink_to(child_path, target_is_directory=True)

            with (
                mock.patch.object(skill_manager, "REPO_ROOT", repo),
                mock.patch.object(skill_manager, "TARGET_DIRS", {"claude": claude, "codex": codex}),
            ):
                result = skill_manager.install_skills(
                    [suite, child],
                    registry,
                    copy_mode=False,
                    force=False,
                    dry_run=False,
                )

            self.assertTrue((claude / "sky-flow").is_symlink())
            self.assertTrue((claude / "to-implement").is_symlink())
            self.assertTrue((codex / "sky-flow").is_symlink())
            self.assertFalse((codex / "to-implement").exists())
            self.assertEqual("linked-via-suite", result["to-implement"][str(codex)])

    def test_codex_foreign_child_requires_force_before_suite_migration(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            root = Path(raw_tmp)
            repo = root / "checkout"
            child_path = repo / "skills" / "to-implement"
            child_path.mkdir(parents=True)
            (repo / "SKILL.md").write_text("suite\n", encoding="utf-8")
            (child_path / "SKILL.md").write_text("executor\n", encoding="utf-8")

            suite = self.skill("sky-flow", repo, Path("."), is_suite_entry=True)
            child = self.skill("to-implement", child_path, Path("skills/to-implement"))
            registry = {suite.name: suite, child.name: child}
            codex = root / "codex"
            codex.mkdir()
            foreign = codex / "to-implement"
            foreign.symlink_to(root / "foreign" / "to-implement", target_is_directory=True)

            with (
                mock.patch.object(skill_manager, "REPO_ROOT", repo),
                mock.patch.object(skill_manager, "TARGET_DIRS", {"claude": root / "claude", "codex": codex}),
            ):
                blocked = skill_manager.install_skills(
                    [child],
                    registry,
                    copy_mode=False,
                    force=False,
                    dry_run=False,
                )
                forced = skill_manager.install_skills(
                    [child],
                    registry,
                    copy_mode=False,
                    force=True,
                    dry_run=False,
                )

            self.assertEqual("skipped-existing", blocked["to-implement"][str(codex)])
            self.assertEqual("linked-via-suite", forced["to-implement"][str(codex)])
            self.assertFalse(foreign.exists() or foreign.is_symlink())

    def test_codex_doctor_accepts_current_suite_and_rejects_stale_nested_copy(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            root = Path(raw_tmp)
            repo = root / "checkout"
            child_path = repo / "skills" / "to-implement"
            child_path.mkdir(parents=True)
            (repo / "SKILL.md").write_text("suite\n", encoding="utf-8")
            source_doc = child_path / "SKILL.md"
            source_doc.write_text("current executor\n", encoding="utf-8")

            suite = self.skill("sky-flow", repo, Path("."), is_suite_entry=True)
            child = self.skill(
                "to-implement",
                child_path,
                Path("skills/to-implement"),
                install_targets=["codex"],
            )
            registry = {suite.name: suite, child.name: child}
            codex = root / "codex"
            codex.mkdir()

            direct_child = codex / "to-implement"
            direct_child.symlink_to(child_path, target_is_directory=True)
            with (
                mock.patch.object(skill_manager, "REPO_ROOT", repo),
                mock.patch.object(skill_manager, "TARGET_DIRS", {"claude": root / "claude", "codex": codex}),
            ):
                redundant_state = skill_manager.inspect_install_state(child, registry)
            self.assertEqual("redundant-link", redundant_state["targets"]["codex"])
            self.assertEqual("broken", redundant_state["status"])
            direct_child.unlink()

            suite_link = codex / "sky-flow"
            suite_link.symlink_to(repo, target_is_directory=True)
            with (
                mock.patch.object(skill_manager, "REPO_ROOT", repo),
                mock.patch.object(skill_manager, "TARGET_DIRS", {"claude": root / "claude", "codex": codex}),
            ):
                linked_state = skill_manager.inspect_install_state(child, registry)
            self.assertEqual("linked-via-suite", linked_state["targets"]["codex"])
            self.assertEqual("ready", linked_state["status"])

            suite_link.unlink()
            installed_doc = codex / "sky-flow" / "skills" / "to-implement" / "SKILL.md"
            installed_doc.parent.mkdir(parents=True)
            installed_doc.write_text("current executor\n", encoding="utf-8")
            with (
                mock.patch.object(skill_manager, "REPO_ROOT", repo),
                mock.patch.object(skill_manager, "TARGET_DIRS", {"claude": root / "claude", "codex": codex}),
            ):
                copied_state = skill_manager.inspect_install_state(child, registry)
            self.assertEqual("copied-via-suite", copied_state["targets"]["codex"])
            self.assertEqual("ready", copied_state["status"])

            source_reference = child_path / "references" / "thin-plan.md"
            source_reference.parent.mkdir()
            source_reference.write_text("current plan contract\n", encoding="utf-8")
            with (
                mock.patch.object(skill_manager, "REPO_ROOT", repo),
                mock.patch.object(skill_manager, "TARGET_DIRS", {"claude": root / "claude", "codex": codex}),
            ):
                missing_reference_state = skill_manager.inspect_install_state(child, registry)
            self.assertEqual("stale-suite-copy", missing_reference_state["targets"]["codex"])

            installed_reference = installed_doc.parent / "references" / "thin-plan.md"
            installed_reference.parent.mkdir()
            installed_reference.write_text("current plan contract\n", encoding="utf-8")
            with (
                mock.patch.object(skill_manager, "REPO_ROOT", repo),
                mock.patch.object(skill_manager, "TARGET_DIRS", {"claude": root / "claude", "codex": codex}),
            ):
                current_reference_state = skill_manager.inspect_install_state(child, registry)
            self.assertEqual("copied-via-suite", current_reference_state["targets"]["codex"])

            installed_doc.write_text("legacy executor\n", encoding="utf-8")
            with (
                mock.patch.object(skill_manager, "REPO_ROOT", repo),
                mock.patch.object(skill_manager, "TARGET_DIRS", {"claude": root / "claude", "codex": codex}),
            ):
                stale_state = skill_manager.inspect_install_state(child, registry)
            self.assertEqual("stale-suite-copy", stale_state["targets"]["codex"])
            self.assertEqual("broken", stale_state["status"])


class InvocationPolicyTests(unittest.TestCase):
    EXPLICIT_SKILL_DIRS = (
        "skills/pick-goal",
        "skills/to-spec",
        "skills/to-issue",
        "skills/to-knowledge",
        "skills/to-review",
        "skills/to-review-loop",
        "skills/to-agent-review",
        "skills/to-acceptance",
        "skills/to-acceptance/skills/to-next-acceptance",
        "skills/to-backlog",
        "skills/to-handoff",
        "skills/to-consolidation",
        "skills/to-claude-review",
    )

    def test_explicit_skills_disable_implicit_invocation(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        for relative_dir in self.EXPLICIT_SKILL_DIRS:
            with self.subTest(skill=relative_dir):
                metadata = repo / relative_dir / "agents" / "openai.yaml"
                self.assertTrue(metadata.is_file(), f"missing {metadata}")
                self.assertIn(
                    "allow_implicit_invocation: false",
                    metadata.read_text(encoding="utf-8"),
                )


if __name__ == "__main__":
    unittest.main()
