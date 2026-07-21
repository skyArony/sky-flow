from __future__ import annotations

import json
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().with_name("validate_flow.ts")


class ValidateFlowPlanTests(unittest.TestCase):
    def run_validator(
        self,
        files: dict[str, str],
        *,
        inputs: list[str] | None = None,
    ) -> tuple[subprocess.CompletedProcess[str], dict]:
        with tempfile.TemporaryDirectory() as raw_tmp:
            root = Path(raw_tmp)
            for relative_path, content in files.items():
                target = root / relative_path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(textwrap.dedent(content).lstrip(), encoding="utf-8")

            command = ["node", str(SCRIPT), "--root", str(root)]
            command.extend(inputs or [])
            result = subprocess.run(
                command,
                cwd=root,
                check=False,
                capture_output=True,
                text=True,
            )
            return result, json.loads(result.stdout)

    @staticmethod
    def codes(report: dict, collection: str) -> list[str]:
        return [item["code"] for item in report[collection]]

    @staticmethod
    def spec(spec_id: str = "checkout-flow", status: str = "in_progress") -> str:
        progress = "\n## Progress\n\n- Next: continue implementation.\n" if status != "draft" else ""
        return f"""---
id: {spec_id}
artifact_type: spec
status: {status}
---

# Checkout flow
{progress}
"""

    @staticmethod
    def plan(
        plan_id: str = "checkout-recovery",
        *,
        source_type: str = "spec",
        source_id: str = "checkout-flow",
        status: str = "in_progress",
        extra_frontmatter: str = "",
        body: str = "## Progress\n\n- Done: source inspected.\n- Active: implementation.\n- Next: run focused tests.\n- Blockers: none.\n",
    ) -> str:
        extra = f"{extra_frontmatter}\n" if extra_frontmatter else ""
        return f"""---
id: {plan_id}
artifact_type: plan
status: {status}
source_type: {source_type}
source_id: {source_id}
{extra}---

# Checkout recovery

{body}
"""

    def test_spec_without_plan_is_valid(self) -> None:
        result, report = self.run_validator(
            {"docs/spec/checkout-flow.md": self.spec(status="in_progress")}
        )

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertTrue(report["summary"]["ok"])
        self.assertEqual([], report["errors"])
        self.assertEqual([], report["warnings"])
        self.assertEqual(1, report["summary"]["checked_artifacts"])

    def test_valid_plan_uses_lightweight_report(self) -> None:
        result, report = self.run_validator(
            {
                "docs/spec/checkout-flow.md": self.spec(),
                "docs/plan/checkout-recovery.md": self.plan(),
            }
        )

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual([], report["errors"])
        self.assertEqual([], report["warnings"])
        self.assertEqual("sky-flow-validate-report/v3", report["schema_version"])
        self.assertNotIn("graph", report)
        self.assertNotIn("llm_review_hints", report)

    def test_plan_requires_stable_spec_source(self) -> None:
        cases = {
            "wrong-type": (self.plan(source_type="issue"), "PLAN_SOURCE_MUST_BE_SPEC"),
            "session-id": (
                self.plan(source_id="current-session"),
                "PLAN_SOURCE_ID_INVALID",
            ),
            "empty-list-id": (
                self.plan(source_id="[]"),
                "PLAN_SOURCE_FIELD_TYPE_INVALID",
            ),
            "one-item-list-id": (
                self.plan(source_id="[checkout-flow]"),
                "PLAN_SOURCE_FIELD_TYPE_INVALID",
            ),
            "one-item-list-type": (
                self.plan(source_type="[spec]"),
                "PLAN_SOURCE_FIELD_TYPE_INVALID",
            ),
            "one-item-list-base-id": (
                self.plan(extra_frontmatter="id: [checkout-recovery]"),
                "BASE_FIELD_TYPE_INVALID",
            ),
        }
        for name, (plan, expected_code) in cases.items():
            with self.subTest(name=name):
                result, report = self.run_validator(
                    {"docs/plan/checkout-recovery.md": plan}
                )
                self.assertEqual(1, result.returncode)
                self.assertIn(expected_code, self.codes(report, "errors"))

    def test_missing_plan_source_in_full_scan_is_an_error(self) -> None:
        result, report = self.run_validator(
            {"docs/plan/checkout-recovery.md": self.plan(source_id="external-spec")}
        )

        self.assertEqual(1, result.returncode)
        self.assertIn("PLAN_SOURCE_SPEC_MISSING", self.codes(report, "errors"))

    def test_partial_plan_lint_does_not_resolve_source(self) -> None:
        result, report = self.run_validator(
            {"docs/plan/checkout-recovery.md": self.plan(source_id="external-spec")},
            inputs=["docs/plan/checkout-recovery.md"],
        )

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual([], report["warnings"])

    def test_explicit_sky_flow_root_is_still_a_full_scan(self) -> None:
        result, report = self.run_validator(
            {"docs/plan/checkout-recovery.md": self.plan(source_id="external-spec")},
            inputs=["docs"],
        )

        self.assertEqual(1, result.returncode)
        self.assertIn("PLAN_SOURCE_SPEC_MISSING", self.codes(report, "errors"))

    def test_active_plan_without_progress_warns(self) -> None:
        result, report = self.run_validator(
            {
                "docs/spec/checkout-flow.md": self.spec(),
                "docs/plan/checkout-recovery.md": self.plan(body="## Approach\n\n- Continue.\n"),
            }
        )

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("PLAN_PROGRESS_MISSING", self.codes(report, "warnings"))

    def test_multiple_active_plans_are_resolved_by_runtime(self) -> None:
        files = {
            "docs/spec/checkout-flow.md": self.spec(),
            "docs/plan/checkout-recovery.md": self.plan(),
            "docs/plan/checkout-migration.md": self.plan(plan_id="checkout-migration"),
        }
        result, report = self.run_validator(files)

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertNotIn("MULTIPLE_ACTIVE_PLANS_FOR_SPEC", self.codes(report, "warnings"))

    def test_plan_source_lifecycle_is_checked_at_resume_not_lint(self) -> None:
        for source_status in ("draft", "completed", "abandoned"):
            with self.subTest(source_status=source_status):
                result, report = self.run_validator(
                    {
                        "docs/spec/checkout-flow.md": self.spec(status=source_status),
                        "docs/plan/checkout-recovery.md": self.plan(),
                    }
                )
                self.assertEqual(0, result.returncode, result.stderr)
                self.assertNotIn("PLAN_SOURCE_SPEC_NOT_EXECUTABLE", self.codes(report, "errors"))

    def test_plan_has_no_draft_stage_but_source_status_can_lag(self) -> None:
        result, report = self.run_validator(
            {
                "docs/spec/checkout-flow.md": self.spec(),
                "docs/plan/checkout-recovery.md": self.plan(status="draft"),
            }
        )
        self.assertEqual(1, result.returncode)
        self.assertIn("PLAN_DRAFT_STATUS_NOT_ALLOWED", self.codes(report, "errors"))

        result, report = self.run_validator(
            {
                "docs/spec/checkout-flow.md": self.spec(status="not_started"),
                "docs/plan/checkout-recovery.md": self.plan(status="in_progress"),
            }
        )
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertNotIn("PLAN_SOURCE_SPEC_STATUS_BEHIND", self.codes(report, "errors"))

    def test_legacy_plan_shapes_are_rejected(self) -> None:
        cases = {
            "topology-field": (
                "docs/plan/checkout-recovery.md",
                self.plan(extra_frontmatter="tasks: [one]"),
                "RETIRED_TOPOLOGY_FIELD",
            ),
            "workflow-field": (
                "docs/plan/checkout-recovery.md",
                self.plan(extra_frontmatter="owner: agent-a"),
                "RETIRED_PLAN_FIELD",
            ),
            "legacy-section": (
                "docs/plan/checkout-recovery.md",
                self.plan(body="## Progress Log\n\n- M1\n\n## Progress\n\n- Next: M1.\n"),
                "RETIRED_PLAN_BODY_SECTION",
            ),
            "numeric-id": (
                "docs/plan/001-checkout.md",
                self.plan(plan_id="001-checkout"),
                "PLAN_MUST_NOT_USE_LEGACY_NUMERIC_PREFIX",
            ),
            "done-directory": (
                "docs/plan/done/checkout-recovery.md",
                self.plan(),
                "PLAN_DONE_DIRECTORY_RETIRED",
            ),
        }
        for name, (path, plan, expected_code) in cases.items():
            with self.subTest(name=name):
                result, report = self.run_validator(
                    {"docs/spec/checkout-flow.md": self.spec(), path: plan}
                )
                self.assertEqual(1, result.returncode)
                self.assertIn(expected_code, self.codes(report, "errors"))

    def test_recovery_heading_is_allowed_in_a_thin_plan(self) -> None:
        result, report = self.run_validator(
            {
                "docs/spec/checkout-flow.md": self.spec(),
                "docs/plan/checkout-recovery.md": self.plan(
                    body=(
                        "## Recovery\n\n- Resume at adapter verification.\n\n"
                        "## Progress\n\n- Next: run adapter verification.\n"
                    )
                ),
            }
        )

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertNotIn("RETIRED_PLAN_BODY_SECTION", self.codes(report, "errors"))

    def test_task_and_step_artifacts_remain_retired(self) -> None:
        for artifact_type in ("task", "step"):
            with self.subTest(artifact_type=artifact_type):
                artifact_id = f"legacy-{artifact_type}"
                result, report = self.run_validator(
                    {
                        f"docs/{artifact_type}/{artifact_id}.md": f"""
                        ---
                        id: {artifact_id}
                        artifact_type: {artifact_type}
                        status: in_progress
                        ---
                        """
                    }
                )
                self.assertEqual(1, result.returncode)
                self.assertIn("RETIRED_ARTIFACT_TYPE", self.codes(report, "errors"))

    def test_boundary_artifact_provenance_is_not_a_validated_graph(self) -> None:
        result, report = self.run_validator(
            {
                "docs/spec/checkout-flow.md": self.spec(),
                "docs/plan/checkout-recovery.md": self.plan(),
                "docs/handoff/checkout-handoff.md": """
                ---
                id: checkout-handoff
                artifact_type: handoff
                status: in_progress
                source_type: plan
                source_id: checkout-recovery
                resume_from: continue locally
                ---
                """,
            }
        )

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual([], report["errors"])

    def test_backlog_allows_empty_dependency_list(self) -> None:
        result, report = self.run_validator(
            {
                "docs/backlog/deferred-cleanup.md": """
                ---
                id: deferred-cleanup
                artifact_type: backlog
                status: draft
                depends_on: []
                recommended_resume: after-priority-review
                ---
                """,
            }
        )

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertNotIn("MISSING_REQUIRED_FIELD", self.codes(report, "errors"))

    def test_acceptance_and_handoff_do_not_require_source_fields(self) -> None:
        result, report = self.run_validator(
            {
                "docs/acceptance/manual-check.md": """
                ---
                id: manual-check
                artifact_type: acceptance
                status: draft
                acceptance_type: interactive
                round: 1
                ---
                """,
                "docs/handoff/local-state.md": """
                ---
                id: local-state
                artifact_type: handoff
                status: draft
                resume_from: inspect-current-diff
                ---
                """,
            }
        )

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertNotIn("MISSING_REQUIRED_FIELD", self.codes(report, "errors"))


if __name__ == "__main__":
    unittest.main()
