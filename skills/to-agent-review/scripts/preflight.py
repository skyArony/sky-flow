#!/usr/bin/env python3
"""Build a compact manifest for native Agent transcript review."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import date, datetime
from pathlib import Path
from typing import Any

DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ROLL_OUT_DATE_PATTERN = re.compile(r"rollout-(\d{4}-\d{2}-\d{2})T")
UUID_PATTERN = re.compile(
    r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})",
    re.IGNORECASE,
)

DEFAULT_OUTPUT_ROOT = Path("docs/backlog/agent-reivew")
DEFAULT_EMPTY_TITLE = "原生会话日志缺失复盘"

SEARCH_WORDS = (
    "rg",
    "grep",
    "find",
    "fd",
    "ls",
    "nl",
    "sed",
    "cat",
    "head",
    "tail",
    "git grep",
)
VALIDATION_COMMAND_PATTERNS = (
    r"^\.\/build-ai-check\.sh\b",
    r"^(?:[A-Z0-9_]+=\S+\s+)+go\s+(?:test|build)\b",
    r"^git\s+diff\s+--check\b",
    r"^go\s+(?:test|build)\b",
    r"^gofmt\b",
    r"^npm\s+run\s+(?:test|build|lint|typecheck)\b",
    r"^npx\s+(?:tsc|jest|eslint|prettier)\b",
    r"^pnpm\s+(?:--filter\s+\S+\s+)?(?:test|build|lint|typecheck)\b",
    r"^pnpm\s+(?:--filter\s+\S+\s+)?exec\s+(?:vitest|eslint|tsc|prettier)\b",
    r"^pytest\b",
    r"^python3?\s+-m\s+py_compile\b",
)
EDIT_WORDS = ("apply_patch", "Edit", "Write", "MultiEdit")
SUBAGENT_TOOL_NAMES = {
    "Task",
    "close_agent",
    "resume_agent",
    "send_input",
    "spawn_agent",
    "wait_agent",
}
HIDDEN_CONTENT_TYPES = {"agent_reasoning", "reasoning", "thinking", "encrypted_content"}
HIDDEN_CONTENT_KEYS = {"encrypted_content", "reasoning", "thinking"}
REDACTED_HIDDEN_CONTENT = "[hidden]"
LONG_GAP_SECONDS = 5 * 60
HUMAN_DECISION_WAIT_TOOL_NAMES = {
    "AskUserQuestion",
    "ExitPlanMode",
    "request_user_input",
}
BROWSER_SCRIPT_TOOL_NAMES = {
    "evaluate_script",
}
APPROVAL_WAIT_PATTERNS = (
    r"approval denied via mcp elicitation",
    r"computer use approval denied",
)
BROWSER_SAMPLING_MARKERS = (
    "monitor",
    "capture",
    "summary",
    "__fg",
    "__yaxing",
)
INFRA_WAIT_COMMAND_PATTERNS = (
    r"\bkubectl\b.*\bport-forward\b",
)
RESOURCE_EXHAUSTION_PATTERNS = (
    r"\btoo many open files\b",
    r"\bos error 24\b",
    r"\bemfile\b",
    r"\bdup of fd \d+ failed\b",
)
ORIGINAL_TOKEN_COUNT_PATTERN = re.compile(r"Original token count:\s*(\d+)", re.IGNORECASE)
RUNNING_SESSION_ID_PATTERN = re.compile(r"Process running with session ID\s+(\d+)", re.IGNORECASE)
EXIT_CODE_PATTERN = re.compile(r"(?:Process exited with code|exit code:)\s*(-?\d+)", re.IGNORECASE)
HIGH_OUTPUT_CONTEXT_TOKEN_THRESHOLD = 3000
HIGH_OUTPUT_CONTEXT_CHAR_THRESHOLD = 20_000


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare native Codex / Claude Code transcript review inputs.",
    )
    parser.add_argument(
        "input",
        nargs="?",
        help="Optional native JSONL file or directory. Defaults to runtime homes.",
    )
    parser.add_argument(
        "--runtime",
        choices=("auto", "codex", "claude"),
        default="auto",
        help="Native runtime to inspect.",
    )
    parser.add_argument(
        "--date",
        dest="target_date",
        default=date.today().isoformat(),
        help="Target date in YYYY-MM-DD, or auto-max for the busiest visible day. Defaults to today.",
    )
    parser.add_argument(
        "--cwd",
        default=".",
        help="Project cwd used to filter Codex sessions and derive Claude Code project slug.",
    )
    parser.add_argument(
        "--all-cwd",
        action="store_true",
        help="Include Codex sessions from every cwd instead of filtering to --cwd.",
    )
    parser.add_argument("--codex-home", default="~/.codex")
    parser.add_argument("--claude-home", default="~/.claude")
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    parser.add_argument(
        "--summary-only",
        action="store_true",
        help="Print aggregate plus top sessions instead of the full sessions array.",
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="With --summary-only, print a compact daily digest instead of full nested session signals.",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=None,
        help="Number of top sessions to include in summary output. Defaults to 3 with --compact, otherwise 10.",
    )
    parser.add_argument(
        "--top-days",
        action="store_true",
        help="Print busiest visible dates and exit without writing reports.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Number of dates to include with --top-days. Defaults to 10.",
    )
    parser.add_argument(
        "--signal-limit",
        type=int,
        default=10,
        help="Maximum entries kept in decision-signal top lists. Defaults to 10.",
    )
    parser.add_argument(
        "--summarize-lines",
        action="append",
        default=[],
        help=(
            "Summarize JSONL transcript line ranges such as 58-74 or 58-74,1085-1110. "
            "Requires an input JSONL file and skips normal manifest generation."
        ),
    )
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def expand_path(raw_path: str | Path) -> Path:
    return Path(raw_path).expanduser()


def validate_date(value: str) -> str:
    if not DATE_PATTERN.match(value):
        raise SystemExit(f"--date must use YYYY-MM-DD, got: {value}")
    return value


def project_slug(cwd: Path) -> str:
    return str(cwd.resolve()).replace("/", "-")


def safe_json_loads(line: str) -> dict[str, Any] | None:
    try:
        value = json.loads(line)
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def timestamp_to_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        normalized = value.replace("Z", "+00:00")
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def timestamp_date(value: str | None) -> str | None:
    parsed = timestamp_to_datetime(value)
    if parsed is not None:
        return parsed.date().isoformat()
    if value and DATE_PATTERN.match(value[:10]):
        return value[:10]
    return None


def path_mtime_date(path: Path) -> str | None:
    try:
        return datetime.fromtimestamp(path.stat().st_mtime).date().isoformat()
    except OSError:
        return None


def codex_file_date(path: Path) -> str | None:
    match = ROLL_OUT_DATE_PATTERN.search(path.name)
    if match:
        return match.group(1)
    return path_mtime_date(path)


def normalize_cwd(value: str | Path | None) -> str:
    if value is None:
        return ""
    try:
        return str(Path(value).expanduser().resolve())
    except OSError:
        return str(Path(value).expanduser())


def codex_session_meta(path: Path) -> dict[str, Any]:
    """读取 Codex transcript 开头的当前 session metadata。"""
    path_session_id = uuid_from_text(path.name)
    try:
        handle = path.open(encoding="utf-8")
    except OSError:
        return {}

    with handle:
        for line_no, line in enumerate(handle, start=1):
            if line_no > 20:
                break
            obj = safe_json_loads(line)
            if obj is None:
                continue
            payload = obj.get("payload") if isinstance(obj.get("payload"), dict) else {}
            payload_type = str(payload.get("type") or obj.get("type") or "")
            if payload_type != "session_meta":
                continue
            payload_id = str(payload.get("id") or "")
            if path_session_id and payload_id and payload_id != path_session_id:
                continue
            git = payload.get("git") if isinstance(payload.get("git"), dict) else {}
            return {
                "id": payload_id,
                "cwd": str(payload.get("cwd") or ""),
                "forked_from_id": str(payload.get("forked_from_id") or ""),
                "git_branch": str(git.get("branch") or ""),
                "git_commit": str(git.get("commit_hash") or ""),
                "line": line_no,
            }
    return {}


def uuid_from_text(value: str) -> str | None:
    matches = UUID_PATTERN.findall(value)
    return matches[-1] if matches else None


def redact_hidden_text(value: str) -> str:
    """隐藏 transcript 中可能携带的加密 reasoning 字段值。"""
    return re.sub(
        r'(\\?"encrypted_content\\?"\s*:\s*\\?")[^"\\]*(\\?")',
        rf"\1{REDACTED_HIDDEN_CONTENT}\2",
        value,
    )


def redact_hidden_value(value: Any) -> Any:
    """递归隐藏非可见 reasoning 字段，避免摘要工具误展开。"""
    if isinstance(value, dict):
        return {
            key: REDACTED_HIDDEN_CONTENT
            if key in HIDDEN_CONTENT_KEYS
            else redact_hidden_value(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_hidden_value(item) for item in value]
    if isinstance(value, str):
        return redact_hidden_text(value)
    return value


def compact_text(value: Any, limit: int = 160) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        text = redact_hidden_text(value)
    else:
        text = json.dumps(redact_hidden_value(value), ensure_ascii=False, sort_keys=True)
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    return f"{text[: limit - 1]}..."


def event_text(*values: Any) -> str:
    return " ".join(compact_text(value, 400) for value in values if value is not None)


def compact_visible_text(value: Any, limit: int = 240) -> str:
    """摘要可见内容，避免 transcript 精读时展开大段工具输出。"""
    if value is None:
        return ""
    text = full_output_text(redact_hidden_value(value))
    return compact_text(text, limit)


def full_output_text(value: Any) -> str:
    """保留完整工具输出，用于识别搜索类工具的高输出成本。"""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "\n".join(full_output_text(item) for item in value)
    if isinstance(value, dict):
        if isinstance(value.get("text"), str):
            return value["text"]
        if isinstance(value.get("content"), str):
            return value["content"]
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)


def high_output_intent(tool_call: dict[str, Any]) -> str:
    """按命令意图归类大输出，避免只把搜索类上下文膨胀记入成本。"""
    key = str(tool_call.get("key") or "")
    text = f"{tool_call.get('tool_name') or ''} {key}".lower()
    if tool_call.get("is_search"):
        return "search"
    if re.search(r"(^|[^a-z0-9_-])ps\s", text) or "pgrep" in text:
        return "process"
    if "helm template" in text:
        return "helm"
    if "git diff" in text or re.search(r"(^|[^a-z0-9_-])diff\s", text):
        return "diff"
    if "sqlite3" in text:
        return "sqlite"
    if ".jsonl" in text:
        return "transcript"
    return "other"


def high_output_context_record(
    tool_call: dict[str, Any],
    output: Any,
    result_line: int,
) -> dict[str, Any] | None:
    """将任何上下文读取类大输出记录成可聚合的决策信号。"""
    text = full_output_text(output)
    if not text:
        return None

    token_match = ORIGINAL_TOKEN_COUNT_PATTERN.search(text)
    token_count = int(token_match.group(1)) if token_match else None
    char_count = len(text)
    is_high_output = (
        token_count is not None
        and token_count >= HIGH_OUTPUT_CONTEXT_TOKEN_THRESHOLD
    ) or char_count >= HIGH_OUTPUT_CONTEXT_CHAR_THRESHOLD
    if not is_high_output:
        return None

    return {
        "key": compact_text(tool_call.get("key"), 180),
        "tool_name": str(tool_call.get("tool_name") or "unknown"),
        "intent": high_output_intent(tool_call),
        "tokens": token_count,
        "chars": char_count,
        "score": token_count if token_count is not None else round(char_count / 4),
        "lines": [tool_call.get("line"), result_line],
    }


def extract_command(details: str) -> str:
    try:
        parsed = json.loads(details)
    except json.JSONDecodeError:
        return " ".join(details.split())

    if isinstance(parsed, dict):
        cmd = parsed.get("cmd") or parsed.get("command")
        if isinstance(cmd, str):
            return " ".join(cmd.split())
    return " ".join(details.split())


def extract_interactive_session_id(details: Any) -> str | None:
    parsed = value_from_json_text(details)
    if isinstance(parsed, dict) and parsed.get("session_id") is not None:
        return str(parsed["session_id"])
    return None


def extract_running_session_id(output: Any) -> str | None:
    text = full_output_text(output)
    match = RUNNING_SESSION_ID_PATTERN.search(text)
    return match.group(1) if match else None


def extract_original_token_count(output: Any) -> int | None:
    match = ORIGINAL_TOKEN_COUNT_PATTERN.search(full_output_text(output))
    return int(match.group(1)) if match else None


def extract_exit_code(output: Any) -> int | None:
    match = EXIT_CODE_PATTERN.search(full_output_text(output))
    return int(match.group(1)) if match else None


def is_search_action(tool_name: str, details: str) -> bool:
    name = tool_name.lower()
    text = details.lower()
    if any(word.lower() in name for word in ("grep", "glob", "read", "ls")):
        return True
    return any(re.search(rf"(^|[^a-z0-9_-]){re.escape(word)}([^a-z0-9_-]|$)", text) for word in SEARCH_WORDS)


def is_validation_action(details: str) -> bool:
    command = extract_command(details)
    if not command:
        return False
    return any(re.search(pattern, command) for pattern in VALIDATION_COMMAND_PATTERNS)


def is_browser_sampling_action(tool_name: str, details: str) -> bool:
    """识别浏览器内显式等待采样，避免把观察窗口误判为普通慢工具。"""
    if tool_name not in BROWSER_SCRIPT_TOOL_NAMES:
        return False
    text = details.lower()
    return "settimeout" in text and any(marker in text for marker in BROWSER_SAMPLING_MARKERS)


def is_edit_action(tool_name: str, details: str) -> bool:
    return any(word.lower() in f"{tool_name} {details}".lower() for word in EDIT_WORDS)


def is_subagent_action(tool_name: str) -> bool:
    return tool_name in SUBAGENT_TOOL_NAMES


def wait_category_for_tool(tool_name: str) -> str | None:
    if tool_name in HUMAN_DECISION_WAIT_TOOL_NAMES:
        return "human_decision_wait"
    return None


def wait_category_for_tool_output(output: Any) -> str | None:
    text = compact_visible_text(output, 1200).lower()
    if any(re.search(pattern, text) for pattern in APPROVAL_WAIT_PATTERNS):
        return "human_decision_wait"
    return None


def wait_category_for_exec(command: str) -> str | None:
    if any(re.search(pattern, command) for pattern in INFRA_WAIT_COMMAND_PATTERNS):
        return "infra_wait"
    return None


def retry_action_category(tool_name: str, key: str) -> str:
    if tool_name in SUBAGENT_TOOL_NAMES or tool_name in ("Agent", "Task"):
        return "subagent_dispatch"
    if tool_name == "exec_command":
        command = key.removeprefix("exec_command:").strip()
        if wait_category_for_exec(command) == "infra_wait":
            return "infra"
        if is_validation_action(command):
            return "validation"
        if is_search_action(tool_name, command):
            return "search"
    if is_search_action(tool_name, key):
        return "search"
    return "other"


def failure_kind(tool_name: str, output: Any) -> str | None:
    text = compact_text(output, 800).lower()
    if any(re.search(pattern, text) for pattern in RESOURCE_EXHAUSTION_PATTERNS):
        return "resource_exhaustion"
    if tool_name == "spawn_agent" and "full-history forked agents inherit" in text:
        return "subagent_param_conflict"
    return None


def format_duration(seconds: float) -> str:
    rounded = int(seconds)
    minutes, secs = divmod(rounded, 60)
    if minutes:
        return f"{minutes}m{secs:02d}s"
    return f"{secs}s"


def value_from_json_text(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def command_from_exec_event(payload: dict[str, Any]) -> str:
    parsed_cmd = payload.get("parsed_cmd")
    if isinstance(parsed_cmd, list) and parsed_cmd:
        first = parsed_cmd[0]
        if isinstance(first, dict) and isinstance(first.get("cmd"), str):
            return " ".join(str(first["cmd"]).split())

    command = payload.get("command")
    if isinstance(command, list):
        if len(command) >= 3 and command[0].endswith("zsh") and command[1] == "-lc":
            return " ".join(str(command[2]).split())
        return " ".join(str(part) for part in command)
    if isinstance(command, str):
        return " ".join(command.split())
    return ""


def tool_action_key(tool_name: str, details: Any, *, limit: int = 220) -> str:
    parsed = value_from_json_text(details)
    value: Any = parsed
    if isinstance(parsed, dict):
        if tool_name in ("exec_command", "Bash"):
            value = parsed.get("cmd") or parsed.get("command") or parsed
        elif tool_name == "apply_patch":
            value = parsed
        elif tool_name in ("Read", "Edit", "Write", "MultiEdit"):
            value = parsed.get("file_path") or parsed.get("path") or parsed.get("file") or parsed
        elif tool_name in SUBAGENT_TOOL_NAMES or tool_name in ("Agent", "Task"):
            value = parsed.get("message") or parsed.get("prompt") or parsed.get("description") or parsed
        else:
            value = (
                parsed.get("cmd")
                or parsed.get("command")
                or parsed.get("file_path")
                or parsed.get("path")
                or parsed.get("description")
                or parsed
            )
    elif tool_name == "apply_patch" and isinstance(parsed, str):
        targets = re.findall(r"^\*\*\* (?:Update|Add|Delete) File: (.+)$", parsed, re.MULTILINE)
        value = ", ".join(targets[:6]) if targets else parsed
    text = compact_text(value, limit)
    return f"{tool_name}:{text}" if text else tool_name


def classify_output_attempt(output: Any) -> str | None:
    text = compact_text(output, 600).lower()
    if not text:
        return None
    exit_code = extract_exit_code(output)
    if exit_code is not None:
        return "success" if exit_code == 0 else "failure"
    if any(
        marker in text
        for marker in (
            "full-history forked agents inherit",
            "sandbox denied",
            "permission denied",
            "not_found",
            "not found",
            "rejected",
            "invalid",
            "failed",
            "error:",
        )
    ):
        return "failure"
    if any(marker in text for marker in ("success.", '"agent_id"', '"status": "completed"', '"status":"completed"')):
        return "success"
    return None


def record_tool_latency(
    tool_call: dict[str, Any],
    *,
    result_timestamp: str,
    result_line: int,
    output: Any = None,
    tool_roundtrips: list[float],
    slow_roundtrips: list[dict[str, Any]],
    validation_poll_waits: list[float],
    validation_poll_wait_records: list[dict[str, Any]],
    human_decision_waits: list[float],
    human_decision_wait_records: list[dict[str, Any]],
) -> None:
    """记录工具调用耗时，并把验证轮询 / 人工决策等待从普通工具耗时中拆开。"""
    call_time = timestamp_to_datetime(str(tool_call.get("timestamp") or ""))
    result_time = timestamp_to_datetime(result_timestamp)
    if call_time is None or result_time is None:
        return

    elapsed = (result_time - call_time).total_seconds()
    if elapsed < 0:
        return

    tool_name = str(tool_call.get("tool_name") or "unknown")
    record = {
        "key": compact_text(tool_call.get("key"), 180),
        "tool_name": tool_name,
        "seconds": round(elapsed, 3),
        "lines": [tool_call.get("line"), result_line],
    }
    wait_category = wait_category_for_tool(tool_name) or wait_category_for_tool_output(output)
    if wait_category == "human_decision_wait":
        human_decision_waits.append(elapsed)
        if elapsed >= 5:
            human_decision_wait_records.append(record)
        return

    if tool_call.get("is_validation") or tool_call.get("is_validation_poll"):
        validation_poll_waits.append(elapsed)
        if elapsed >= 5:
            validation_poll_wait_records.append(record)
        return

    tool_roundtrips.append(elapsed)
    if elapsed >= 5:
        slow_roundtrips.append(record)


def record_tool_attempt(
    attempts_by_key: dict[str, list[dict[str, Any]]],
    failed_actions: Counter[str],
    failure_kinds: Counter[str],
    subagent_param_conflict_actions: Counter[str],
    resource_exhaustion_actions: Counter[str],
    *,
    key: str,
    status: str | None,
    line_no: int,
    tool_name: str,
    failure_output: Any = None,
) -> tuple[int, int]:
    """记录一次工具成功 / 失败尝试，返回 attempt 与 failure 增量。"""
    if status not in ("success", "failure") or not key:
        return 0, 0
    attempts_by_key.setdefault(key, []).append(
        {
            "status": status,
            "line": line_no,
            "tool_name": tool_name,
        }
    )
    if status != "failure":
        return 1, 0

    failed_actions[key] += 1
    kind = failure_kind(tool_name, failure_output)
    if kind:
        failure_kinds[kind] += 1
        if kind == "subagent_param_conflict":
            subagent_param_conflict_actions[key] += 1
        if kind == "resource_exhaustion":
            resource_exhaustion_actions[key] += 1
    return 1, 1


def summarize_retry_success_paths(
    attempts_by_key: dict[str, list[dict[str, Any]]],
    *,
    limit: int | None = 10,
) -> list[dict[str, Any]]:
    paths: list[dict[str, Any]] = []
    for key, attempts in attempts_by_key.items():
        if len(attempts) < 2 or attempts[0]["status"] != "failure":
            continue
        success_index = next(
            (index for index, attempt in enumerate(attempts[1:], start=1) if attempt["status"] == "success"),
            None,
        )
        if success_index is None:
            continue
        before_success = attempts[: success_index + 1]
        failure_count = len([attempt for attempt in before_success if attempt["status"] == "failure"])
        paths.append(
            {
                "key": compact_text(key, 180),
                "category": retry_action_category(str(attempts[0].get("tool_name") or "unknown"), key),
                "tool_name": str(attempts[0].get("tool_name") or "unknown"),
                "attempts_until_success": len(before_success),
                "failures_before_success": failure_count,
                "lines": [attempts[0]["line"], before_success[-1]["line"]],
            }
        )

    paths.sort(key=lambda item: (-int(item["failures_before_success"]), -int(item["attempts_until_success"]), item["key"]))
    if limit is None:
        return paths
    return paths[: max(0, limit)]


def render_empty_report(
    *,
    report_date: str,
    runtime: str,
    cwd: Path,
    codex_home: Path,
    claude_project_dir: Path,
    input_path: Path | None,
) -> str:
    input_line = str(input_path) if input_path is not None else "未指定，使用系统原生日志默认位置"
    return "\n".join(
        [
            f"# {DEFAULT_EMPTY_TITLE}",
            "",
            f"日期：{report_date}",
            f"输入来源：{runtime}",
            "",
            "## 总结",
            "",
            "本次 preflight 没有枚举到可分析的 Codex / Claude Code 原生会话。该结果不代表 Review 失败，只说明目标日期暂无可匹配输入。",
            "",
            "## 检查路径",
            "",
            f"- 输入路径：`{input_line}`",
            f"- 项目 cwd：`{cwd}`",
            f"- Codex：`{codex_home}`",
            f"- Claude Code：`{claude_project_dir}`",
            "",
            "## 低效链路",
            "",
            "证据不足：没有输入会话，无法评估低效探索或决策链路。",
            "",
            "## 成本结构",
            "",
            "证据不足：没有工具调用和时间线样本。",
            "",
            "## 高 ROI 优化建议",
            "",
            "证据不足：需要至少一份原生会话后再评估。",
            "",
            "## 可脚本化候选",
            "",
            "- `Low`：保留当前 preflight 空输入报告能力，确保每日自动化有稳定产物。",
            "",
            "## Skill / CLAUDE.md 改进候选",
            "",
            "暂不建议改动。下一轮应先确认 Codex / Claude Code 在目标日期是否确实产生过会话。",
            "",
            "## 不建议优化的点",
            "",
            "- 不建议在无输入样本时扩大自动化范围，避免凭空判断日志链路异常。",
            "",
            "## 建议下一步",
            "",
            f"- 下一次观察 `{report_date}` 的原生会话是否出现在上述路径。",
            "",
        ]
    )


def collect_explicit_files(input_path: Path | None, runtime: str) -> dict[str, list[Path]]:
    result: dict[str, list[Path]] = {"codex": [], "claude": []}
    if input_path is None:
        return result

    candidates: list[Path] = []
    if input_path.is_file() and input_path.suffix == ".jsonl":
        candidates = [input_path]
    elif input_path.is_dir():
        candidates = sorted(path for path in input_path.glob("*.jsonl") if path.is_file())

    for path in candidates:
        text = str(path)
        if runtime in ("auto", "codex") and (".codex" in text or path.name.startswith("rollout-")):
            result["codex"].append(path)
        elif runtime in ("auto", "claude") and ".claude" in text:
            result["claude"].append(path)
        elif runtime == "codex":
            result["codex"].append(path)
        elif runtime == "claude":
            result["claude"].append(path)

    return result


def load_codex_index(codex_home: Path, target_date: str) -> tuple[dict[str, dict[str, str]], set[str]]:
    index_file = codex_home / "session_index.jsonl"
    sessions: dict[str, dict[str, str]] = {}
    ids_for_date: set[str] = set()
    if not index_file.exists():
        return sessions, ids_for_date

    with index_file.open(encoding="utf-8") as handle:
        for line in handle:
            obj = safe_json_loads(line)
            if obj is None:
                continue
            session_id = str(obj.get("id") or "")
            if not session_id:
                continue
            entry = {
                "thread_name": str(obj.get("thread_name") or ""),
                "updated_at": str(obj.get("updated_at") or ""),
            }
            sessions[session_id] = entry
            if timestamp_date(entry["updated_at"]) == target_date:
                ids_for_date.add(session_id)

    return sessions, ids_for_date


def collect_codex_files(
    *,
    codex_home: Path,
    target_date: str,
    index_ids_for_date: set[str],
    explicit_files: list[Path],
) -> list[Path]:
    files: set[Path] = set(explicit_files)
    archive_dir = codex_home / "archived_sessions"
    if archive_dir.exists():
        for path in archive_dir.glob("rollout-*.jsonl"):
            if codex_file_date(path) == target_date:
                files.add(path)
                continue
            session_id = uuid_from_text(path.name)
            if session_id and session_id in index_ids_for_date:
                files.add(path)

    return sorted(files)


def filter_codex_files_by_cwd(
    files: list[Path],
    *,
    cwd: Path,
    explicit_files: list[Path],
    include_all_cwd: bool,
    signal_limit: int,
) -> tuple[list[Path], dict[str, Any]]:
    """默认只保留当前项目 cwd 的 Codex session，显式输入和 --all-cwd 例外。"""
    target_cwd = normalize_cwd(cwd)
    explicit_paths = {path.resolve() for path in explicit_files}
    excluded_cwds: Counter[str] = Counter()
    filtered: list[Path] = []

    for path in files:
        is_explicit = path.resolve() in explicit_paths
        meta = codex_session_meta(path)
        session_cwd = normalize_cwd(meta.get("cwd"))
        if include_all_cwd or is_explicit or not session_cwd or session_cwd == target_cwd:
            filtered.append(path)
            continue
        excluded_cwds[session_cwd] += 1

    stats = {
        "cwd_filter_enabled": not include_all_cwd,
        "target_cwd": target_cwd,
        "candidate_file_count_before_cwd_filter": len(files),
        "candidate_file_count": len(filtered),
        "explicit_file_count": len(explicit_files),
        "excluded_by_cwd_count": sum(excluded_cwds.values()),
        "excluded_by_cwd_top": top_counter(excluded_cwds, signal_limit),
    }
    return sorted(filtered), stats


def add_window(
    windows: list[dict[str, Any]],
    line_no: int,
    total_lines: int,
    reason: str,
    *,
    priority: int = 10,
) -> None:
    start = max(1, line_no - 2)
    end = min(total_lines, line_no + 2)
    for item in windows:
        if start <= item["end"] + 1 and end >= item["start"] - 1:
            item["start"] = min(item["start"], start)
            item["end"] = max(item["end"], end)
            item["priority"] = max(int(item.get("priority") or 0), priority)
            if reason not in item["reason"]:
                item["reason"] = f"{item['reason']}；{reason}"
            return
    windows.append({"start": start, "end": end, "reason": reason, "priority": priority})


def ranked_windows(windows: list[dict[str, Any]], limit: int = 12) -> list[dict[str, Any]]:
    selected = sorted(windows, key=lambda item: (-int(item.get("priority") or 0), item["start"]))[:limit]
    return [
        {
            "start": item["start"],
            "end": item["end"],
            "reason": item["reason"],
        }
        for item in sorted(selected, key=lambda item: item["start"])
    ]


def tool_window_priority(
    *,
    is_subagent: bool,
    is_validation: bool,
    is_edit: bool,
    is_search: bool,
) -> int:
    if is_subagent:
        return 90
    if is_validation:
        return 80
    if is_edit:
        return 60
    if is_search:
        return 30
    return 20


def top_counter(counter: Counter[str], limit: int = 20) -> dict[str, int]:
    return dict(counter.most_common(limit))


def duration_seconds(value: Any) -> float | None:
    if not isinstance(value, dict):
        return None
    secs = value.get("secs")
    nanos = value.get("nanos")
    if not isinstance(secs, (int, float)) and not isinstance(nanos, (int, float)):
        return None
    return float(secs or 0) + float(nanos or 0) / 1_000_000_000


def percent(value: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round(value * 100 / total, 2)


def percentile(values: list[float], ratio: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = int(round((len(ordered) - 1) * ratio))
    return round(ordered[index], 3)


def numeric_summary(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"count": 0}
    return {
        "count": len(values),
        "p50": percentile(values, 0.50),
        "p95": percentile(values, 0.95),
        "max": round(max(values), 3),
    }


def top_records(records: list[dict[str, Any]], score_key: str, limit: int) -> list[dict[str, Any]]:
    return sorted(records, key=lambda item: float(item.get(score_key) or 0), reverse=True)[: max(0, limit)]


def token_usage_snapshot(usage: dict[str, Any] | None) -> dict[str, int]:
    if not isinstance(usage, dict):
        return {}
    result: dict[str, int] = {}
    for key in (
        "input_tokens",
        "cached_input_tokens",
        "cache_read_input_tokens",
        "cache_creation_input_tokens",
        "output_tokens",
        "reasoning_output_tokens",
        "total_tokens",
    ):
        value = usage.get(key)
        if isinstance(value, int):
            result[key] = value
    if "total_tokens" not in result:
        total = (
            result.get("input_tokens", 0)
            + result.get("cached_input_tokens", 0)
            + result.get("cache_read_input_tokens", 0)
            + result.get("cache_creation_input_tokens", 0)
            + result.get("output_tokens", 0)
            + result.get("reasoning_output_tokens", 0)
        )
        if total:
            result["total_tokens"] = total
    return result


def add_token_usage(total: Counter[str], usage: dict[str, Any] | None) -> None:
    for key, value in token_usage_snapshot(usage).items():
        total[key] += value


def rate_limit_percentages(rate_limits: dict[str, Any] | None) -> dict[str, float]:
    if not isinstance(rate_limits, dict):
        return {}
    result: dict[str, float] = {}
    for name in ("primary", "secondary"):
        bucket = rate_limits.get(name)
        if isinstance(bucket, dict) and isinstance(bucket.get("used_percent"), (int, float)):
            result[f"{name}_used_percent"] = round(float(bucket["used_percent"]), 2)
    return result


def merge_counter_from_dict(counter: Counter[str], values: Any) -> None:
    if not isinstance(values, dict):
        return
    counter.update({str(key): int(value) for key, value in values.items() if isinstance(value, int)})


def session_identity(session: dict[str, Any]) -> str:
    return str(session.get("session_id") or session.get("file") or "")


def codex_fork_duplicate_signature(session: dict[str, Any]) -> tuple[Any, ...] | None:
    """为 fork 出来的疑似重复 rollout 构造保守签名。"""
    if session.get("runtime") != "codex":
        return None
    forked_from_id = str(session.get("forked_from_id") or "")
    if not forked_from_id:
        return None

    tool_counts = tuple(
        sorted((str(key), int(value)) for key, value in session.get("tool_call_counts", {}).items())
    )
    retry_paths = session.get("retry_success_paths") if isinstance(session.get("retry_success_paths"), list) else []
    retry_keys = tuple(sorted(str(path.get("key") or "") for path in retry_paths if isinstance(path, dict)))
    if not tool_counts and not retry_keys:
        return None

    git = session.get("git") if isinstance(session.get("git"), dict) else {}
    return (
        normalize_cwd(str(session.get("cwd") or "")),
        forked_from_id,
        str(git.get("commit_hash") or ""),
        int(session.get("tool_call_count") or 0),
        tool_counts,
        retry_keys,
    )


def codex_replayed_parent_call_ids(session: dict[str, Any], parent: dict[str, Any]) -> set[str]:
    """返回 fork session 中已经由 parent session 记录过的工具调用 ID。"""
    child_ids = {str(value) for value in session.get("tool_call_ids") or [] if value}
    parent_ids = {str(value) for value in parent.get("tool_call_ids") or [] if value}
    if not child_ids or not parent_ids:
        return set()
    return child_ids & parent_ids


def representative_session(sessions: list[dict[str, Any]]) -> dict[str, Any]:
    return max(
        sessions,
        key=lambda item: (
            int(item.get("line_count") or 0),
            str(item.get("time_range", {}).get("end") or ""),
            session_identity(item),
        ),
    )


def deduplicate_codex_fork_rollouts(
    sessions: list[dict[str, Any]],
    *,
    signal_limit: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    groups_by_signature: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    for session in sessions:
        signature = codex_fork_duplicate_signature(session)
        if signature is not None:
            groups_by_signature.setdefault(signature, []).append(session)

    duplicate_groups: list[dict[str, Any]] = []
    dropped_ids: set[str] = set()
    for grouped_sessions in groups_by_signature.values():
        if len(grouped_sessions) < 2:
            continue
        representative = representative_session(grouped_sessions)
        representative_id = session_identity(representative)
        member_ids = [session_identity(item) for item in grouped_sessions]
        dropped_ids.update(item for item in member_ids if item != representative_id)
        duplicate_groups.append(
            {
                "reason": "same_fork_parent_tool_counts_retry_paths",
                "forked_from_id": str(representative.get("forked_from_id") or ""),
                "cwd": str(representative.get("cwd") or ""),
                "representative_session_id": representative_id,
                "session_ids": member_ids,
                "raw_session_count": len(grouped_sessions),
                "dropped_session_count": len(grouped_sessions) - 1,
                "raw_tool_call_count": sum(int(item.get("tool_call_count") or 0) for item in grouped_sessions),
                "deduped_tool_call_count": int(representative.get("tool_call_count") or 0),
            }
        )

    sessions_by_id = {session_identity(session): session for session in sessions}
    for session in sessions:
        if session.get("runtime") != "codex":
            continue
        identity = session_identity(session)
        if identity in dropped_ids:
            continue
        forked_from_id = str(session.get("forked_from_id") or "")
        if not forked_from_id:
            continue
        parent = sessions_by_id.get(forked_from_id)
        if not parent:
            continue

        child_ids = {str(value) for value in session.get("tool_call_ids") or [] if value}
        if not child_ids:
            continue
        replayed_ids = codex_replayed_parent_call_ids(session, parent)
        replay_ratio = len(replayed_ids) / len(child_ids)
        if replay_ratio < 0.90:
            continue

        dropped_ids.add(identity)
        duplicate_groups.append(
            {
                "reason": "forked_parent_replayed_tool_call_ids",
                "forked_from_id": forked_from_id,
                "cwd": str(session.get("cwd") or parent.get("cwd") or ""),
                "representative_session_id": session_identity(parent),
                "session_ids": [session_identity(parent), identity],
                "raw_session_count": 2,
                "dropped_session_count": 1,
                "raw_tool_call_count": int(parent.get("tool_call_count") or 0)
                + int(session.get("tool_call_count") or 0),
                "deduped_tool_call_count": int(parent.get("tool_call_count") or 0),
                "duplicate_call_id_count": len(replayed_ids),
                "duplicate_call_id_ratio_percent": percent(len(replayed_ids), len(child_ids)),
            }
        )

    deduped_sessions: list[dict[str, Any]] = []
    for session in sessions:
        identity = session_identity(session)
        if identity in dropped_ids:
            continue
        deduped_sessions.append(session)

    duplicate_groups.sort(
        key=lambda item: (
            -int(item.get("dropped_session_count") or 0),
            str(item.get("representative_session_id") or ""),
        )
    )
    return deduped_sessions, duplicate_groups[: max(0, signal_limit)]


def build_bottlenecks(
    *,
    tool_call_count: int,
    search_count: int,
    high_output_context_read_count: int,
    validation_count: int,
    subagent_count: int,
    retry_success_count: int,
    tool_failure_count: int,
    subagent_param_conflict_count: int,
    resource_exhaustion_count: int,
    slow_tool_count: int,
    human_decision_wait_count: int,
    infra_wait_count: int,
    token_total: int,
    long_gaps: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    bottlenecks: list[dict[str, Any]] = []
    if search_count >= 8:
        bottlenecks.append(
            {
                "type": "context_search",
                "severity": "Medium",
                "evidence": f"搜索 / 读上下文类工具调用 {search_count} 次，建议检查是否能用固定入口或脚本收敛。",
            }
        )
    if high_output_context_read_count:
        bottlenecks.append(
            {
                "type": "high_output_context_read",
                "severity": "Medium",
                "evidence": f"发现 {high_output_context_read_count} 次上下文读取输出过大，建议先摘要、按意图过滤，再精读目标片段。",
            }
        )
    if tool_call_count >= 30:
        bottlenecks.append(
            {
                "type": "tool_density",
                "severity": "Medium",
                "evidence": f"工具调用 {tool_call_count} 次，建议检查是否存在重复探索或批处理机会。",
            }
        )
    if validation_count >= 4:
        bottlenecks.append(
            {
                "type": "validation_wait",
                "severity": "Low",
                "evidence": f"验证类工具调用 {validation_count} 次，建议确认失败重跑是否可脚本化。",
            }
        )
    if subagent_count:
        bottlenecks.append(
            {
                "type": "subagent_wait",
                "severity": "Low",
                "evidence": f"发现子代理相关产物或调用 {subagent_count} 个，复盘时检查派发边界和等待收益。",
            }
        )
    if retry_success_count:
        severity = "Medium" if retry_success_count >= 3 else "Low"
        bottlenecks.append(
            {
                "type": "retry_success_path",
                "severity": severity,
                "evidence": f"发现 {retry_success_count} 条首次失败、后续成功的工具热路径，建议检查是否可前置规则或脚本化。",
            }
        )
    if tool_failure_count >= 3:
        bottlenecks.append(
            {
                "type": "tool_failure",
                "severity": "Medium",
                "evidence": f"工具失败 / 中断 {tool_failure_count} 次，建议检查失败是否集中在同一命令、权限或参数模式。",
            }
        )
    if subagent_param_conflict_count:
        bottlenecks.append(
            {
                "type": "subagent_param_conflict",
                "severity": "Medium",
                "evidence": f"发现 {subagent_param_conflict_count} 次子代理参数冲突；fork_context=true 时只传任务内容，需指定 agent_type/model/reasoning_effort 时不要 full-history fork。",
            }
        )
    if resource_exhaustion_count:
        bottlenecks.append(
            {
                "type": "resource_exhaustion",
                "severity": "Medium",
                "evidence": f"发现 {resource_exhaustion_count} 次本地资源耗尽失败，建议检查并行工具 / 子代理 fanout 是否超过文件句柄或进程资源上限。",
            }
        )
    if slow_tool_count >= 3:
        bottlenecks.append(
            {
                "type": "tool_latency",
                "severity": "Medium",
                "evidence": f"发现 {slow_tool_count} 个耗时超过 5 秒的工具事件，建议优先查看慢工具 Top 列表。",
            }
        )
    if human_decision_wait_count:
        bottlenecks.append(
            {
                "type": "human_decision_wait",
                "severity": "Low",
                "evidence": f"发现 {human_decision_wait_count} 个人工决策等待，复盘时应与慢工具分开评估。",
            }
        )
    if infra_wait_count:
        bottlenecks.append(
            {
                "type": "infra_wait",
                "severity": "Low",
                "evidence": f"发现 {infra_wait_count} 个基础设施等待，复盘时应与 Agent 工具低效分开评估。",
            }
        )
    if token_total >= 1_000_000:
        bottlenecks.append(
            {
                "type": "token_cost",
                "severity": "Low",
                "evidence": f"会话累计 token 指标约 {token_total}，建议检查上下文膨胀、cache 命中和重复读取。",
            }
        )
    for gap in long_gaps[:5]:
        bottlenecks.append(
            {
                "type": "long_gap",
                "severity": "Low",
                "evidence": f"相邻事件间隔约 {gap['duration']}，可能是 LLM 探索、工具等待或人工等待。",
                "lines": gap["lines"],
            }
        )
    return bottlenecks


def analyze_codex_file(
    path: Path,
    *,
    target_date: str,
    index: dict[str, dict[str, str]],
    signal_limit: int,
) -> dict[str, Any] | None:
    tool_names: Counter[str] = Counter()
    payload_types: Counter[str] = Counter()
    hidden_events: Counter[str] = Counter()
    suggested_windows: list[dict[str, Any]] = []
    long_gaps: list[dict[str, Any]] = []
    retry_attempts: dict[str, list[dict[str, Any]]] = {}
    codex_tool_calls: dict[str, dict[str, Any]] = {}
    tool_call_ids: set[str] = set()
    exec_durations: list[float] = []
    tool_roundtrips: list[float] = []
    slow_execs: list[dict[str, Any]] = []
    slow_roundtrips: list[dict[str, Any]] = []
    validation_poll_waits: list[float] = []
    validation_poll_wait_records: list[dict[str, Any]] = []
    validation_interactive_sessions: set[str] = set()
    high_output_search_records: list[dict[str, Any]] = []
    human_decision_waits: list[float] = []
    infra_waits: list[float] = []
    human_decision_wait_records: list[dict[str, Any]] = []
    infra_wait_records: list[dict[str, Any]] = []
    failed_actions: Counter[str] = Counter()
    failure_kinds: Counter[str] = Counter()
    subagent_param_conflict_actions: Counter[str] = Counter()
    resource_exhaustion_actions: Counter[str] = Counter()
    token_total_usage: dict[str, int] = {}
    token_last_usage: dict[str, int] = {}
    token_usage_events = 0
    max_rate_limits: dict[str, float] = {}
    max_context_window = 0
    spawn_statuses: Counter[str] = Counter()
    spawn_models: Counter[str] = Counter()
    interaction_counts: Counter[str] = Counter()
    tool_attempt_count = 0
    tool_failure_count = 0

    session_id = uuid_from_text(path.name)
    path_session_id = session_id
    session_cwd = ""
    session_forked_from_id = ""
    session_git_branch = ""
    session_git_commit = ""
    session_meta_line: int | None = None
    start_time: str | None = None
    end_time: str | None = None
    previous_time: datetime | None = None
    previous_line: int | None = None
    lines_for_date = False
    total_lines = 0
    tool_call_count = 0
    tool_result_count = 0
    search_count = 0
    validation_count = 0
    edit_count = 0
    subagent_count = 0

    with path.open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            total_lines = line_no
            obj = safe_json_loads(line)
            if obj is None:
                continue

            payload = obj.get("payload") if isinstance(obj.get("payload"), dict) else {}
            timestamp = str(obj.get("timestamp") or payload.get("timestamp") or "")
            if timestamp:
                event_date = timestamp_date(timestamp)
                if event_date == target_date:
                    lines_for_date = True
                start_time = timestamp if start_time is None or timestamp < start_time else start_time
                end_time = timestamp if end_time is None or timestamp > end_time else end_time
                parsed_time = timestamp_to_datetime(timestamp)
                if parsed_time is not None and previous_time is not None and previous_line is not None:
                    gap_seconds = (parsed_time - previous_time).total_seconds()
                    if gap_seconds >= LONG_GAP_SECONDS:
                        long_gaps.append(
                            {
                                "duration": format_duration(gap_seconds),
                                "lines": [previous_line, line_no],
                            }
                        )
                        add_window(suggested_windows, line_no, total_lines, "长时间空窗后的事件", priority=75)
                if parsed_time is not None:
                    previous_time = parsed_time
                    previous_line = line_no

            payload_type = str(payload.get("type") or obj.get("type") or "")
            if payload_type:
                payload_types[payload_type] += 1
            if payload_type in HIDDEN_CONTENT_TYPES:
                hidden_events[payload_type] += 1
                continue

            if payload_type == "session_meta":
                payload_id = str(payload.get("id") or "")
                is_current_session = not session_meta_line and (
                    not path_session_id
                    or not payload_id
                    or payload_id == path_session_id
                )
                if is_current_session:
                    session_id = payload_id or session_id or ""
                    session_cwd = str(payload.get("cwd") or "")
                    session_forked_from_id = str(payload.get("forked_from_id") or "")
                    git = payload.get("git") if isinstance(payload.get("git"), dict) else {}
                    session_git_branch = str(git.get("branch") or "")
                    session_git_commit = str(git.get("commit_hash") or "")
                    session_meta_line = line_no

            if payload_type in ("function_call", "custom_tool_call"):
                tool_call_count += 1
                tool_name = str(payload.get("name") or "unknown")
                tool_names[tool_name] += 1
                raw_details = (
                    payload.get("arguments")
                    if payload.get("arguments") is not None
                    else payload.get("input")
                    if payload.get("input") is not None
                    else payload.get("content")
                )
                details = event_text(payload.get("arguments"), payload.get("input"), payload.get("content"))
                search_action = is_search_action(tool_name, details)
                validation_action = is_validation_action(details)
                browser_sampling_action = is_browser_sampling_action(tool_name, details)
                interactive_session_id = extract_interactive_session_id(raw_details)
                validation_poll_action = (
                    browser_sampling_action
                    or (
                        tool_name == "write_stdin"
                        and interactive_session_id is not None
                        and interactive_session_id in validation_interactive_sessions
                    )
                )
                edit_action = is_edit_action(tool_name, details)
                subagent_action = is_subagent_action(tool_name)
                call_id = str(payload.get("call_id") or "")
                if call_id:
                    tool_call_ids.add(call_id)
                    codex_tool_calls[call_id] = {
                        "key": tool_action_key(tool_name, raw_details),
                        "tool_name": tool_name,
                        "line": line_no,
                        "timestamp": timestamp,
                        "is_search": search_action,
                        "is_validation": validation_action,
                        "is_validation_poll": validation_poll_action,
                    }
                add_window(
                    suggested_windows,
                    line_no,
                    total_lines,
                    f"工具调用：{tool_name}",
                    priority=tool_window_priority(
                        is_subagent=subagent_action,
                        is_validation=validation_action,
                        is_edit=edit_action,
                        is_search=search_action,
                    ),
                )
                if search_action:
                    search_count += 1
                if validation_action:
                    validation_count += 1
                if edit_action:
                    edit_count += 1
                if subagent_action:
                    subagent_count += 1

            if payload_type in ("function_call_output", "custom_tool_call_output"):
                tool_result_count += 1
                call_id = str(payload.get("call_id") or "")
                tool_call = codex_tool_calls.get(call_id)
                if tool_call:
                    record = high_output_context_record(tool_call, payload.get("output"), line_no)
                    if record:
                        high_output_search_records.append(record)
                    running_session_id = extract_running_session_id(payload.get("output"))
                    if running_session_id and tool_call.get("is_validation"):
                        validation_interactive_sessions.add(running_session_id)
                if tool_call and tool_call["tool_name"] != "exec_command":
                    record_tool_latency(
                        tool_call,
                        result_timestamp=timestamp,
                        result_line=line_no,
                        output=payload.get("output"),
                        tool_roundtrips=tool_roundtrips,
                        slow_roundtrips=slow_roundtrips,
                        validation_poll_waits=validation_poll_waits,
                        validation_poll_wait_records=validation_poll_wait_records,
                        human_decision_waits=human_decision_waits,
                        human_decision_wait_records=human_decision_wait_records,
                    )
                    attempt_delta, failure_delta = record_tool_attempt(
                        retry_attempts,
                        failed_actions,
                        failure_kinds,
                        subagent_param_conflict_actions,
                        resource_exhaustion_actions,
                        key=str(tool_call["key"]),
                        status=classify_output_attempt(payload.get("output")),
                        line_no=line_no,
                        tool_name=str(tool_call["tool_name"]),
                        failure_output=payload.get("output"),
                    )
                    tool_attempt_count += attempt_delta
                    tool_failure_count += failure_delta
                elif tool_call and tool_call["tool_name"] == "exec_command":
                    output = payload.get("output")
                    status = classify_output_attempt(output)
                    if status == "failure" and failure_kind("exec_command", output) == "resource_exhaustion":
                        attempt_delta, failure_delta = record_tool_attempt(
                            retry_attempts,
                            failed_actions,
                            failure_kinds,
                            subagent_param_conflict_actions,
                            resource_exhaustion_actions,
                            key=str(tool_call["key"]),
                            status=status,
                            line_no=line_no,
                            tool_name="exec_command",
                            failure_output=output,
                        )
                        tool_attempt_count += attempt_delta
                        tool_failure_count += failure_delta

            if payload_type == "exec_command_end":
                command = command_from_exec_event(payload)
                if command:
                    elapsed = duration_seconds(payload.get("duration"))
                    if elapsed is not None:
                        wait_category = wait_category_for_exec(command)
                        if wait_category == "infra_wait":
                            infra_waits.append(elapsed)
                            if elapsed >= 5:
                                infra_wait_records.append(
                                    {
                                        "key": compact_text(f"exec_command:{command}", 180),
                                        "seconds": round(elapsed, 3),
                                        "line": line_no,
                                        "exit_code": payload.get("exit_code"),
                                    }
                                )
                        elif is_validation_action(command):
                            validation_poll_waits.append(elapsed)
                            if elapsed >= 5:
                                validation_poll_wait_records.append(
                                    {
                                        "key": compact_text(f"exec_command:{command}", 180),
                                        "seconds": round(elapsed, 3),
                                        "line": line_no,
                                        "exit_code": payload.get("exit_code"),
                                    }
                                )
                        else:
                            exec_durations.append(elapsed)
                            if elapsed >= 5:
                                slow_execs.append(
                                    {
                                        "key": compact_text(f"exec_command:{command}", 180),
                                        "seconds": round(elapsed, 3),
                                        "line": line_no,
                                        "exit_code": payload.get("exit_code"),
                                    }
                                )
                    exit_code = payload.get("exit_code")
                    status = "success" if payload.get("status") == "completed" and exit_code == 0 else "failure"
                    attempt_delta, failure_delta = record_tool_attempt(
                        retry_attempts,
                        failed_actions,
                        failure_kinds,
                        subagent_param_conflict_actions,
                        resource_exhaustion_actions,
                        key=f"exec_command:{command}",
                        status=status,
                        line_no=line_no,
                        tool_name="exec_command",
                        failure_output=payload,
                    )
                    tool_attempt_count += attempt_delta
                    tool_failure_count += failure_delta

            if payload_type == "patch_apply_end":
                changes = payload.get("changes")
                if isinstance(changes, dict) and changes:
                    key = f"apply_patch:{', '.join(sorted(changes)[:6])}"
                    status = "success" if payload.get("success") is True else "failure"
                    attempt_delta, failure_delta = record_tool_attempt(
                        retry_attempts,
                        failed_actions,
                        failure_kinds,
                        subagent_param_conflict_actions,
                        resource_exhaustion_actions,
                        key=key,
                        status=status,
                        line_no=line_no,
                        tool_name="apply_patch",
                    )
                    tool_attempt_count += attempt_delta
                    tool_failure_count += failure_delta

            if payload_type == "collab_agent_spawn_end":
                status_value = str(payload.get("status") or "")
                if status_value:
                    spawn_statuses[status_value] += 1
                    model_key = f"{payload.get('model') or 'unknown'} / {payload.get('reasoning_effort') or 'unknown'}"
                    spawn_models[model_key] += 1
                    status = "success" if status_value in ("pending_init", "running", "completed") else "failure"
                    key = tool_action_key("spawn_agent", {"message": payload.get("prompt"), "model": payload.get("model")})
                    attempt_delta, failure_delta = record_tool_attempt(
                        retry_attempts,
                        failed_actions,
                        failure_kinds,
                        subagent_param_conflict_actions,
                        resource_exhaustion_actions,
                        key=key,
                        status=status,
                        line_no=line_no,
                        tool_name="spawn_agent",
                    )
                    tool_attempt_count += attempt_delta
                    tool_failure_count += failure_delta

            if payload_type == "token_count":
                token_usage_events += 1
                info = payload.get("info") if isinstance(payload.get("info"), dict) else {}
                token_total_usage = token_usage_snapshot(info.get("total_token_usage"))
                token_last_usage = token_usage_snapshot(info.get("last_token_usage"))
                if isinstance(info.get("model_context_window"), int):
                    max_context_window = max(max_context_window, int(info["model_context_window"]))
                for key, value in rate_limit_percentages(payload.get("rate_limits")).items():
                    max_rate_limits[key] = max(max_rate_limits.get(key, 0.0), value)

            if payload_type in ("context_compacted", "user_message", "task_started", "task_complete", "collab_waiting_end"):
                interaction_counts[payload_type] += 1

    file_date = codex_file_date(path)
    index_entry = index.get(session_id or "", {})
    if not lines_for_date and file_date != target_date and timestamp_date(index_entry.get("updated_at")) != target_date:
        return None

    title = index_entry.get("thread_name") or path.stem
    all_retry_success_paths = summarize_retry_success_paths(retry_attempts, limit=None)
    retry_success_paths = all_retry_success_paths[: max(0, signal_limit)]
    tool_latency = {
        "exec_seconds": numeric_summary(exec_durations),
        "roundtrip_seconds": numeric_summary(tool_roundtrips),
        "top_slow_exec": top_records(slow_execs, "seconds", signal_limit),
        "top_slow_roundtrip": top_records(slow_roundtrips, "seconds", signal_limit),
    }
    validation_poll_wait = {
        "roundtrip_seconds": numeric_summary(validation_poll_waits),
        "top_slow_roundtrip": top_records(validation_poll_wait_records, "seconds", signal_limit),
    }
    wait_latency = {
        "human_decision_wait_seconds": numeric_summary(human_decision_waits),
        "infra_wait_seconds": numeric_summary(infra_waits),
        "top_human_decision_wait": top_records(human_decision_wait_records, "seconds", signal_limit),
        "top_infra_wait": top_records(infra_wait_records, "seconds", signal_limit),
    }
    tool_failure = {
        "failure_count": tool_failure_count,
        "attempt_count": tool_attempt_count,
        "failure_rate_percent": percent(tool_failure_count, tool_attempt_count),
        "top_failed_actions": top_counter(failed_actions, signal_limit),
        "failure_kind_counts": top_counter(failure_kinds, signal_limit),
        "top_subagent_param_conflict_actions": top_counter(subagent_param_conflict_actions, signal_limit),
        "top_resource_exhaustion_actions": top_counter(resource_exhaustion_actions, signal_limit),
    }
    token_cost = {
        "usage_event_count": token_usage_events,
        "total_usage": token_total_usage,
        "last_usage": token_last_usage,
        "max_rate_limits": max_rate_limits,
        "max_context_window": max_context_window,
    }
    subagent_runtime = {
        "spawn_status_counts": top_counter(spawn_statuses, signal_limit),
        "spawn_model_effort_counts": top_counter(spawn_models, signal_limit),
    }
    tool_output = {
        "high_output_context_read_count": len(high_output_search_records),
        "top_high_output_context_read": top_records(high_output_search_records, "score", signal_limit),
        "high_output_search_count": sum(1 for record in high_output_search_records if record.get("intent") == "search"),
        "top_high_output_search": top_records(
            [record for record in high_output_search_records if record.get("intent") == "search"],
            "score",
            signal_limit,
        ),
    }
    interaction_interrupts = top_counter(interaction_counts, signal_limit)
    decision_signals = {
        "tool_latency": tool_latency,
        "tool_output": tool_output,
        "validation_poll_wait": validation_poll_wait,
        "wait_latency": wait_latency,
        "tool_failure": tool_failure,
        "token_cost": token_cost,
        "subagent_runtime": subagent_runtime,
        "interaction_interrupts": interaction_interrupts,
    }
    bottlenecks = build_bottlenecks(
        tool_call_count=tool_call_count,
        search_count=search_count,
        high_output_context_read_count=len(high_output_search_records),
        validation_count=validation_count,
        subagent_count=subagent_count,
        retry_success_count=len(all_retry_success_paths),
        tool_failure_count=tool_failure_count,
        subagent_param_conflict_count=int(failure_kinds.get("subagent_param_conflict", 0)),
        resource_exhaustion_count=int(failure_kinds.get("resource_exhaustion", 0)),
        slow_tool_count=len(slow_execs) + len(slow_roundtrips),
        human_decision_wait_count=len(human_decision_wait_records),
        infra_wait_count=len(infra_wait_records),
        token_total=token_total_usage.get("total_tokens", 0),
        long_gaps=long_gaps,
    )

    return {
        "runtime": "codex",
        "session_id": session_id or "",
        "title": title,
        "file": str(path),
        "cwd": session_cwd,
        "forked_from_id": session_forked_from_id,
        "git": {
            "branch": session_git_branch,
            "commit_hash": session_git_commit,
        },
        "session_meta_line": session_meta_line,
        "line_count": total_lines,
        "time_range": {"start": start_time, "end": end_time},
        "tool_call_count": tool_call_count,
        "tool_result_count": tool_result_count,
        "tool_call_counts": top_counter(tool_names),
        "tool_call_ids": sorted(tool_call_ids),
        "event_counts": top_counter(payload_types),
        "hidden_event_counts": top_counter(hidden_events),
        "search_like_tool_calls": search_count,
        "validation_like_tool_calls": validation_count,
        "edit_like_tool_calls": edit_count,
        "subagent_count": subagent_count,
        "retry_success_path_count": len(all_retry_success_paths),
        "retry_success_paths": retry_success_paths,
        "decision_signals": decision_signals,
        "candidate_bottlenecks": bottlenecks,
        "suggested_read_lines": ranked_windows(suggested_windows),
    }


def collect_claude_files(
    *,
    claude_project_dir: Path,
    explicit_files: list[Path],
) -> list[Path]:
    files: set[Path] = set(explicit_files)
    if claude_project_dir.exists():
        files.update(path for path in claude_project_dir.glob("*.jsonl") if path.is_file())
    return sorted(files)


def claude_content_items(message: Any) -> list[dict[str, Any]]:
    if not isinstance(message, dict):
        return []
    content = message.get("content")
    if not isinstance(content, list):
        return []
    return [item for item in content if isinstance(item, dict)]


def claude_visible_title(obj: dict[str, Any], current_title: str | None) -> str | None:
    slug = obj.get("slug")
    if isinstance(slug, str) and slug.strip():
        return slug.strip()
    if current_title:
        return current_title
    if obj.get("type") != "user":
        return None
    for item in claude_content_items(obj.get("message")):
        if item.get("type") == "text":
            return compact_text(item.get("text"), 80)
    return None


def count_child_files(parent: Path, session_id: str, dirname: str, suffix: str) -> int:
    candidates = [parent / session_id / dirname]
    total = 0
    for directory in candidates:
        if directory.exists():
            total += len([path for path in directory.glob(f"*{suffix}") if path.is_file()])
    return total


def collect_child_json_field_counts(parent: Path, session_id: str, dirname: str, suffix: str, field: str) -> Counter[str]:
    result: Counter[str] = Counter()
    directory = parent / session_id / dirname
    if not directory.exists():
        return result
    for path in directory.glob(f"*{suffix}"):
        if not path.is_file():
            continue
        try:
            obj = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(obj, dict):
            result[str(obj.get(field) or "unknown")] += 1
    return result


def analyze_claude_file(
    path: Path,
    *,
    target_date: str,
    project_dir: Path,
    signal_limit: int,
) -> dict[str, Any] | None:
    tool_names: Counter[str] = Counter()
    top_types: Counter[str] = Counter()
    content_types: Counter[str] = Counter()
    hidden_events: Counter[str] = Counter()
    suggested_windows: list[dict[str, Any]] = []
    long_gaps: list[dict[str, Any]] = []
    retry_attempts: dict[str, list[dict[str, Any]]] = {}
    claude_tool_calls: dict[str, dict[str, Any]] = {}
    tool_roundtrips: list[float] = []
    slow_roundtrips: list[dict[str, Any]] = []
    validation_poll_waits: list[float] = []
    validation_poll_wait_records: list[dict[str, Any]] = []
    high_output_search_records: list[dict[str, Any]] = []
    human_decision_waits: list[float] = []
    human_decision_wait_records: list[dict[str, Any]] = []
    failed_actions: Counter[str] = Counter()
    failure_kinds: Counter[str] = Counter()
    subagent_param_conflict_actions: Counter[str] = Counter()
    resource_exhaustion_actions: Counter[str] = Counter()
    token_usage_totals: Counter[str] = Counter()
    token_usage_events = 0
    token_models: Counter[str] = Counter()
    token_speeds: Counter[str] = Counter()
    seen_usage_requests: set[str] = set()
    queue_ops: Counter[str] = Counter()
    permission_modes: Counter[str] = Counter()
    interaction_counts: Counter[str] = Counter()
    tool_attempt_count = 0
    tool_failure_count = 0

    session_id = path.stem
    title: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    previous_time: datetime | None = None
    previous_line: int | None = None
    lines_for_date = False
    total_lines = 0
    tool_call_count = 0
    tool_result_count = 0
    search_count = 0
    validation_count = 0
    edit_count = 0
    subagent_tool_count = 0

    with path.open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            total_lines = line_no
            obj = safe_json_loads(line)
            if obj is None:
                continue

            session_id = str(obj.get("sessionId") or session_id)
            title = claude_visible_title(obj, title)
            event_type = str(obj.get("type") or "")
            if event_type:
                top_types[event_type] += 1
            if event_type == "queue-operation":
                queue_ops[str(obj.get("operation") or "unknown")] += 1
            if event_type == "permission-mode":
                permission_modes[str(obj.get("permissionMode") or "unknown")] += 1
            if event_type in ("file-history-snapshot", "progress", "last-prompt"):
                interaction_counts[event_type] += 1
            if event_type == "user" and "[Request interrupted by user]" in event_text(obj.get("message")):
                interaction_counts["request_interrupted_by_user"] += 1
            attachment = obj.get("attachment") if isinstance(obj.get("attachment"), dict) else {}
            if attachment.get("type") in ("deferred_tools_delta", "opened_file_in_ide"):
                interaction_counts[str(attachment.get("type"))] += 1

            message = obj.get("message") if isinstance(obj.get("message"), dict) else {}
            usage = message.get("usage") if isinstance(message.get("usage"), dict) else None
            usage_key = str(obj.get("requestId") or message.get("id") or "")
            if usage is not None and usage_key and usage_key not in seen_usage_requests:
                seen_usage_requests.add(usage_key)
                add_token_usage(token_usage_totals, usage)
                token_usage_events += 1
                if isinstance(message.get("model"), str):
                    token_models[str(message["model"])] += 1
                if isinstance(usage.get("speed"), str):
                    token_speeds[str(usage["speed"])] += 1

            timestamp = str(obj.get("timestamp") or "")
            if timestamp:
                event_date = timestamp_date(timestamp)
                if event_date == target_date:
                    lines_for_date = True
                start_time = timestamp if start_time is None or timestamp < start_time else start_time
                end_time = timestamp if end_time is None or timestamp > end_time else end_time
                parsed_time = timestamp_to_datetime(timestamp)
                if parsed_time is not None and previous_time is not None and previous_line is not None:
                    gap_seconds = (parsed_time - previous_time).total_seconds()
                    if gap_seconds >= LONG_GAP_SECONDS:
                        long_gaps.append(
                            {
                                "duration": format_duration(gap_seconds),
                                "lines": [previous_line, line_no],
                            }
                        )
                        add_window(suggested_windows, line_no, total_lines, "长时间空窗后的事件", priority=75)
                if parsed_time is not None:
                    previous_time = parsed_time
                    previous_line = line_no

            for item in claude_content_items(message):
                item_type = str(item.get("type") or "")
                if item_type:
                    content_types[item_type] += 1
                if item_type in HIDDEN_CONTENT_TYPES:
                    hidden_events[item_type] += 1
                    continue
                if item_type == "tool_use":
                    tool_call_count += 1
                    tool_name = str(item.get("name") or "unknown")
                    tool_names[tool_name] += 1
                    raw_details = item.get("input")
                    details = event_text(raw_details)
                    search_action = is_search_action(tool_name, details)
                    validation_action = is_validation_action(details)
                    browser_sampling_action = is_browser_sampling_action(tool_name, details)
                    edit_action = is_edit_action(tool_name, details)
                    subagent_action = is_subagent_action(tool_name)
                    tool_use_id = str(item.get("id") or "")
                    if tool_use_id:
                        claude_tool_calls[tool_use_id] = {
                            "key": tool_action_key(tool_name, raw_details),
                            "tool_name": tool_name,
                            "line": line_no,
                            "timestamp": timestamp,
                            "is_search": search_action,
                            "is_validation": validation_action,
                            "is_validation_poll": browser_sampling_action,
                        }
                    add_window(
                        suggested_windows,
                        line_no,
                        total_lines,
                        f"工具调用：{tool_name}",
                        priority=tool_window_priority(
                            is_subagent=subagent_action,
                            is_validation=validation_action,
                            is_edit=edit_action,
                            is_search=search_action,
                        ),
                    )
                    if search_action:
                        search_count += 1
                    if validation_action:
                        validation_count += 1
                    if edit_action:
                        edit_count += 1
                    if subagent_action:
                        subagent_tool_count += 1
                elif item_type == "tool_result":
                    tool_result_count += 1
                    tool_use_id = str(item.get("tool_use_id") or "")
                    tool_call = claude_tool_calls.get(tool_use_id)
                    if tool_call:
                        record = high_output_context_record(tool_call, item.get("content"), line_no)
                        if record:
                            high_output_search_records.append(record)
                        record_tool_latency(
                            tool_call,
                            result_timestamp=timestamp,
                            result_line=line_no,
                            output=item.get("content"),
                            tool_roundtrips=tool_roundtrips,
                            slow_roundtrips=slow_roundtrips,
                            validation_poll_waits=validation_poll_waits,
                            validation_poll_wait_records=validation_poll_wait_records,
                            human_decision_waits=human_decision_waits,
                            human_decision_wait_records=human_decision_wait_records,
                        )
                        attempt_delta, failure_delta = record_tool_attempt(
                            retry_attempts,
                            failed_actions,
                            failure_kinds,
                            subagent_param_conflict_actions,
                            resource_exhaustion_actions,
                            key=str(tool_call["key"]),
                            status="failure" if item.get("is_error") else "success",
                            line_no=line_no,
                            tool_name=str(tool_call["tool_name"]),
                            failure_output=item.get("content"),
                        )
                        tool_attempt_count += attempt_delta
                        tool_failure_count += failure_delta

            if "toolUseResult" in obj:
                tool_result_count += 1
                result = obj.get("toolUseResult")
                if isinstance(result, dict) and (result.get("interrupted") or result.get("stderr")):
                    key = f"toolUseResult:{compact_text(result.get('stderr') or result.get('stdout'), 120)}"
                    attempt_delta, failure_delta = record_tool_attempt(
                        retry_attempts,
                        failed_actions,
                        failure_kinds,
                        subagent_param_conflict_actions,
                        resource_exhaustion_actions,
                        key=key,
                        status="failure",
                        line_no=line_no,
                        tool_name="toolUseResult",
                        failure_output=result.get("stderr") or result.get("stdout"),
                    )
                    tool_attempt_count += attempt_delta
                    tool_failure_count += failure_delta

    if not lines_for_date and path_mtime_date(path) != target_date:
        return None

    subagent_file_count = count_child_files(project_dir, session_id, "subagents", ".jsonl")
    tool_result_file_count = count_child_files(project_dir, session_id, "tool-results", ".txt")
    subagent_meta_counts = collect_child_json_field_counts(project_dir, session_id, "subagents", ".meta.json", "agentType")
    subagent_count = subagent_tool_count + subagent_file_count
    all_retry_success_paths = summarize_retry_success_paths(retry_attempts, limit=None)
    retry_success_paths = all_retry_success_paths[: max(0, signal_limit)]
    tool_latency = {
        "roundtrip_seconds": numeric_summary(tool_roundtrips),
        "top_slow_roundtrip": top_records(slow_roundtrips, "seconds", signal_limit),
    }
    validation_poll_wait = {
        "roundtrip_seconds": numeric_summary(validation_poll_waits),
        "top_slow_roundtrip": top_records(validation_poll_wait_records, "seconds", signal_limit),
    }
    wait_latency = {
        "human_decision_wait_seconds": numeric_summary(human_decision_waits),
        "infra_wait_seconds": numeric_summary([]),
        "top_human_decision_wait": top_records(human_decision_wait_records, "seconds", signal_limit),
        "top_infra_wait": [],
    }
    tool_failure = {
        "failure_count": tool_failure_count,
        "attempt_count": tool_attempt_count,
        "failure_rate_percent": percent(tool_failure_count, tool_attempt_count),
        "top_failed_actions": top_counter(failed_actions, signal_limit),
        "failure_kind_counts": top_counter(failure_kinds, signal_limit),
        "top_subagent_param_conflict_actions": top_counter(subagent_param_conflict_actions, signal_limit),
        "top_resource_exhaustion_actions": top_counter(resource_exhaustion_actions, signal_limit),
    }
    token_cost = {
        "usage_event_count": token_usage_events,
        "total_usage": dict(token_usage_totals),
        "model_counts": top_counter(token_models, signal_limit),
        "speed_counts": top_counter(token_speeds, signal_limit),
    }
    subagent_runtime = {
        "agent_tool_calls": subagent_tool_count,
        "subagent_file_count": subagent_file_count,
        "subagent_meta_counts": top_counter(subagent_meta_counts, signal_limit),
    }
    tool_output = {
        "high_output_context_read_count": len(high_output_search_records),
        "top_high_output_context_read": top_records(high_output_search_records, "score", signal_limit),
        "high_output_search_count": sum(1 for record in high_output_search_records if record.get("intent") == "search"),
        "top_high_output_search": top_records(
            [record for record in high_output_search_records if record.get("intent") == "search"],
            "score",
            signal_limit,
        ),
    }
    interaction_counts.update({f"queue_{key}": value for key, value in queue_ops.items()})
    interaction_counts.update({f"permission_{key}": value for key, value in permission_modes.items()})
    decision_signals = {
        "tool_latency": tool_latency,
        "tool_output": tool_output,
        "validation_poll_wait": validation_poll_wait,
        "wait_latency": wait_latency,
        "tool_failure": tool_failure,
        "token_cost": token_cost,
        "subagent_runtime": subagent_runtime,
        "interaction_interrupts": top_counter(interaction_counts, signal_limit),
    }
    bottlenecks = build_bottlenecks(
        tool_call_count=tool_call_count,
        search_count=search_count,
        high_output_context_read_count=len(high_output_search_records),
        validation_count=validation_count,
        subagent_count=subagent_count,
        retry_success_count=len(all_retry_success_paths),
        tool_failure_count=tool_failure_count,
        subagent_param_conflict_count=int(failure_kinds.get("subagent_param_conflict", 0)),
        resource_exhaustion_count=int(failure_kinds.get("resource_exhaustion", 0)),
        slow_tool_count=len(slow_roundtrips),
        human_decision_wait_count=len(human_decision_wait_records),
        infra_wait_count=0,
        token_total=int(token_usage_totals.get("total_tokens", 0)),
        long_gaps=long_gaps,
    )

    return {
        "runtime": "claude",
        "session_id": session_id,
        "title": title or path.stem,
        "file": str(path),
        "line_count": total_lines,
        "time_range": {"start": start_time, "end": end_time},
        "tool_call_count": tool_call_count,
        "tool_result_count": tool_result_count,
        "tool_call_counts": top_counter(tool_names),
        "event_counts": top_counter(top_types),
        "content_event_counts": top_counter(content_types),
        "hidden_event_counts": top_counter(hidden_events),
        "search_like_tool_calls": search_count,
        "validation_like_tool_calls": validation_count,
        "edit_like_tool_calls": edit_count,
        "subagent_count": subagent_count,
        "subagent_file_count": subagent_file_count,
        "tool_result_file_count": tool_result_file_count,
        "retry_success_path_count": len(all_retry_success_paths),
        "retry_success_paths": retry_success_paths,
        "decision_signals": decision_signals,
        "candidate_bottlenecks": bottlenecks,
        "suggested_read_lines": ranked_windows(suggested_windows),
    }


def aggregate_sessions(
    sessions: list[dict[str, Any]],
    *,
    signal_limit: int,
    include_deduplicated: bool = True,
) -> dict[str, Any]:
    runtimes: Counter[str] = Counter()
    tools: Counter[str] = Counter()
    bottlenecks: Counter[str] = Counter()
    retry_paths: Counter[str] = Counter()
    retry_categories: Counter[str] = Counter()
    failed_actions: Counter[str] = Counter()
    failure_kinds: Counter[str] = Counter()
    subagent_param_conflict_actions: Counter[str] = Counter()
    resource_exhaustion_actions: Counter[str] = Counter()
    token_usage_totals: Counter[str] = Counter()
    token_models: Counter[str] = Counter()
    token_speeds: Counter[str] = Counter()
    subagent_statuses: Counter[str] = Counter()
    subagent_models: Counter[str] = Counter()
    subagent_meta: Counter[str] = Counter()
    interaction_counts: Counter[str] = Counter()
    slow_execs: list[dict[str, Any]] = []
    slow_roundtrips: list[dict[str, Any]] = []
    validation_poll_wait_records: list[dict[str, Any]] = []
    high_output_search_records: list[dict[str, Any]] = []
    human_decision_wait_records: list[dict[str, Any]] = []
    infra_wait_records: list[dict[str, Any]] = []
    tool_calls = 0
    subagents = 0
    retry_success_path_count = 0
    failure_count = 0
    attempt_count = 0
    human_decision_wait_count = 0
    infra_wait_count = 0
    validation_poll_wait_count = 0
    high_output_context_read_count = 0
    high_output_search_count = 0
    token_usage_event_count = 0
    max_context_window = 0
    max_rate_limits: dict[str, float] = {}

    for session in sessions:
        runtimes[str(session.get("runtime") or "unknown")] += 1
        tool_calls += int(session.get("tool_call_count") or 0)
        subagents += int(session.get("subagent_count") or 0)
        tools.update({str(k): int(v) for k, v in session.get("tool_call_counts", {}).items()})
        paths = session.get("retry_success_paths") if isinstance(session.get("retry_success_paths"), list) else []
        retry_success_path_count += int(session.get("retry_success_path_count") or len(paths))
        for path in paths:
            if isinstance(path, dict):
                retry_paths[str(path.get("key") or "unknown")] += 1
                retry_categories[str(path.get("category") or "other")] += 1
        for item in session.get("candidate_bottlenecks", []):
            if isinstance(item, dict):
                bottlenecks[str(item.get("type") or "unknown")] += 1

        signals = session.get("decision_signals") if isinstance(session.get("decision_signals"), dict) else {}
        latency = signals.get("tool_latency") if isinstance(signals.get("tool_latency"), dict) else {}
        for item in latency.get("top_slow_exec", []):
            if isinstance(item, dict):
                slow_execs.append({**item, "session_id": session.get("session_id")})
        for item in latency.get("top_slow_roundtrip", []):
            if isinstance(item, dict):
                slow_roundtrips.append({**item, "session_id": session.get("session_id")})

        validation_poll = (
            signals.get("validation_poll_wait")
            if isinstance(signals.get("validation_poll_wait"), dict)
            else {}
        )
        validation_poll_summary = validation_poll.get("roundtrip_seconds")
        if isinstance(validation_poll_summary, dict):
            validation_poll_wait_count += int(validation_poll_summary.get("count") or 0)
        for item in validation_poll.get("top_slow_roundtrip", []):
            if isinstance(item, dict):
                validation_poll_wait_records.append({**item, "session_id": session.get("session_id")})

        tool_output = signals.get("tool_output") if isinstance(signals.get("tool_output"), dict) else {}
        high_output_context_read_count += int(
            tool_output.get("high_output_context_read_count")
            or tool_output.get("high_output_search_count")
            or 0
        )
        high_output_search_count += int(tool_output.get("high_output_search_count") or 0)
        for item in tool_output.get("top_high_output_context_read") or tool_output.get("top_high_output_search", []):
            if isinstance(item, dict):
                high_output_search_records.append({**item, "session_id": session.get("session_id")})

        wait_latency = signals.get("wait_latency") if isinstance(signals.get("wait_latency"), dict) else {}
        human_summary = wait_latency.get("human_decision_wait_seconds")
        if isinstance(human_summary, dict):
            human_decision_wait_count += int(human_summary.get("count") or 0)
        infra_summary = wait_latency.get("infra_wait_seconds")
        if isinstance(infra_summary, dict):
            infra_wait_count += int(infra_summary.get("count") or 0)
        for item in wait_latency.get("top_human_decision_wait", []):
            if isinstance(item, dict):
                human_decision_wait_records.append({**item, "session_id": session.get("session_id")})
        for item in wait_latency.get("top_infra_wait", []):
            if isinstance(item, dict):
                infra_wait_records.append({**item, "session_id": session.get("session_id")})

        failure = signals.get("tool_failure") if isinstance(signals.get("tool_failure"), dict) else {}
        failure_count += int(failure.get("failure_count") or 0)
        attempt_count += int(failure.get("attempt_count") or 0)
        merge_counter_from_dict(failed_actions, failure.get("top_failed_actions"))
        merge_counter_from_dict(failure_kinds, failure.get("failure_kind_counts"))
        merge_counter_from_dict(
            subagent_param_conflict_actions,
            failure.get("top_subagent_param_conflict_actions"),
        )
        merge_counter_from_dict(
            resource_exhaustion_actions,
            failure.get("top_resource_exhaustion_actions"),
        )

        token_cost = signals.get("token_cost") if isinstance(signals.get("token_cost"), dict) else {}
        add_token_usage(token_usage_totals, token_cost.get("total_usage"))
        token_usage_event_count += int(token_cost.get("usage_event_count") or 0)
        if isinstance(token_cost.get("max_context_window"), int):
            max_context_window = max(max_context_window, int(token_cost["max_context_window"]))
        merge_counter_from_dict(token_models, token_cost.get("model_counts"))
        merge_counter_from_dict(token_speeds, token_cost.get("speed_counts"))
        rate_limits = token_cost.get("max_rate_limits") if isinstance(token_cost.get("max_rate_limits"), dict) else {}
        for key, value in rate_limits.items():
            if isinstance(value, (int, float)):
                max_rate_limits[str(key)] = max(max_rate_limits.get(str(key), 0.0), round(float(value), 2))

        subagent_runtime = (
            signals.get("subagent_runtime") if isinstance(signals.get("subagent_runtime"), dict) else {}
        )
        merge_counter_from_dict(subagent_statuses, subagent_runtime.get("spawn_status_counts"))
        merge_counter_from_dict(subagent_models, subagent_runtime.get("spawn_model_effort_counts"))
        merge_counter_from_dict(subagent_meta, subagent_runtime.get("subagent_meta_counts"))

        merge_counter_from_dict(interaction_counts, signals.get("interaction_interrupts"))

    result: dict[str, Any] = {
        "session_count": len(sessions),
        "runtime_counts": dict(runtimes),
        "tool_call_count": tool_calls,
        "subagent_count": subagents,
        "retry_success_path_count": retry_success_path_count,
        "top_retry_success_categories": top_counter(retry_categories, signal_limit),
        "top_retry_success_paths": top_counter(retry_paths, signal_limit),
        "top_tool_names": top_counter(tools),
        "bottleneck_type_counts": top_counter(bottlenecks),
        "decision_signals": {
            "tool_latency": {
                "top_slow_exec": top_records(slow_execs, "seconds", signal_limit),
                "top_slow_roundtrip": top_records(slow_roundtrips, "seconds", signal_limit),
            },
            "tool_output": {
                "high_output_context_read_count": high_output_context_read_count,
                "top_high_output_context_read": top_records(high_output_search_records, "score", signal_limit),
                "high_output_search_count": high_output_search_count,
                "top_high_output_search": top_records(
                    [record for record in high_output_search_records if record.get("intent") == "search"],
                    "score",
                    signal_limit,
                ),
            },
            "validation_poll_wait": {
                "roundtrip_count": validation_poll_wait_count,
                "top_slow_roundtrip": top_records(validation_poll_wait_records, "seconds", signal_limit),
            },
            "wait_latency": {
                "human_decision_wait_count": human_decision_wait_count,
                "infra_wait_count": infra_wait_count,
                "top_human_decision_wait": top_records(human_decision_wait_records, "seconds", signal_limit),
                "top_infra_wait": top_records(infra_wait_records, "seconds", signal_limit),
            },
            "tool_failure": {
                "failure_count": failure_count,
                "attempt_count": attempt_count,
                "failure_rate_percent": percent(failure_count, attempt_count),
                "top_failed_actions": top_counter(failed_actions, signal_limit),
                "failure_kind_counts": top_counter(failure_kinds, signal_limit),
                "top_subagent_param_conflict_actions": top_counter(
                    subagent_param_conflict_actions,
                    signal_limit,
                ),
                "top_resource_exhaustion_actions": top_counter(
                    resource_exhaustion_actions,
                    signal_limit,
                ),
            },
            "token_cost": {
                "usage_event_count": token_usage_event_count,
                "total_usage": dict(token_usage_totals),
                "model_counts": top_counter(token_models, signal_limit),
                "speed_counts": top_counter(token_speeds, signal_limit),
                "max_rate_limits": max_rate_limits,
                "max_context_window": max_context_window,
            },
            "subagent_runtime": {
                "spawn_status_counts": top_counter(subagent_statuses, signal_limit),
                "spawn_model_effort_counts": top_counter(subagent_models, signal_limit),
                "subagent_meta_counts": top_counter(subagent_meta, signal_limit),
            },
            "interaction_interrupts": top_counter(interaction_counts, signal_limit),
        },
    }
    if include_deduplicated:
        deduped_sessions, duplicate_groups = deduplicate_codex_fork_rollouts(
            sessions,
            signal_limit=signal_limit,
        )
        result["deduplicated"] = {
            "session_count": len(deduped_sessions),
            "duplicate_group_count": len(duplicate_groups),
            "duplicate_groups": duplicate_groups,
            "aggregate": aggregate_sessions(
                deduped_sessions,
                signal_limit=signal_limit,
                include_deduplicated=False,
            ),
        }
    return result


def compact_top_records(records: list[dict[str, Any]], limit: int) -> list[str]:
    """压缩 Top 记录，避免日报 summary 展开完整嵌套 signal。"""
    compacted: list[str] = []
    for item in records[: max(0, limit)]:
        if not isinstance(item, dict):
            continue
        parts: list[str] = []
        for key in ("session_id", "tool_name", "intent"):
            value = item.get(key)
            if value:
                parts.append(f"{key}[{value}]")
        for key in ("tokens", "chars", "score", "seconds", "line", "exit_code"):
            value = item.get(key)
            if value is not None and value != "":
                parts.append(f"{key}[{value}]")
        if item.get("lines"):
            parts.append(f"lines[{item['lines']}]")
        if item.get("key"):
            parts.append(f"key[{compact_text(item['key'], 120)}]")
        if parts:
            compacted.append(" ".join(parts))
    return compacted


def compact_decision_signals(signals: Any, *, signal_limit: int) -> dict[str, Any]:
    """保留日报判断需要的 signal，丢弃大段 session 级嵌套细节。"""
    if not isinstance(signals, dict):
        return {}
    record_limit = min(max(0, signal_limit), 3)
    latency = signals.get("tool_latency") if isinstance(signals.get("tool_latency"), dict) else {}
    tool_output = signals.get("tool_output") if isinstance(signals.get("tool_output"), dict) else {}
    failure = signals.get("tool_failure") if isinstance(signals.get("tool_failure"), dict) else {}
    validation = signals.get("validation_poll_wait") if isinstance(signals.get("validation_poll_wait"), dict) else {}
    wait = signals.get("wait_latency") if isinstance(signals.get("wait_latency"), dict) else {}
    token = signals.get("token_cost") if isinstance(signals.get("token_cost"), dict) else {}
    return {
        "tool_latency": {
            "top_slow_exec": compact_top_records(latency.get("top_slow_exec", []), record_limit),
            "top_slow_roundtrip": compact_top_records(latency.get("top_slow_roundtrip", []), record_limit),
        },
        "tool_output": {
            "high_output_context_read_count": int(tool_output.get("high_output_context_read_count") or 0),
            "top_high_output_context_read": compact_top_records(
                tool_output.get("top_high_output_context_read", []),
                record_limit,
            ),
            "high_output_search_count": int(tool_output.get("high_output_search_count") or 0),
        },
        "validation_poll_wait": validation,
        "wait_latency": wait,
        "tool_failure": {
            "failure_count": int(failure.get("failure_count") or 0),
            "attempt_count": int(failure.get("attempt_count") or 0),
            "failure_rate_percent": failure.get("failure_rate_percent", 0.0),
            "top_failed_actions": failure.get("top_failed_actions", {}),
            "failure_kind_counts": failure.get("failure_kind_counts", {}),
            "top_subagent_param_conflict_actions": failure.get("top_subagent_param_conflict_actions", {}),
            "top_resource_exhaustion_actions": failure.get("top_resource_exhaustion_actions", {}),
        },
        "token_cost": {
            "usage_event_count": int(token.get("usage_event_count") or 0),
            "total_usage": token.get("total_usage", {}),
            "max_rate_limits": token.get("max_rate_limits", {}),
            "max_context_window": token.get("max_context_window", 0),
        },
        "subagent_runtime": signals.get("subagent_runtime", {}),
        "interaction_interrupts": signals.get("interaction_interrupts", {}),
    }


def compact_aggregate_summary(aggregate: dict[str, Any], *, signal_limit: int) -> dict[str, Any]:
    """生成 automation 日报默认消费的聚合摘要。"""
    source = aggregate
    deduplicated = aggregate.get("deduplicated") if isinstance(aggregate.get("deduplicated"), dict) else None
    if deduplicated and int(deduplicated.get("duplicate_group_count") or 0) > 0:
        deduped_aggregate = deduplicated.get("aggregate")
        if isinstance(deduped_aggregate, dict):
            source = deduped_aggregate

    result: dict[str, Any] = {
        "session_count": source.get("session_count", 0),
        "runtime_counts": source.get("runtime_counts", {}),
        "tool_call_count": source.get("tool_call_count", 0),
        "subagent_count": source.get("subagent_count", 0),
        "retry_success_path_count": source.get("retry_success_path_count", 0),
        "top_retry_success_categories": source.get("top_retry_success_categories", {}),
        "top_retry_success_paths": source.get("top_retry_success_paths", {}),
        "top_tool_names": source.get("top_tool_names", {}),
        "bottleneck_type_counts": source.get("bottleneck_type_counts", {}),
        "decision_signals": compact_decision_signals(
            source.get("decision_signals"),
            signal_limit=signal_limit,
        ),
    }
    if deduplicated:
        result["deduplicated"] = {
            "session_count": deduplicated.get("session_count", 0),
            "raw_session_count": aggregate.get("session_count", 0),
            "raw_tool_call_count": aggregate.get("tool_call_count", 0),
            "duplicate_group_count": deduplicated.get("duplicate_group_count", 0),
            "duplicate_groups": deduplicated.get("duplicate_groups", [])[: max(0, signal_limit)],
        }
    return result


def compact_session_decision_signals(signals: Any) -> dict[str, Any]:
    """Top session 只保留计数，Top evidence 统一放在 aggregate。"""
    if not isinstance(signals, dict):
        return {}
    tool_output = signals.get("tool_output") if isinstance(signals.get("tool_output"), dict) else {}
    failure = signals.get("tool_failure") if isinstance(signals.get("tool_failure"), dict) else {}
    validation = signals.get("validation_poll_wait") if isinstance(signals.get("validation_poll_wait"), dict) else {}
    wait = signals.get("wait_latency") if isinstance(signals.get("wait_latency"), dict) else {}
    token = signals.get("token_cost") if isinstance(signals.get("token_cost"), dict) else {}
    validation_summary = validation.get("roundtrip_seconds") if isinstance(validation.get("roundtrip_seconds"), dict) else {}
    human_summary = wait.get("human_decision_wait_seconds") if isinstance(wait.get("human_decision_wait_seconds"), dict) else {}
    infra_summary = wait.get("infra_wait_seconds") if isinstance(wait.get("infra_wait_seconds"), dict) else {}
    total_usage = token.get("total_usage") if isinstance(token.get("total_usage"), dict) else {}
    return {
        "tool_output": {
            "high_output_context_read_count": int(tool_output.get("high_output_context_read_count") or 0),
            "high_output_search_count": int(tool_output.get("high_output_search_count") or 0),
        },
        "validation_poll_wait": {
            "roundtrip_count": int(
                validation.get("roundtrip_count")
                or validation_summary.get("count")
                or 0
            ),
        },
        "wait_latency": {
            "human_decision_wait_count": int(
                wait.get("human_decision_wait_count")
                or human_summary.get("count")
                or 0
            ),
            "infra_wait_count": int(
                wait.get("infra_wait_count")
                or infra_summary.get("count")
                or 0
            ),
        },
        "tool_failure": {
            "failure_count": int(failure.get("failure_count") or 0),
            "attempt_count": int(failure.get("attempt_count") or 0),
            "failure_kind_counts": failure.get("failure_kind_counts", {}),
        },
        "token_cost": {
            "usage_event_count": int(token.get("usage_event_count") or 0),
            "total_tokens": int(total_usage.get("total_tokens") or 0),
            "max_context_window": token.get("max_context_window", 0),
        },
    }


def compact_session_summary(session: dict[str, Any], *, signal_limit: int) -> dict[str, Any]:
    time_range = session.get("time_range") if isinstance(session.get("time_range"), dict) else {}
    item_limit = min(max(0, signal_limit), 5)
    bottlenecks = []
    for item in (session.get("candidate_bottlenecks") or [])[:item_limit]:
        if isinstance(item, dict):
            bottlenecks.append(f"{item.get('type', 'unknown')}:{item.get('severity', 'unknown')}")
    suggested = []
    for item in (session.get("suggested_read_lines") or [])[:item_limit]:
        if isinstance(item, dict):
            suggested.append(f"{item.get('start')}-{item.get('end')} {item.get('reason', '')}")
    tool_counts = session.get("tool_call_counts") if isinstance(session.get("tool_call_counts"), dict) else {}
    tool_call_counts = ", ".join(f"{key}[{value}]" for key, value in tool_counts.items())
    return {
        "runtime": session.get("runtime"),
        "session_id": session.get("session_id"),
        "title": session.get("title"),
        "file": session.get("file"),
        "time_range": f"{time_range.get('start')}..{time_range.get('end')}",
        "line_count": session.get("line_count"),
        "tool_call_count": session.get("tool_call_count"),
        "search_like_tool_calls": session.get("search_like_tool_calls"),
        "validation_like_tool_calls": session.get("validation_like_tool_calls"),
        "edit_like_tool_calls": session.get("edit_like_tool_calls"),
        "subagent_count": session.get("subagent_count"),
        "retry_success_path_count": session.get("retry_success_path_count"),
        "tool_call_counts": tool_call_counts,
        "candidate_bottlenecks": bottlenecks,
        "suggested_read_lines": suggested,
        "decision_signals": compact_session_decision_signals(session.get("decision_signals")),
    }


def compact_top_session_summaries(
    sessions: list[dict[str, Any]],
    limit: int,
    *,
    signal_limit: int,
) -> list[dict[str, Any]]:
    ranked = sorted(
        sessions,
        key=lambda item: int(item.get("tool_call_count") or 0),
        reverse=True,
    )
    return [
        compact_session_summary(session, signal_limit=signal_limit)
        for session in ranked[: max(0, limit)]
    ]


def session_summary(session: dict[str, Any]) -> dict[str, Any]:
    return {
        "runtime": session.get("runtime"),
        "session_id": session.get("session_id"),
        "title": session.get("title"),
        "file": session.get("file"),
        "cwd": session.get("cwd"),
        "forked_from_id": session.get("forked_from_id"),
        "git": session.get("git"),
        "time_range": session.get("time_range"),
        "line_count": session.get("line_count"),
        "tool_call_count": session.get("tool_call_count"),
        "search_like_tool_calls": session.get("search_like_tool_calls"),
        "validation_like_tool_calls": session.get("validation_like_tool_calls"),
        "edit_like_tool_calls": session.get("edit_like_tool_calls"),
        "subagent_count": session.get("subagent_count"),
        "retry_success_path_count": session.get("retry_success_path_count"),
        "retry_success_paths": session.get("retry_success_paths"),
        "decision_signals": session.get("decision_signals"),
        "tool_call_counts": session.get("tool_call_counts"),
        "candidate_bottlenecks": session.get("candidate_bottlenecks"),
        "suggested_read_lines": session.get("suggested_read_lines"),
    }


def top_session_summaries(sessions: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    ranked = sorted(
        sessions,
        key=lambda item: int(item.get("tool_call_count") or 0),
        reverse=True,
    )
    return [session_summary(session) for session in ranked[: max(0, limit)]]


def collect_claude_session_dates(path: Path) -> set[str]:
    dates: set[str] = set()
    try:
        handle = path.open(encoding="utf-8")
    except OSError:
        return dates

    with handle:
        for line in handle:
            obj = safe_json_loads(line)
            if obj is None:
                continue
            event_date = timestamp_date(str(obj.get("timestamp") or ""))
            if event_date:
                dates.add(event_date)
    if not dates:
        fallback_date = path_mtime_date(path)
        if fallback_date:
            dates.add(fallback_date)
    return dates


def build_top_days(
    *,
    runtime: str,
    codex_home: Path,
    claude_project_dir: Path,
    explicit_files: dict[str, list[Path]],
    cwd: Path,
    include_all_cwd: bool,
    limit: int,
) -> list[dict[str, Any]]:
    codex_index, _ = load_codex_index(codex_home, "")
    codex_index_ids_by_date: dict[str, set[str]] = {}
    for session_id, entry in codex_index.items():
        entry_date = timestamp_date(entry.get("updated_at"))
        if entry_date:
            codex_index_ids_by_date.setdefault(entry_date, set()).add(session_id)

    codex_files_by_date: dict[str, set[Path]] = {}
    if runtime in ("auto", "codex"):
        archive_dir = codex_home / "archived_sessions"
        codex_candidates: set[Path] = set(explicit_files["codex"])
        if archive_dir.exists():
            codex_candidates.update(path for path in archive_dir.glob("rollout-*.jsonl") if path.is_file())
        filtered_codex_candidates, _ = filter_codex_files_by_cwd(
            sorted(codex_candidates),
            cwd=cwd,
            explicit_files=explicit_files["codex"],
            include_all_cwd=include_all_cwd,
            signal_limit=limit,
        )
        for path in filtered_codex_candidates:
            file_date = codex_file_date(path)
            if file_date:
                codex_files_by_date.setdefault(file_date, set()).add(path)
            session_id = uuid_from_text(path.name)
            if not session_id:
                continue
            for entry_date, ids in codex_index_ids_by_date.items():
                if session_id in ids:
                    codex_files_by_date.setdefault(entry_date, set()).add(path)

    claude_counts_by_date: Counter[str] = Counter()
    if runtime in ("auto", "claude"):
        claude_files = collect_claude_files(
            claude_project_dir=claude_project_dir,
            explicit_files=explicit_files["claude"],
        )
        for path in claude_files:
            for session_date in collect_claude_session_dates(path):
                claude_counts_by_date[session_date] += 1

    all_dates = set(codex_files_by_date) | set(claude_counts_by_date)
    rows: list[dict[str, Any]] = []
    for session_date in sorted(all_dates):
        codex_count = len(codex_files_by_date.get(session_date, set()))
        claude_count = int(claude_counts_by_date.get(session_date, 0))
        rows.append(
            {
                "date": session_date,
                "session_count": codex_count + claude_count,
                "runtime_counts": {
                    "codex": codex_count,
                    "claude": claude_count,
                },
                "codex_index_count": len(codex_index_ids_by_date.get(session_date, set())),
            }
        )

    rows.sort(key=lambda item: (int(item["session_count"]), item["date"]), reverse=True)
    return rows[: max(0, limit)]


def parse_line_ranges(raw_ranges: list[str]) -> list[dict[str, int]]:
    ranges: list[dict[str, int]] = []
    for raw in raw_ranges:
        for part in re.split(r"[,\s]+", raw):
            if not part:
                continue
            match = re.fullmatch(r"(\d+)(?:-(\d+))?", part)
            if not match:
                raise SystemExit(f"--summarize-lines must use START-END or LINE, got: {part}")
            start = int(match.group(1))
            end = int(match.group(2) or start)
            if start <= 0 or end < start:
                raise SystemExit(f"Invalid line range: {part}")
            ranges.append({"start": start, "end": end})
    if not ranges:
        raise SystemExit("--summarize-lines requires at least one line range")
    ranges.sort(key=lambda item: (item["start"], item["end"]))
    return ranges


def range_label(line_no: int, ranges: list[dict[str, int]]) -> str | None:
    for item in ranges:
        if item["start"] <= line_no <= item["end"]:
            return f"{item['start']}-{item['end']}"
    return None


def summarize_event_line(
    *,
    line_no: int,
    obj: dict[str, Any],
    codex_calls: dict[str, dict[str, Any]],
    claude_calls: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """将 transcript 单行压缩成可引用摘要，避免输出大段工具结果。"""
    payload = obj.get("payload") if isinstance(obj.get("payload"), dict) else {}
    timestamp = str(obj.get("timestamp") or payload.get("timestamp") or "")
    payload_type = str(payload.get("type") or obj.get("type") or "")
    base = {
        "line": line_no,
        "timestamp": timestamp,
        "event_type": payload_type,
    }

    if payload_type in HIDDEN_CONTENT_TYPES:
        return [{**base, "hidden": True, "summary": f"{payload_type} hidden"}]

    if payload_type in ("function_call", "custom_tool_call"):
        tool_name = str(payload.get("name") or "unknown")
        raw_details = (
            payload.get("arguments")
            if payload.get("arguments") is not None
            else payload.get("input")
            if payload.get("input") is not None
            else payload.get("content")
        )
        call_id = str(payload.get("call_id") or "")
        key = tool_action_key(tool_name, raw_details)
        if call_id:
            codex_calls[call_id] = {
                "tool_name": tool_name,
                "key": key,
                "line": line_no,
            }
        return [
            {
                **base,
                "tool_name": tool_name,
                "call_id": call_id,
                "key": compact_text(key, 220),
                "arguments_excerpt": compact_visible_text(raw_details, 260),
            }
        ]

    if payload_type in ("function_call_output", "custom_tool_call_output"):
        output = payload.get("output")
        call_id = str(payload.get("call_id") or "")
        call = codex_calls.get(call_id, {})
        return [
            {
                **base,
                "tool_name": call.get("tool_name"),
                "call_id": call_id,
                "call_line": call.get("line"),
                "key": compact_text(call.get("key"), 220),
                "status": classify_output_attempt(output),
                "exit_code": extract_exit_code(output),
                "original_token_count": extract_original_token_count(output),
                "output_chars": len(full_output_text(output)),
                "output_excerpt": compact_visible_text(output, 260),
            }
        ]

    if payload_type == "token_count":
        info = payload.get("info") if isinstance(payload.get("info"), dict) else {}
        return [
            {
                **base,
                "total_usage": token_usage_snapshot(info.get("total_token_usage")),
                "last_usage": token_usage_snapshot(info.get("last_token_usage")),
                "model_context_window": info.get("model_context_window"),
            }
        ]

    if payload_type == "session_meta":
        git = payload.get("git") if isinstance(payload.get("git"), dict) else {}
        return [
            {
                **base,
                "session_id": payload.get("id"),
                "cwd": payload.get("cwd"),
                "forked_from_id": payload.get("forked_from_id"),
                "git": {
                    "branch": git.get("branch"),
                    "commit_hash": git.get("commit_hash"),
                },
            }
        ]

    if payload_type in ("exec_command_end", "patch_apply_end", "collab_agent_spawn_end"):
        return [
            {
                **base,
                "status": payload.get("status"),
                "success": payload.get("success"),
                "exit_code": payload.get("exit_code"),
                "duration": payload.get("duration"),
                "summary": compact_visible_text(payload, 260),
            }
        ]

    events: list[dict[str, Any]] = []
    message = obj.get("message") if isinstance(obj.get("message"), dict) else {}
    for item in claude_content_items(message):
        item_type = str(item.get("type") or "")
        item_base = {**base, "event_type": item_type or payload_type}
        if item_type in HIDDEN_CONTENT_TYPES:
            events.append({**item_base, "hidden": True, "summary": f"{item_type} hidden"})
            continue
        if item_type == "tool_use":
            tool_name = str(item.get("name") or "unknown")
            tool_use_id = str(item.get("id") or "")
            key = tool_action_key(tool_name, item.get("input"))
            if tool_use_id:
                claude_calls[tool_use_id] = {
                    "tool_name": tool_name,
                    "key": key,
                    "line": line_no,
                }
            events.append(
                {
                    **item_base,
                    "tool_name": tool_name,
                    "tool_use_id": tool_use_id,
                    "key": compact_text(key, 220),
                    "input_excerpt": compact_visible_text(item.get("input"), 260),
                }
            )
        elif item_type == "tool_result":
            content = item.get("content")
            tool_use_id = str(item.get("tool_use_id") or "")
            call = claude_calls.get(tool_use_id, {})
            events.append(
                {
                    **item_base,
                    "tool_name": call.get("tool_name"),
                    "tool_use_id": tool_use_id,
                    "call_line": call.get("line"),
                    "key": compact_text(call.get("key"), 220),
                    "is_error": item.get("is_error"),
                    "original_token_count": extract_original_token_count(content),
                    "content_chars": len(full_output_text(content)),
                    "content_excerpt": compact_visible_text(content, 260),
                }
            )
        else:
            events.append({**item_base, "summary": compact_visible_text(item, 260)})

    if events:
        return events

    return [
        {
            **base,
            "summary": compact_visible_text(payload or obj, 260),
        }
    ]


def summarize_transcript_lines(path: Path, ranges: list[dict[str, int]]) -> dict[str, Any]:
    max_end = max(item["end"] for item in ranges)
    codex_calls: dict[str, dict[str, Any]] = {}
    claude_calls: dict[str, dict[str, Any]] = {}
    events: list[dict[str, Any]] = []
    total_lines = 0

    with path.open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            total_lines = line_no
            if line_no > max_end:
                break
            obj = safe_json_loads(line)
            if obj is None:
                continue
            label = range_label(line_no, ranges)
            summarized_events = summarize_event_line(
                line_no=line_no,
                obj=obj,
                codex_calls=codex_calls,
                claude_calls=claude_calls,
            )
            if label is not None:
                for event in summarized_events:
                    events.append({**event, "range": label})

    return {
        "status": "ready",
        "input_path": str(path),
        "line_ranges": ranges,
        "line_count_scanned": total_lines,
        "event_count": len(events),
        "events": events,
    }


def main() -> int:
    args = parse_args()
    cwd = expand_path(args.cwd)
    codex_home = expand_path(args.codex_home)
    claude_home = expand_path(args.claude_home)
    claude_project_dir = claude_home / "projects" / project_slug(cwd)
    output_root = expand_path(args.output_root)
    input_path = expand_path(args.input) if args.input else None

    if args.summarize_lines:
        if input_path is None or not input_path.is_file():
            raise SystemExit("--summarize-lines requires an input JSONL file")
        line_ranges = parse_line_ranges(args.summarize_lines)
        print(json.dumps(summarize_transcript_lines(input_path, line_ranges), ensure_ascii=False, indent=2))
        return 0

    explicit_files = collect_explicit_files(input_path, args.runtime)

    if args.top_days:
        top_days = build_top_days(
            runtime=args.runtime,
            codex_home=codex_home,
            claude_project_dir=claude_project_dir,
            explicit_files=explicit_files,
            cwd=cwd,
            include_all_cwd=args.all_cwd,
            limit=args.limit,
        )
        result = {
            "status": "ready" if top_days else "empty",
            "runtime": args.runtime,
            "cwd": str(cwd),
            "input_path": str(input_path) if input_path is not None else None,
            "top_days": top_days,
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if args.target_date == "auto-max":
        top_days = build_top_days(
            runtime=args.runtime,
            codex_home=codex_home,
            claude_project_dir=claude_project_dir,
            explicit_files=explicit_files,
            cwd=cwd,
            include_all_cwd=args.all_cwd,
            limit=1,
        )
        if not top_days:
            raise SystemExit("--date auto-max found no visible sessions")
        target_date = str(top_days[0]["date"])
    else:
        target_date = validate_date(args.target_date)

    output_dir = output_root / target_date
    sessions: list[dict[str, Any]] = []
    sources: dict[str, Any] = {}

    if args.runtime in ("auto", "codex"):
        codex_index, ids_for_date = load_codex_index(codex_home, target_date)
        codex_files = collect_codex_files(
            codex_home=codex_home,
            target_date=target_date,
            index_ids_for_date=ids_for_date,
            explicit_files=explicit_files["codex"],
        )
        codex_files, codex_cwd_filter = filter_codex_files_by_cwd(
            codex_files,
            cwd=cwd,
            explicit_files=explicit_files["codex"],
            include_all_cwd=args.all_cwd,
            signal_limit=args.signal_limit,
        )
        sources["codex"] = {
            "home": str(codex_home),
            "session_index": str(codex_home / "session_index.jsonl"),
            **codex_cwd_filter,
        }
        for path in codex_files:
            session = analyze_codex_file(
                path,
                target_date=target_date,
                index=codex_index,
                signal_limit=args.signal_limit,
            )
            if session is not None:
                sessions.append(session)

    if args.runtime in ("auto", "claude"):
        claude_files = collect_claude_files(
            claude_project_dir=claude_project_dir,
            explicit_files=explicit_files["claude"],
        )
        sources["claude"] = {
            "home": str(claude_home),
            "project_dir": str(claude_project_dir),
            "candidate_file_count": len(claude_files),
        }
        for path in claude_files:
            session = analyze_claude_file(
                path,
                target_date=target_date,
                project_dir=claude_project_dir,
                signal_limit=args.signal_limit,
            )
            if session is not None:
                sessions.append(session)

    sessions.sort(key=lambda item: str(item.get("time_range", {}).get("start") or item.get("file") or ""))
    empty_report_path = output_dir / f"{DEFAULT_EMPTY_TITLE}.md"
    result = {
        "status": "ready" if sessions else "empty",
        "target_date": target_date,
        "runtime": args.runtime,
        "cwd": str(cwd),
        "input_path": str(input_path) if input_path is not None else None,
        "sources": sources,
        "output_dir": str(output_dir),
        "empty_report_path": str(empty_report_path),
        "empty_report_created": False,
        "aggregate": aggregate_sessions(sessions, signal_limit=args.signal_limit),
    }
    if args.summary_only:
        top_limit = args.top if args.top is not None else (3 if args.compact else 10)
        if args.compact:
            summary_sessions, _ = deduplicate_codex_fork_rollouts(
                sessions,
                signal_limit=args.signal_limit,
            )
            result["compact"] = True
            result["aggregate"] = compact_aggregate_summary(
                result["aggregate"],
                signal_limit=args.signal_limit,
            )
            result["top_sessions"] = compact_top_session_summaries(
                summary_sessions,
                top_limit,
                signal_limit=args.signal_limit,
            )
        else:
            result["top_sessions"] = top_session_summaries(sessions, top_limit)
    else:
        result["sessions"] = sessions

    if not sessions and not args.dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)
        empty_report_path.write_text(
            render_empty_report(
                report_date=target_date,
                runtime=args.runtime,
                cwd=cwd,
                codex_home=codex_home,
                claude_project_dir=claude_project_dir,
                input_path=input_path,
            ),
            encoding="utf-8",
        )
        result["empty_report_created"] = True

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
