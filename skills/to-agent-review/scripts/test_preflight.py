import json
import tempfile
import unittest
from pathlib import Path

from preflight import (
    analyze_claude_file,
    analyze_codex_file,
    aggregate_sessions,
    compact_aggregate_summary,
    compact_top_session_summaries,
    filter_codex_files_by_cwd,
    parse_line_ranges,
    summarize_transcript_lines,
    wait_category_for_tool,
)


def write_jsonl(path, events):
    path.write_text(
        "\n".join(json.dumps(event, ensure_ascii=False) for event in events) + "\n",
        encoding="utf-8",
    )


def assistant_tool(tool_id, tool_name, timestamp):
    return {
        "type": "assistant",
        "timestamp": timestamp,
        "sessionId": "session-human-wait",
        "message": {
            "role": "assistant",
            "content": [
                {
                    "type": "tool_use",
                    "id": tool_id,
                    "name": tool_name,
                    "input": {"plan": "确认计划"} if tool_name == "ExitPlanMode" else {},
                }
            ],
        },
    }


def user_tool_result(tool_id, timestamp, content="approved"):
    return {
        "type": "user",
        "timestamp": timestamp,
        "sessionId": "session-human-wait",
        "message": {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": tool_id,
                    "content": content,
                }
            ],
        },
    }


def codex_session_meta(session_id, timestamp, cwd, forked_from_id=""):
    return {
        "type": "session_meta",
        "timestamp": timestamp,
        "payload": {
            "id": session_id,
            "forked_from_id": forked_from_id,
            "cwd": cwd,
            "git": {
                "branch": "codex/test",
                "commit_hash": "abc123",
            },
        },
    }


def codex_spawn_attempt(call_id, timestamp, message="review task"):
    return {
        "timestamp": timestamp,
        "type": "response_item",
        "payload": {
            "type": "function_call",
            "name": "spawn_agent",
            "arguments": json.dumps({"message": message}),
            "call_id": call_id,
        },
    }


def codex_tool_output(call_id, timestamp, output):
    return {
        "timestamp": timestamp,
        "type": "response_item",
        "payload": {
            "type": "function_call_output",
            "call_id": call_id,
            "output": output,
        },
    }


class PreflightLatencyTest(unittest.TestCase):
    def test_codex_files_are_filtered_to_project_cwd_by_default(self):
        with tempfile.TemporaryDirectory() as directory:
            tmp_path = Path(directory)
            target_cwd = tmp_path / "FakeGame"
            other_cwd = tmp_path / "CloudBet"
            target_file = tmp_path / "rollout-2026-05-21T00-00-00-11111111-1111-1111-1111-111111111111.jsonl"
            other_file = tmp_path / "rollout-2026-05-21T00-00-00-22222222-2222-2222-2222-222222222222.jsonl"
            write_jsonl(
                target_file,
                [
                    codex_session_meta(
                        "11111111-1111-1111-1111-111111111111",
                        "2026-05-21T00:00:00.000Z",
                        str(target_cwd),
                    )
                ],
            )
            write_jsonl(
                other_file,
                [
                    codex_session_meta(
                        "22222222-2222-2222-2222-222222222222",
                        "2026-05-21T00:00:00.000Z",
                        str(other_cwd),
                    )
                ],
            )

            filtered, stats = filter_codex_files_by_cwd(
                [target_file, other_file],
                cwd=target_cwd,
                explicit_files=[],
                include_all_cwd=False,
                signal_limit=10,
            )
            explicit_filtered, explicit_stats = filter_codex_files_by_cwd(
                [other_file],
                cwd=target_cwd,
                explicit_files=[other_file],
                include_all_cwd=False,
                signal_limit=10,
            )

        self.assertEqual(filtered, [target_file])
        self.assertEqual(stats["candidate_file_count_before_cwd_filter"], 2)
        self.assertEqual(stats["candidate_file_count"], 1)
        self.assertEqual(stats["excluded_by_cwd_count"], 1)
        self.assertIn(str(other_cwd.resolve()), stats["excluded_by_cwd_top"])
        self.assertEqual(explicit_filtered, [other_file])
        self.assertEqual(explicit_stats["excluded_by_cwd_count"], 0)

    def test_codex_fork_duplicate_rollouts_have_deduplicated_aggregate(self):
        with tempfile.TemporaryDirectory() as directory:
            tmp_path = Path(directory)
            cwd = tmp_path / "FakeGame"
            sessions = []
            for suffix in ("33333333-3333-3333-3333-333333333333", "44444444-4444-4444-4444-444444444444"):
                transcript = tmp_path / f"rollout-2026-05-21T00-00-00-{suffix}.jsonl"
                write_jsonl(
                    transcript,
                    [
                        codex_session_meta(
                            suffix,
                            "2026-05-21T00:00:00.000Z",
                            str(cwd),
                            forked_from_id="99999999-9999-9999-9999-999999999999",
                        ),
                        codex_spawn_attempt("call-agent", "2026-05-21T00:00:01.000Z"),
                        codex_tool_output(
                            "call-agent",
                            "2026-05-21T00:00:02.000Z",
                            "collab spawn failed: agent thread limit reached",
                        ),
                        codex_spawn_attempt("call-agent-retry", "2026-05-21T00:00:03.000Z"),
                        codex_tool_output(
                            "call-agent-retry",
                            "2026-05-21T00:00:04.000Z",
                            '{"agent_id":"agent-ok","nickname":"reviewer"}',
                        ),
                    ],
                )
                session = analyze_codex_file(
                    transcript,
                    target_date="2026-05-21",
                    index={},
                    signal_limit=10,
                )
                sessions.append(session)

        self.assertTrue(all(session is not None for session in sessions))
        aggregate = aggregate_sessions(sessions, signal_limit=10)
        deduplicated = aggregate["deduplicated"]
        deduped_aggregate = deduplicated["aggregate"]

        self.assertEqual(aggregate["session_count"], 2)
        self.assertEqual(aggregate["tool_call_count"], 4)
        self.assertEqual(deduplicated["session_count"], 1)
        self.assertEqual(deduplicated["duplicate_group_count"], 1)
        self.assertEqual(deduplicated["duplicate_groups"][0]["dropped_session_count"], 1)
        self.assertEqual(deduped_aggregate["session_count"], 1)
        self.assertEqual(deduped_aggregate["tool_call_count"], 2)
        self.assertEqual(deduped_aggregate["retry_success_path_count"], 1)

    def test_claude_human_decision_waits_are_not_tool_latency(self):
        with tempfile.TemporaryDirectory() as directory:
            tmp_path = Path(directory)
            transcript = tmp_path / "session-human-wait.jsonl"
            write_jsonl(
                transcript,
                [
                    assistant_tool(
                        "plan-1",
                        "ExitPlanMode",
                        "2026-05-12T00:00:00.000Z",
                    ),
                    user_tool_result("plan-1", "2026-05-12T00:10:00.000Z"),
                    assistant_tool(
                        "ask-1",
                        "AskUserQuestion",
                        "2026-05-12T00:10:10.000Z",
                    ),
                    user_tool_result("ask-1", "2026-05-12T00:11:00.000Z"),
                    assistant_tool("bash-1", "Bash", "2026-05-12T00:11:05.000Z"),
                    user_tool_result("bash-1", "2026-05-12T00:11:11.000Z"),
                ],
            )

            session = analyze_claude_file(
                transcript,
                target_date="2026-05-12",
                project_dir=tmp_path,
                signal_limit=10,
            )

        self.assertIsNotNone(session)
        tool_latency = session["decision_signals"]["tool_latency"]
        wait_latency = session["decision_signals"]["wait_latency"]

        self.assertEqual(tool_latency["roundtrip_seconds"]["count"], 1)
        self.assertEqual(tool_latency["top_slow_roundtrip"][0]["tool_name"], "Bash")
        self.assertEqual(wait_latency["human_decision_wait_seconds"]["count"], 2)
        self.assertEqual(
            {record["tool_name"] for record in wait_latency["top_human_decision_wait"]},
            {"AskUserQuestion", "ExitPlanMode"},
        )

    def test_claude_plan_and_question_tools_are_human_decision_waits(self):
        self.assertEqual(
            wait_category_for_tool("AskUserQuestion"),
            "human_decision_wait",
        )
        self.assertEqual(
            wait_category_for_tool("ExitPlanMode"),
            "human_decision_wait",
        )

    def test_codex_exec_fd_failures_are_resource_exhaustion(self):
        with tempfile.TemporaryDirectory() as directory:
            tmp_path = Path(directory)
            transcript = tmp_path / "rollout-2026-05-16T08-21-07-session-resource.jsonl"
            write_jsonl(
                transcript,
                [
                    {
                        "timestamp": "2026-05-16T08:21:07.841Z",
                        "type": "response_item",
                        "payload": {
                            "type": "function_call",
                            "name": "exec_command",
                            "arguments": json.dumps({"cmd": "pwd"}),
                            "call_id": "call-exec",
                        },
                    },
                    {
                        "timestamp": "2026-05-16T08:21:07.847Z",
                        "type": "response_item",
                        "payload": {
                            "type": "function_call_output",
                            "call_id": "call-exec",
                            "output": (
                                "exec_command failed for `/bin/zsh -lc pwd`: "
                                'CreateProcess { message: "Rejected(\\"Failed to create unified exec process: '
                                'dup of fd 248 failed\\")" }'
                            ),
                        },
                    },
                ],
            )

            session = analyze_codex_file(
                transcript,
                target_date="2026-05-16",
                index={},
                signal_limit=10,
            )

        self.assertIsNotNone(session)
        failure = session["decision_signals"]["tool_failure"]

        self.assertEqual(failure["failure_kind_counts"]["resource_exhaustion"], 1)
        self.assertEqual(failure["top_resource_exhaustion_actions"]["exec_command:pwd"], 1)
        self.assertIn(
            "resource_exhaustion",
            {item["type"] for item in session["candidate_bottlenecks"]},
        )

        aggregate = aggregate_sessions([session], signal_limit=10)
        aggregate_failure = aggregate["decision_signals"]["tool_failure"]
        self.assertEqual(aggregate_failure["failure_kind_counts"]["resource_exhaustion"], 1)
        self.assertEqual(aggregate_failure["top_resource_exhaustion_actions"]["exec_command:pwd"], 1)

    def test_codex_high_output_search_is_flagged(self):
        with tempfile.TemporaryDirectory() as directory:
            tmp_path = Path(directory)
            transcript = tmp_path / "rollout-2026-05-16T08-21-07-session-high-output.jsonl"
            write_jsonl(
                transcript,
                [
                    {
                        "timestamp": "2026-05-16T08:21:07.841Z",
                        "type": "response_item",
                        "payload": {
                            "type": "function_call",
                            "name": "exec_command",
                            "arguments": json.dumps(
                                {
                                    "cmd": (
                                        'rg -n "handleOfficial|handleTamper" '
                                        "apps/server/src/modules/game/gg360"
                                    )
                                }
                            ),
                            "call_id": "call-search",
                        },
                    },
                    {
                        "timestamp": "2026-05-16T08:21:07.847Z",
                        "type": "response_item",
                        "payload": {
                            "type": "function_call_output",
                            "call_id": "call-search",
                            "output": (
                                "Chunk ID: search\n"
                                "Wall time: 0.0000 seconds\n"
                                "Process exited with code 0\n"
                                "Original token count: 4732\n"
                                "Output:\n"
                                "apps/server/src/modules/game/gg360/gg360-tamper.service.ts:1:match"
                            ),
                        },
                    },
                ],
            )

            session = analyze_codex_file(
                transcript,
                target_date="2026-05-16",
                index={},
                signal_limit=10,
            )

        self.assertIsNotNone(session)
        tool_output = session["decision_signals"]["tool_output"]

        self.assertEqual(tool_output["high_output_context_read_count"], 1)
        self.assertEqual(tool_output["top_high_output_context_read"][0]["intent"], "search")
        self.assertEqual(tool_output["high_output_search_count"], 1)
        self.assertEqual(tool_output["top_high_output_search"][0]["tool_name"], "exec_command")
        self.assertEqual(tool_output["top_high_output_search"][0]["tokens"], 4732)
        self.assertIn(
            "high_output_context_read",
            {item["type"] for item in session["candidate_bottlenecks"]},
        )

        aggregate = aggregate_sessions([session], signal_limit=10)
        aggregate_output = aggregate["decision_signals"]["tool_output"]
        self.assertEqual(aggregate_output["high_output_context_read_count"], 1)
        self.assertEqual(aggregate_output["high_output_search_count"], 1)
        self.assertEqual(aggregate_output["top_high_output_context_read"][0]["intent"], "search")
        self.assertEqual(aggregate_output["top_high_output_search"][0]["tokens"], 4732)

    def test_codex_non_search_high_output_is_flagged_by_intent(self):
        with tempfile.TemporaryDirectory() as directory:
            tmp_path = Path(directory)
            transcript = tmp_path / "rollout-2026-05-25T13-34-25-session-helm-output.jsonl"
            write_jsonl(
                transcript,
                [
                    {
                        "timestamp": "2026-05-25T13:34:25.646Z",
                        "type": "response_item",
                        "payload": {
                            "type": "function_call",
                            "name": "exec_command",
                            "arguments": json.dumps(
                                {
                                    "cmd": (
                                        "helm template app ./charts/app -n fgproject-gz-test "
                                        "-f envs/gz-test/app.yaml"
                                    )
                                }
                            ),
                            "call_id": "call-helm",
                        },
                    },
                    {
                        "timestamp": "2026-05-25T13:34:26.646Z",
                        "type": "response_item",
                        "payload": {
                            "type": "function_call_output",
                            "call_id": "call-helm",
                            "output": (
                                "Chunk ID: helm\n"
                                "Wall time: 0.1000 seconds\n"
                                "Process exited with code 0\n"
                                "Original token count: 28861\n"
                                "Output:\n"
                                "---\n# Source: fgproject-app/templates/reverse-proxy.yaml"
                            ),
                        },
                    },
                ],
            )

            session = analyze_codex_file(
                transcript,
                target_date="2026-05-25",
                index={},
                signal_limit=10,
            )

        self.assertIsNotNone(session)
        tool_output = session["decision_signals"]["tool_output"]
        self.assertEqual(tool_output["high_output_context_read_count"], 1)
        self.assertEqual(tool_output["top_high_output_context_read"][0]["intent"], "helm")
        self.assertEqual(tool_output["top_high_output_context_read"][0]["tokens"], 28861)
        self.assertEqual(tool_output["high_output_search_count"], 0)

    def test_compact_summary_keeps_daily_signals_without_full_session_payload(self):
        with tempfile.TemporaryDirectory() as directory:
            tmp_path = Path(directory)
            transcript = tmp_path / "rollout-2026-05-25T13-34-25-session-compact.jsonl"
            write_jsonl(
                transcript,
                [
                    {
                        "timestamp": "2026-05-25T13:34:25.646Z",
                        "type": "response_item",
                        "payload": {
                            "type": "function_call",
                            "name": "exec_command",
                            "arguments": json.dumps({"cmd": "rg -n error docs apps"}),
                            "call_id": "call-search",
                        },
                    },
                    {
                        "timestamp": "2026-05-25T13:34:26.646Z",
                        "type": "response_item",
                        "payload": {
                            "type": "function_call_output",
                            "call_id": "call-search",
                            "output": (
                                "Chunk ID: search\n"
                                "Process exited with code 0\n"
                                "Original token count: 9000\n"
                                "Output:\n"
                                "docs/example.md:1:error"
                            ),
                        },
                    },
                ],
            )

            session = analyze_codex_file(
                transcript,
                target_date="2026-05-25",
                index={},
                signal_limit=10,
            )

        self.assertIsNotNone(session)
        aggregate = aggregate_sessions([session], signal_limit=10)
        compact_aggregate = compact_aggregate_summary(aggregate, signal_limit=2)
        compact_sessions = compact_top_session_summaries([session], 1, signal_limit=2)

        self.assertEqual(compact_aggregate["session_count"], 1)
        self.assertEqual(
            compact_aggregate["decision_signals"]["tool_output"]["high_output_context_read_count"],
            1,
        )
        self.assertNotIn("aggregate", compact_aggregate.get("deduplicated", {}))
        self.assertEqual(len(compact_sessions), 1)
        self.assertNotIn("retry_success_paths", compact_sessions[0])
        self.assertIn(
            "tokens[9000]",
            compact_aggregate["decision_signals"]["tool_output"]["top_high_output_context_read"][0],
        )
        self.assertEqual(
            compact_sessions[0]["decision_signals"]["tool_output"]["high_output_context_read_count"],
            1,
        )
        self.assertNotIn(
            "top_high_output_context_read",
            compact_sessions[0]["decision_signals"]["tool_output"],
        )

    def test_codex_validation_exit_zero_with_error_logs_is_success(self):
        with tempfile.TemporaryDirectory() as directory:
            tmp_path = Path(directory)
            transcript = tmp_path / "rollout-2026-05-26T15-00-21-session-validation-log.jsonl"
            write_jsonl(
                transcript,
                [
                    {
                        "timestamp": "2026-05-26T15:03:00.000Z",
                        "type": "response_item",
                        "payload": {
                            "type": "function_call",
                            "name": "exec_command",
                            "arguments": json.dumps(
                                {"cmd": "pnpm --filter @fg/server test -- payout.handler.spec.ts"}
                            ),
                            "call_id": "call-test",
                        },
                    },
                    {
                        "timestamp": "2026-05-26T15:03:01.000Z",
                        "type": "response_item",
                        "payload": {
                            "type": "function_call_output",
                            "call_id": "call-test",
                            "output": "Process running with session ID 12345\nOutput:\njest running",
                        },
                    },
                    {
                        "timestamp": "2026-05-26T15:03:02.000Z",
                        "type": "response_item",
                        "payload": {
                            "type": "function_call",
                            "name": "write_stdin",
                            "arguments": json.dumps({"session_id": 12345, "chars": ""}),
                            "call_id": "call-poll",
                        },
                    },
                    {
                        "timestamp": "2026-05-26T15:03:03.000Z",
                        "type": "response_item",
                        "payload": {
                            "type": "function_call_output",
                            "call_id": "call-poll",
                            "output": (
                                "Process exited with code 0\n"
                                "Output:\n"
                                "ERROR [YXNewPayoutHandler] expected failure branch\n"
                                "Test Suites: 1 passed, 1 total"
                            ),
                        },
                    },
                ],
            )

            session = analyze_codex_file(
                transcript,
                target_date="2026-05-26",
                index={},
                signal_limit=10,
            )

        self.assertIsNotNone(session)
        failure = session["decision_signals"]["tool_failure"]
        validation_poll = session["decision_signals"]["validation_poll_wait"]

        self.assertEqual(failure["failure_count"], 0)
        self.assertEqual(failure["attempt_count"], 1)
        self.assertEqual(failure["top_failed_actions"], {})
        self.assertEqual(validation_poll["roundtrip_seconds"]["count"], 1)

    def test_codex_validation_poll_waits_are_not_tool_latency(self):
        with tempfile.TemporaryDirectory() as directory:
            tmp_path = Path(directory)
            transcript = tmp_path / "rollout-2026-05-16T08-21-07-session-validation-poll.jsonl"
            write_jsonl(
                transcript,
                [
                    {
                        "timestamp": "2026-05-16T08:21:07.000Z",
                        "type": "response_item",
                        "payload": {
                            "type": "function_call",
                            "name": "exec_command",
                            "arguments": json.dumps({"cmd": "pnpm --filter @fg/server build"}),
                            "call_id": "call-build",
                        },
                    },
                    {
                        "timestamp": "2026-05-16T08:21:08.000Z",
                        "type": "response_item",
                        "payload": {
                            "type": "function_call_output",
                            "call_id": "call-build",
                            "output": "Process running with session ID 12345\nOutput:\nTSC Initializing",
                        },
                    },
                    {
                        "timestamp": "2026-05-16T08:21:10.000Z",
                        "type": "response_item",
                        "payload": {
                            "type": "function_call",
                            "name": "write_stdin",
                            "arguments": json.dumps({"session_id": 12345, "chars": ""}),
                            "call_id": "call-poll",
                        },
                    },
                    {
                        "timestamp": "2026-05-16T08:21:20.000Z",
                        "type": "response_item",
                        "payload": {
                            "type": "function_call_output",
                            "call_id": "call-poll",
                            "output": "Process running with session ID 12345\nOutput:\nSWC Running",
                        },
                    },
                ],
            )

            session = analyze_codex_file(
                transcript,
                target_date="2026-05-16",
                index={},
                signal_limit=10,
            )

        self.assertIsNotNone(session)
        tool_latency = session["decision_signals"]["tool_latency"]
        validation_poll = session["decision_signals"]["validation_poll_wait"]

        self.assertEqual(tool_latency["roundtrip_seconds"]["count"], 0)
        self.assertEqual(validation_poll["roundtrip_seconds"]["count"], 1)
        self.assertEqual(validation_poll["top_slow_roundtrip"][0]["tool_name"], "write_stdin")

        aggregate = aggregate_sessions([session], signal_limit=10)
        aggregate_signals = aggregate["decision_signals"]
        self.assertEqual(aggregate_signals["tool_latency"]["top_slow_roundtrip"], [])
        self.assertEqual(aggregate_signals["validation_poll_wait"]["roundtrip_count"], 1)

    def test_codex_browser_sampling_waits_are_validation_poll_waits(self):
        with tempfile.TemporaryDirectory() as directory:
            tmp_path = Path(directory)
            transcript = tmp_path / "rollout-2026-05-20T00-21-25-session-browser-poll.jsonl"
            write_jsonl(
                transcript,
                [
                    {
                        "timestamp": "2026-05-20T00:00:00.000Z",
                        "type": "response_item",
                        "payload": {
                            "type": "function_call",
                            "name": "evaluate_script",
                            "arguments": json.dumps(
                                {
                                    "function": (
                                        "async () => { await new Promise((resolve) => "
                                        "setTimeout(resolve, 60000)); return "
                                        "window.__fgYxParsedOnlyBurstMonitor.summary(); }"
                                    )
                                }
                            ),
                            "call_id": "call-browser-sample",
                        },
                    },
                    {
                        "timestamp": "2026-05-20T00:01:00.000Z",
                        "type": "response_item",
                        "payload": {
                            "type": "function_call_output",
                            "call_id": "call-browser-sample",
                            "output": 'Script ran on page and returned: {"counters":{"parsedS2C":172}}',
                        },
                    },
                ],
            )

            session = analyze_codex_file(
                transcript,
                target_date="2026-05-20",
                index={},
                signal_limit=10,
            )

        self.assertIsNotNone(session)
        tool_latency = session["decision_signals"]["tool_latency"]
        validation_poll = session["decision_signals"]["validation_poll_wait"]

        self.assertEqual(tool_latency["roundtrip_seconds"]["count"], 0)
        self.assertEqual(validation_poll["roundtrip_seconds"]["count"], 1)
        self.assertEqual(validation_poll["top_slow_roundtrip"][0]["tool_name"], "evaluate_script")

    def test_codex_approval_denial_waits_are_human_decision_waits(self):
        with tempfile.TemporaryDirectory() as directory:
            tmp_path = Path(directory)
            transcript = tmp_path / "rollout-2026-05-20T00-21-25-session-approval.jsonl"
            write_jsonl(
                transcript,
                [
                    {
                        "timestamp": "2026-05-20T00:00:00.000Z",
                        "type": "response_item",
                        "payload": {
                            "type": "function_call",
                            "name": "get_app_state",
                            "arguments": json.dumps({"app": "Google Chrome"}),
                            "call_id": "call-approval",
                        },
                    },
                    {
                        "timestamp": "2026-05-20T00:02:20.000Z",
                        "type": "response_item",
                        "payload": {
                            "type": "function_call_output",
                            "call_id": "call-approval",
                            "output": (
                                "Wall time: 140.8050 seconds Output: "
                                "Computer Use approval denied via MCP elicitation"
                            ),
                        },
                    },
                ],
            )

            session = analyze_codex_file(
                transcript,
                target_date="2026-05-20",
                index={},
                signal_limit=10,
            )

        self.assertIsNotNone(session)
        tool_latency = session["decision_signals"]["tool_latency"]
        wait_latency = session["decision_signals"]["wait_latency"]

        self.assertEqual(tool_latency["roundtrip_seconds"]["count"], 0)
        self.assertEqual(wait_latency["human_decision_wait_seconds"]["count"], 1)
        self.assertEqual(wait_latency["top_human_decision_wait"][0]["tool_name"], "get_app_state")

    def test_transcript_line_summary_truncates_large_outputs_and_hides_reasoning(self):
        with tempfile.TemporaryDirectory() as directory:
            tmp_path = Path(directory)
            transcript = tmp_path / "rollout-2026-05-20T09-01-01-session-summary.jsonl"
            large_output = "x" * 5000
            write_jsonl(
                transcript,
                [
                    {
                        "timestamp": "2026-05-20T00:00:00.000Z",
                        "type": "response_item",
                        "payload": {
                            "type": "function_call",
                            "name": "exec_command",
                            "arguments": json.dumps({"cmd": "rg -n error ~/.codex/archived_sessions"}),
                            "call_id": "call-search",
                        },
                    },
                    {
                        "timestamp": "2026-05-20T00:00:01.000Z",
                        "type": "response_item",
                        "payload": {
                            "type": "function_call_output",
                            "call_id": "call-search",
                            "output": (
                                "Chunk ID: search\n"
                                "Process exited with code 0\n"
                                "Original token count: 262144\n"
                                f"Output:\n{large_output}"
                            ),
                        },
                    },
                    {
                        "timestamp": "2026-05-20T00:00:02.000Z",
                        "type": "response_item",
                        "payload": {
                            "type": "agent_reasoning",
                            "encrypted_content": "secret",
                        },
                    },
                    {
                        "timestamp": "2026-05-20T00:00:03.000Z",
                        "type": "response_item",
                        "payload": {
                            "type": "function_call_output",
                            "call_id": "call-raw",
                            "output": (
                                '{"type":"reasoning","encrypted_content":"output-secret"} '
                                '{\\"type\\":\\"reasoning\\",\\"encrypted_content\\":\\"escaped-secret\\"}'
                            ),
                        },
                    },
                    {
                        "timestamp": "2026-05-20T00:00:04.000Z",
                        "type": "response_item",
                        "payload": {
                            "type": "message",
                            "content": [
                                {
                                    "type": "output_text",
                                    "text": "visible message",
                                    "encrypted_content": "message-secret",
                                }
                            ],
                        },
                    },
                ],
            )

            summary = summarize_transcript_lines(transcript, parse_line_ranges(["1-5"]))

        output_event = summary["events"][1]
        hidden_event = summary["events"][2]

        summary_text = json.dumps(summary, ensure_ascii=False)

        self.assertEqual(summary["event_count"], 5)
        self.assertEqual(output_event["original_token_count"], 262144)
        self.assertEqual(output_event["exit_code"], 0)
        self.assertGreater(output_event["output_chars"], 5000)
        self.assertLess(len(output_event["output_excerpt"]), 320)
        self.assertTrue(hidden_event["hidden"])
        self.assertNotIn("secret", summary_text)
        self.assertNotIn("output-secret", summary_text)
        self.assertNotIn("escaped-secret", summary_text)
        self.assertNotIn("message-secret", summary_text)

    def test_codex_subagent_param_conflict_guidance_is_actionable(self):
        with tempfile.TemporaryDirectory() as directory:
            tmp_path = Path(directory)
            transcript = tmp_path / "rollout-2026-05-16T08-21-07-session-subagent.jsonl"
            write_jsonl(
                transcript,
                [
                    {
                        "timestamp": "2026-05-16T08:21:07.000Z",
                        "type": "response_item",
                        "payload": {
                            "type": "function_call",
                            "name": "spawn_agent",
                            "arguments": json.dumps(
                                {
                                    "fork_context": True,
                                    "agent_type": "explorer",
                                    "reasoning_effort": "medium",
                                    "message": "check docs",
                                }
                            ),
                            "call_id": "call-agent",
                        },
                    },
                    {
                        "timestamp": "2026-05-16T08:21:08.000Z",
                        "type": "response_item",
                        "payload": {
                            "type": "function_call_output",
                            "call_id": "call-agent",
                            "output": (
                                "Full-history forked agents inherit the parent agent type, model, "
                                "and reasoning effort; omit agent_type, model, and reasoning_effort."
                            ),
                        },
                    },
                ],
            )

            session = analyze_codex_file(
                transcript,
                target_date="2026-05-16",
                index={},
                signal_limit=10,
            )

        self.assertIsNotNone(session)
        failure = session["decision_signals"]["tool_failure"]
        bottleneck = next(
            item for item in session["candidate_bottlenecks"] if item["type"] == "subagent_param_conflict"
        )

        self.assertEqual(failure["failure_kind_counts"]["subagent_param_conflict"], 1)
        self.assertIn("fork_context=true", bottleneck["evidence"])
        self.assertIn("不要 full-history fork", bottleneck["evidence"])


if __name__ == "__main__":
    unittest.main()
