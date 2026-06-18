#!/usr/bin/env python3
"""Review-first Claude bridge for Codex backed by `claude-agent-acp`.

The documented path is intentionally narrow:
- run a second-opinion review against the working tree, selected paths, or images
- keep Codex as the implementation owner
- preserve detached jobs so long reviews do not block the main session
"""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import queue
import shlex
import signal
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path
from typing import Any


PROTOCOL_VERSION = 1
AGENT_COMMAND_ENV = "TO_CLAUDE_REVIEW_AGENT_COMMAND"
RESPONSE_POLL_INTERVAL_ENV = "TO_CLAUDE_REVIEW_RESPONSE_POLL_INTERVAL"
REQUEST_IDLE_TIMEOUT_ENV = "TO_CLAUDE_REVIEW_REQUEST_IDLE_TIMEOUT"
REQUEST_MAX_TIMEOUT_ENV = "TO_CLAUDE_REVIEW_REQUEST_MAX_TIMEOUT"
JOB_WAIT_POLL_INTERVAL_ENV = "TO_CLAUDE_REVIEW_JOB_WAIT_POLL_INTERVAL"
JOB_HEARTBEAT_INTERVAL_ENV = "TO_CLAUDE_REVIEW_JOB_HEARTBEAT_INTERVAL"
JOB_ROOT_ENV = "TO_CLAUDE_REVIEW_JOB_ROOT"
JOB_ID_ENV = "TO_CLAUDE_REVIEW_JOB_ID"
JOB_DIR_ENV = "TO_CLAUDE_REVIEW_JOB_DIR"
JOB_STATUS_FILE_ENV = "TO_CLAUDE_REVIEW_JOB_STATUS_FILE"
JOB_STDOUT_FILE_ENV = "TO_CLAUDE_REVIEW_JOB_STDOUT_FILE"
JOB_STDERR_FILE_ENV = "TO_CLAUDE_REVIEW_JOB_STDERR_FILE"
JOB_CANCEL_FILE_ENV = "TO_CLAUDE_REVIEW_JOB_CANCEL_FILE"
DEFAULT_JOB_ROOT = "~/.codex/to-claude-review/jobs"


def env_value(name: str, default: str = "") -> str:
    value = os.environ.get(name, "").strip()
    return value if value else default


def float_env_value(name: str, default: str) -> float:
    return float(env_value(name, default))


DEFAULT_AGENT_COMMAND = env_value(AGENT_COMMAND_ENV, "claude-agent-acp")
RESPONSE_POLL_INTERVAL = max(
    0.1,
    float_env_value(RESPONSE_POLL_INTERVAL_ENV, "1.0"),
)
REQUEST_IDLE_TIMEOUT = max(
    1.0,
    float_env_value(REQUEST_IDLE_TIMEOUT_ENV, "900"),
)
REQUEST_MAX_TIMEOUT = max(
    0.0,
    float_env_value(REQUEST_MAX_TIMEOUT_ENV, "14400"),
)
JOB_WAIT_POLL_INTERVAL = max(
    0.1,
    float_env_value(JOB_WAIT_POLL_INTERVAL_ENV, "1.0"),
)
JOB_HEARTBEAT_INTERVAL = max(
    1.0,
    float_env_value(JOB_HEARTBEAT_INTERVAL_ENV, "5.0"),
)
DEFAULT_CLIENT_CAPABILITIES = {
    "auth": {"terminal": True},
    "_meta": {
        "terminal-auth": True,
        "terminal_output": True,
    },
}
TERMINAL_JOB_STATES = {"completed", "failed", "cancelled"}
SUBCOMMANDS = {
    "review",
    "jobs",
    "job-status",
    "job-wait",
    "job-cancel",
}

PERMISSION_ORDER = {
    "accept-edits": [
        "acceptEdits",
        "allow_always",
        "default",
        "allow",
        "auto",
        "bypassPermissions",
    ],
    "allow": [
        "allow",
        "default",
        "acceptEdits",
        "auto",
        "allow_always",
        "bypassPermissions",
    ],
    "allow-always": [
        "allow_always",
        "auto",
        "acceptEdits",
        "bypassPermissions",
        "allow",
        "default",
    ],
    "auto": [
        "auto",
        "allow_always",
        "acceptEdits",
        "default",
        "allow",
        "bypassPermissions",
    ],
    "bypass-permissions": [
        "bypassPermissions",
        "auto",
        "allow_always",
        "acceptEdits",
        "allow",
        "default",
    ],
    "default": [
        "default",
        "allow",
        "acceptEdits",
        "allow_always",
        "plan",
    ],
    "plan": [
        "plan",
        "reject",
        "default",
    ],
    "reject": [
        "reject",
        "plan",
    ],
}

PERMISSION_KIND_FALLBACKS = {
    "accept-edits": ["allow_always", "allow_once"],
    "allow": ["allow_once", "allow_always"],
    "allow-always": ["allow_always", "allow_once"],
    "auto": ["allow_always", "allow_once"],
    "bypass-permissions": ["allow_always", "allow_once"],
    "default": ["allow_once", "allow_always"],
    "plan": ["reject_once", "allow_once"],
    "reject": ["reject_once"],
}


class RpcError(RuntimeError):
    """JSON-RPC request failure."""


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def write_json_atomically(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp_path.replace(path)


class JobStatusWriter:
    def __init__(self, *, command: str) -> None:
        status_path = env_value(JOB_STATUS_FILE_ENV)
        self.status_file = Path(status_path).expanduser() if status_path else None
        stdout_path = env_value(JOB_STDOUT_FILE_ENV)
        stderr_path = env_value(JOB_STDERR_FILE_ENV)
        self.payload: dict[str, Any] = {}
        self._write_lock = threading.Lock()
        self._last_heartbeat_write = 0.0

        if self.status_file is not None and self.status_file.is_file():
            try:
                loaded = json.loads(self.status_file.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                loaded = {}
            if isinstance(loaded, dict):
                self.payload.update(loaded)

        self.payload.setdefault("command", command)
        self.payload.setdefault("pid", os.getpid())
        self.payload.setdefault("createdAt", utc_now())

        if self.status_file is not None:
            self.payload.setdefault("jobId", env_value(JOB_ID_ENV, self.status_file.parent.name))
            self.payload.setdefault("jobDir", env_value(JOB_DIR_ENV, str(self.status_file.parent)))
            self.payload.setdefault("statusFile", str(self.status_file))
        if stdout_path:
            self.payload.setdefault("stdoutFile", stdout_path)
        if stderr_path:
            self.payload.setdefault("stderrFile", stderr_path)
        cancel_path = env_value(JOB_CANCEL_FILE_ENV)
        if cancel_path:
            self.payload.setdefault("cancelFile", cancel_path)

    def update(self, **fields: Any) -> None:
        if self.status_file is None:
            return
        with self._write_lock:
            self.payload.update(fields)
            timestamp = utc_now()
            self.payload["updatedAt"] = timestamp
            if fields.get("state") in TERMINAL_JOB_STATES:
                self.payload["finishedAt"] = fields.get("finishedAt", timestamp)
            write_json_atomically(self.status_file, self.payload)

    def heartbeat(self) -> None:
        if self.status_file is None:
            return
        now = time.monotonic()
        should_write = False
        with self._write_lock:
            if now - self._last_heartbeat_write >= JOB_HEARTBEAT_INTERVAL:
                self._last_heartbeat_write = now
                should_write = True
        if should_write:
            self.update(lastActivityAt=utc_now())


def preprocess_argv(argv: list[str] | None) -> list[str]:
    if not argv:
        return ["review"]
    if argv[0] in SUBCOMMANDS or argv[0] in {"-h", "--help"}:
        return argv
    return ["review", *argv]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    if argv is None:
        argv = sys.argv[1:]
    argv = preprocess_argv(argv)

    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--agent-command",
        default=DEFAULT_AGENT_COMMAND,
        help=(
            "Command used to launch the ACP adapter. Defaults to "
            "`claude-agent-acp` or $TO_CLAUDE_REVIEW_AGENT_COMMAND."
        ),
    )
    common.add_argument(
        "--verbose-updates",
        action="store_true",
        help="Print non-text session updates and permission decisions to stderr.",
    )

    jobs_parser = subparsers.add_parser("jobs")
    jobs_parser.add_argument(
        "--state",
        action="append",
        default=[],
        metavar="STATE",
        help="Repeatable detached job state filter, for example `running` or `failed`.",
    )
    jobs_parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Maximum number of detached jobs to print.",
    )
    jobs_parser.add_argument(
        "--output-format",
        choices=["text", "json"],
        default="text",
        help="How to print detached job summaries.",
    )

    status_parser = subparsers.add_parser("job-status")
    status_parser.add_argument(
        "job_ref",
        help="Detached job id, `latest`, or a detached job directory path.",
    )
    status_parser.add_argument(
        "--output-format",
        choices=["text", "json"],
        default="text",
        help="How to print detached job status.",
    )

    wait_parser = subparsers.add_parser("job-wait")
    wait_parser.add_argument(
        "job_ref",
        help="Detached job id, `latest`, or a detached job directory path.",
    )
    wait_parser.add_argument(
        "--timeout",
        type=float,
        default=0.0,
        help="Optional maximum seconds to wait. Default 0 waits until the job finishes.",
    )
    wait_parser.add_argument(
        "--poll-interval",
        type=float,
        default=JOB_WAIT_POLL_INTERVAL,
        help="Seconds between status refreshes while waiting.",
    )
    wait_parser.add_argument(
        "--output-format",
        choices=["text", "json"],
        default="text",
        help="How to print the final detached job status.",
    )

    cancel_parser = subparsers.add_parser("job-cancel")
    cancel_parser.add_argument(
        "job_ref",
        help="Detached job id, `latest`, or a detached job directory path.",
    )
    cancel_parser.add_argument(
        "--signal",
        choices=["TERM", "INT", "KILL"],
        default="TERM",
        help="Signal used to cancel the detached worker process group.",
    )
    cancel_parser.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="Seconds to wait for a terminal state after sending the cancel signal.",
    )
    cancel_parser.add_argument(
        "--poll-interval",
        type=float,
        default=JOB_WAIT_POLL_INTERVAL,
        help="Seconds between status refreshes while waiting after cancel.",
    )
    cancel_parser.add_argument(
        "--no-wait",
        action="store_true",
        help="Return immediately after sending the cancel signal.",
    )
    cancel_parser.add_argument(
        "--output-format",
        choices=["text", "json"],
        default="text",
        help="How to print detached job status after cancellation.",
    )

    review_parser = subparsers.add_parser("review", parents=[common])
    review_parser.add_argument(
        "--cwd",
        default=os.getcwd(),
        help="Review working directory. Defaults to the current working directory.",
    )
    review_parser.add_argument(
        "--brief",
        help="Short review brief, for example the risk or question Claude should focus on.",
    )
    review_parser.add_argument(
        "--brief-file",
        help="Read the review brief from a file.",
    )
    review_parser.add_argument(
        "--focus",
        action="append",
        default=[],
        metavar="AREA",
        help="Repeatable review focus, for example `regression-risk` or `missing-tests`.",
    )
    review_parser.add_argument(
        "--path",
        action="append",
        default=[],
        metavar="PATH",
        help="Repeatable file or directory to call out in the review scope.",
    )
    review_parser.add_argument(
        "--working-tree",
        action="store_true",
        help="Ask Claude to inspect the current uncommitted working tree in the review cwd.",
    )
    review_parser.add_argument(
        "--permission-strategy",
        choices=[
            "accept-edits",
            "allow",
            "allow-always",
            "ask",
            "auto",
            "bypass-permissions",
            "cancel",
            "default",
            "plan",
            "reject",
        ],
        default="plan",
        help="How to answer Claude permission requests. `plan` keeps the default review path read-mostly.",
    )
    review_parser.add_argument(
        "--output-format",
        choices=["text", "json", "stream-json"],
        default="text",
        help="How to print the review result and session updates.",
    )
    review_parser.add_argument(
        "--detach",
        action="store_true",
        help="Run the review in a background worker and return job metadata immediately.",
    )
    review_parser.add_argument(
        "--image-file",
        action="append",
        default=[],
        help="Repeatable image file to include in the review context.",
    )

    return parser.parse_args(argv)


def resolve_agent_command(raw_command: str) -> list[str]:
    parts = shlex.split(raw_command.strip())
    if not parts:
        raise SystemExit("agent command is empty")
    return parts


def resolve_review_brief(args: argparse.Namespace) -> str:
    if args.brief and args.brief_file:
        raise SystemExit("use only one of --brief or --brief-file")
    if args.brief:
        return args.brief.strip()
    if args.brief_file:
        return Path(args.brief_file).expanduser().read_text(encoding="utf-8").strip()
    if not sys.stdin.isatty():
        return sys.stdin.read().strip()
    return ""


def resolve_review_paths(args: argparse.Namespace, *, cwd: str) -> list[Path]:
    resolved: list[Path] = []
    seen: set[str] = set()
    cwd_path = Path(cwd)
    for raw_path in args.path:
        candidate = Path(raw_path).expanduser()
        path = candidate.resolve() if candidate.is_absolute() else (cwd_path / candidate).resolve()
        if not path.exists():
            raise SystemExit(f"review path does not exist: {raw_path}")
        key = str(path)
        if key not in seen:
            seen.add(key)
            resolved.append(path)
    return resolved


def build_review_prompt_text(
    args: argparse.Namespace,
    *,
    cwd: str,
    brief: str,
    review_paths: list[Path],
) -> str:
    focus_items = [item.strip() for item in args.focus if item.strip()]
    if not focus_items:
        focus_items = ["correctness", "regression risk", "missing tests", "open questions"]

    scope_lines = [f"- review cwd: {cwd}"]
    if args.working_tree:
        scope_lines.append("- inspect the current uncommitted working tree")
    if review_paths:
        scope_lines.append("- prioritize these explicit paths:")
        for path in review_paths:
            scope_lines.append(f"  - {path}")
    if args.image_file:
        scope_lines.append("- include the attached images as supporting evidence")

    request = brief
    if not request:
        if args.working_tree:
            request = "Review the current working tree and call out the most important correctness and regression risks."
        elif review_paths:
            request = "Review the provided targets and return a findings-first second opinion."
        else:
            request = "Review the provided context and return a concise findings-first second opinion."

    focus_lines = "\n".join(f"- {item}" for item in focus_items)
    scope_text = "\n".join(scope_lines)
    return (
        "You are acting as a read-only second-opinion reviewer for Codex.\n"
        "Stay in review-only mode:\n"
        "- Do not claim to edit files, apply patches, or take implementation ownership.\n"
        "- Prefer concrete findings over broad rewrites.\n"
        "- If evidence is weak or missing, say so explicitly.\n"
        "- Keep remediation guidance concise and subordinate to the findings.\n\n"
        "Return findings first using this exact section order:\n"
        "1. Findings\n"
        "2. Risks / Missing Tests\n"
        "3. Open Questions\n"
        "4. Recommendation\n\n"
        f"Review scope:\n{scope_text}\n\n"
        f"Focus areas:\n{focus_lines}\n\n"
        f"Review brief:\n- {request}\n"
    )


def resolve_prompt_blocks(args: argparse.Namespace) -> list[dict[str, Any]]:
    cwd = str(Path(args.cwd).expanduser().resolve())
    brief = resolve_review_brief(args)
    review_paths = resolve_review_paths(args, cwd=cwd)
    blocks: list[dict[str, Any]] = []
    if brief or review_paths or args.working_tree or args.image_file:
        blocks.append(
            {
                "type": "text",
                "text": build_review_prompt_text(
                    args,
                    cwd=cwd,
                    brief=brief,
                    review_paths=review_paths,
                ),
            }
        )

    for path in review_paths:
        if path.is_file():
            blocks.append(
                {
                    "type": "resource_link",
                    "name": path.name,
                    "uri": path.as_uri(),
                }
            )

    for raw_path in args.image_file:
        blocks.append(image_block(Path(raw_path).expanduser().resolve()))

    if not blocks:
        raise SystemExit(
            "provide --brief, --brief-file, --path, --working-tree, --image-file, "
            "or pipe a review brief on stdin"
        )
    return blocks


def image_block(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise SystemExit(f"image file does not exist: {path}")

    mime_type, _ = mimetypes.guess_type(path.name)
    if not mime_type:
        raise SystemExit(f"unable to guess image mime type for {path}")

    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return {
        "type": "image",
        "mimeType": mime_type,
        "data": data,
        "uri": path.as_uri(),
    }


def pick_permission_option(
    options: list[dict[str, Any]],
    strategy: str,
    *,
    interactive: bool,
) -> str | None:
    if strategy == "cancel":
        return None
    if strategy == "ask":
        if not interactive:
            return None
        return ask_permission_option(options)

    preferred_ids = PERMISSION_ORDER.get(strategy, [])
    option_by_id = {str(option.get("optionId")): option for option in options}
    for option_id in preferred_ids:
        if option_id in option_by_id:
            return option_id

    preferred_kinds = PERMISSION_KIND_FALLBACKS.get(strategy, [])
    for preferred_kind in preferred_kinds:
        for option in options:
            if option.get("kind") == preferred_kind:
                return str(option.get("optionId"))

    return None


def ask_permission_option(options: list[dict[str, Any]]) -> str | None:
    tty = Path("/dev/tty")
    try:
        with tty.open("r+", encoding="utf-8") as handle:
            handle.write("\nPermission requested:\n")
            for index, option in enumerate(options, start=1):
                handle.write(
                    f"  {index}. {option.get('name', option.get('optionId'))} "
                    f"({option.get('optionId')})\n"
                )
            handle.write("Choose an option number, or press Enter to cancel: ")
            handle.flush()
            answer = handle.readline().strip()
    except OSError:
        return None

    if not answer:
        return None
    try:
        index = int(answer) - 1
    except ValueError:
        return None
    if 0 <= index < len(options):
        return str(options[index].get("optionId"))
    return None


class AcpConnection:
    def __init__(
        self,
        *,
        command: list[str],
        output_format: str,
        permission_strategy: str,
        verbose_updates: bool,
        activity_callback: Any | None = None,
    ) -> None:
        self.command = command
        self.output_format = output_format
        self.permission_strategy = permission_strategy
        self.verbose_updates = verbose_updates
        self.activity_callback = activity_callback
        self.proc = subprocess.Popen(
            self.command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=None,
            text=True,
            bufsize=1,
        )
        if self.proc.stdin is None or self.proc.stdout is None:
            raise SystemExit("failed to open stdio pipes to the ACP agent")

        self._stdin = self.proc.stdin
        self._stdout = self.proc.stdout
        self._write_lock = threading.Lock()
        self._activity_lock = threading.Lock()
        self._pending: dict[int, queue.Queue[Any]] = {}
        self._next_id = 1
        self._closed = False
        self._printed_text = False
        self._last_text_had_newline = True
        self._last_activity_at = time.monotonic()
        self.events: list[dict[str, Any]] = []
        self.session_updates: list[dict[str, Any]] = []
        self._reader = threading.Thread(target=self._reader_loop, daemon=True)
        self._reader.start()

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            self._stdin.close()
        except OSError:
            pass
        if self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait(timeout=5)

    def initialize(self) -> dict[str, Any]:
        params: dict[str, Any] = {
            "protocolVersion": PROTOCOL_VERSION,
            "clientCapabilities": DEFAULT_CLIENT_CAPABILITIES,
            "clientInfo": {
                "name": "to-claude-review",
                "title": "To-Claude-Review Bridge",
                "version": "1",
            },
        }
        result = self.request("initialize", params)
        self.emit_event("initialize", result)
        return result

    def request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        if self._closed:
            raise RpcError("ACP connection is closed")

        request_id = self._next_id
        self._next_id += 1
        response_queue: queue.Queue[Any] = queue.Queue(maxsize=1)
        self._pending[request_id] = response_queue
        self._send_json(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": method,
                "params": params,
            }
        )
        response = self._wait_for_response(response_queue, request_id=request_id, method=method)
        if isinstance(response, Exception):
            raise response
        if "error" in response:
            error = response["error"]
            message = error.get("message", "ACP request failed")
            method_label = {
                "initialize": "adapter initialization",
                "session/new": "review session startup",
                "session/prompt": "review request",
            }.get(method, method)
            raise RpcError(f"{method_label} failed: {message}")
        return response.get("result", {})

    def emit_event(self, event: str, payload: dict[str, Any]) -> None:
        record = {
            "event": event,
            "payload": payload,
        }
        self.events.append(record)
        if self.output_format == "stream-json":
            print(json.dumps(record, ensure_ascii=False), flush=True)

    def _reader_loop(self) -> None:
        try:
            for raw_line in self._stdout:
                line = raw_line.strip()
                if not line:
                    continue
                self._record_activity()
                try:
                    message = json.loads(line)
                except json.JSONDecodeError as exc:
                    self._fail_pending(RpcError(f"invalid JSON from ACP agent: {exc}"))
                    return
                self._dispatch_message(message)
        finally:
            if not self._closed:
                self._fail_pending(
                    RpcError(
                        f"ACP agent exited unexpectedly with code {self.proc.poll()}"
                    )
                )

    def _dispatch_message(self, message: dict[str, Any]) -> None:
        if "method" in message and "id" in message:
            self._handle_agent_request(message)
            return
        if "method" in message:
            self._handle_agent_notification(message)
            return
        if "id" in message:
            response_queue = self._pending.pop(int(message["id"]), None)
            if response_queue is not None:
                response_queue.put(message)

    def _handle_agent_request(self, message: dict[str, Any]) -> None:
        method = str(message.get("method"))
        params = message.get("params", {})
        request_id = int(message["id"])

        if method == "session/request_permission":
            result = self._handle_permission_request(params)
            self._send_json(
                {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": result,
                }
            )
            return

        self._send_json(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32601,
                    "message": f"unsupported client method: {method}",
                },
            }
        )

    def _handle_permission_request(self, params: dict[str, Any]) -> dict[str, Any]:
        options = params.get("options", [])
        selected = pick_permission_option(
            list(options),
            self.permission_strategy,
            interactive=sys.stdin.isatty(),
        )

        payload = {
            "strategy": self.permission_strategy,
            "request": params,
            "selected": selected,
        }
        self.emit_event("permission_request", payload)

        if self.verbose_updates:
            tool_call = params.get("toolCall", {})
            title = tool_call.get("title") or tool_call.get("toolCallId") or "permission-request"
            target = selected or "cancelled"
            print(
                f"[permission] {title} -> {target}",
                file=sys.stderr,
            )

        if selected is None:
            return {
                "outcome": {
                    "outcome": "cancelled",
                }
            }
        return {
            "outcome": {
                "outcome": "selected",
                "optionId": selected,
            }
        }

    def _handle_agent_notification(self, message: dict[str, Any]) -> None:
        method = str(message.get("method"))
        params = message.get("params", {})

        if method == "session/update":
            self.session_updates.append(params)
            self.emit_event("session_update", params)
            self._render_session_update(params)
            return

        self.emit_event("notification", {"method": method, "params": params})
        if self.verbose_updates:
            print(f"[notification] {method}", file=sys.stderr)

    def _wait_for_response(
        self,
        response_queue: queue.Queue[Any],
        *,
        request_id: int,
        method: str,
    ) -> Any:
        started_at = time.monotonic()
        while True:
            try:
                return response_queue.get(timeout=RESPONSE_POLL_INTERVAL)
            except queue.Empty:
                now = time.monotonic()
                idle_for = now - self._last_activity_snapshot()
                total_for = now - started_at
                if REQUEST_MAX_TIMEOUT > 0 and total_for >= REQUEST_MAX_TIMEOUT:
                    self._pending.pop(request_id, None)
                    raise RpcError(
                        f"{method} timed out after {REQUEST_MAX_TIMEOUT:.1f}s waiting for a response"
                    )
                if idle_for >= REQUEST_IDLE_TIMEOUT:
                    self._pending.pop(request_id, None)
                    raise RpcError(
                        f"{method} timed out after {idle_for:.1f}s without agent activity"
                    )

    def _record_activity(self) -> None:
        with self._activity_lock:
            self._last_activity_at = time.monotonic()
        if self.activity_callback is not None:
            try:
                self.activity_callback()
            except Exception:
                pass

    def _last_activity_snapshot(self) -> float:
        with self._activity_lock:
            return self._last_activity_at

    def _render_session_update(self, params: dict[str, Any]) -> None:
        if self.output_format != "text":
            return

        update = params.get("update", {})
        update_kind = update.get("sessionUpdate")

        if update_kind == "agent_message_chunk":
            content = update.get("content", {})
            if content.get("type") == "text":
                text = content.get("text", "")
                if text:
                    sys.stdout.write(text)
                    sys.stdout.flush()
                    self._printed_text = True
                    self._last_text_had_newline = text.endswith("\n")
                return

        if not self.verbose_updates:
            return

        summary = json.dumps(update, ensure_ascii=False)
        print(f"[{update_kind}] {summary}", file=sys.stderr)

    def finish_text_output(self) -> None:
        if self.output_format == "text" and self._printed_text and not self._last_text_had_newline:
            print()

    def _send_json(self, payload: dict[str, Any]) -> None:
        serialized = json.dumps(payload, ensure_ascii=False)
        with self._write_lock:
            self._stdin.write(serialized + "\n")
            self._stdin.flush()

    def _fail_pending(self, exc: Exception) -> None:
        pending = list(self._pending.values())
        self._pending.clear()
        for response_queue in pending:
            response_queue.put(exc)


def print_json(value: Any) -> None:
    print(json.dumps(value, indent=2, ensure_ascii=False))


def has_prompt_source(args: argparse.Namespace) -> bool:
    return bool(
        args.brief
        or args.brief_file
        or args.path
        or args.working_tree
        or args.image_file
    )


def default_job_root() -> Path:
    return Path(env_value(JOB_ROOT_ENV, DEFAULT_JOB_ROOT)).expanduser()


def ensure_job_root() -> Path:
    job_root = default_job_root()
    job_root.mkdir(parents=True, exist_ok=True)
    return job_root


def make_job_id() -> str:
    prefix = time.strftime("%Y%m%d-%H%M%S", time.gmtime())
    suffix = uuid.uuid4().hex[:8]
    return f"{prefix}-{suffix}"


def build_job_paths(job_dir: Path) -> dict[str, Any]:
    job_dir = job_dir.expanduser().resolve()
    return {
        "jobId": job_dir.name,
        "jobDir": job_dir,
        "statusFile": job_dir / "status.json",
        "stdoutFile": job_dir / "stdout.log",
        "stderrFile": job_dir / "stderr.log",
        "cancelFile": job_dir / "cancel.json",
    }


def create_detached_job_paths() -> dict[str, Any]:
    job_root = ensure_job_root()
    for _ in range(32):
        job_dir = job_root / make_job_id()
        try:
            job_dir.mkdir(parents=False, exist_ok=False)
        except FileExistsError:
            continue
        return build_job_paths(job_dir)
    raise SystemExit("failed to allocate a detached Claude job directory")


def normalize_job_payload(paths: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(payload)
    normalized.setdefault("jobId", paths["jobId"])
    normalized.setdefault("jobDir", str(paths["jobDir"]))
    normalized.setdefault("statusFile", str(paths["statusFile"]))
    normalized.setdefault("stdoutFile", str(paths["stdoutFile"]))
    normalized.setdefault("stderrFile", str(paths["stderrFile"]))
    normalized.setdefault("cancelFile", str(paths["cancelFile"]))
    return normalized


def write_job_payload(paths: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    normalized = normalize_job_payload(paths, payload)
    write_json_atomically(paths["statusFile"], normalized)
    return normalized


def job_state(payload: dict[str, Any]) -> str:
    return str(payload.get("state") or "")


def has_live_job_status(job_status: JobStatusWriter | None) -> bool:
    return job_status is not None and job_status.status_file is not None


def can_update_job_status(job_status: JobStatusWriter | None) -> bool:
    return has_live_job_status(job_status) and job_status.payload.get("state") not in TERMINAL_JOB_STATES


def record_job_failure(job_status: JobStatusWriter | None, *, error: str, returncode: int) -> None:
    if not can_update_job_status(job_status):
        return
    job_status.update(state="failed", phase="finished", error=error, returncode=returncode)


def process_exists(raw_pid: Any) -> bool:
    try:
        pid = int(raw_pid)
    except (TypeError, ValueError):
        return False
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def read_job_payload(paths: dict[str, Any]) -> dict[str, Any]:
    status_file = paths["statusFile"]
    if not status_file.is_file():
        raise SystemExit(f"detached job status file does not exist: {status_file}")
    try:
        loaded = json.loads(status_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"invalid detached job status JSON: {status_file}: {exc}") from exc
    if not isinstance(loaded, dict):
        raise SystemExit(f"detached job status payload must be a JSON object: {status_file}")
    payload = normalize_job_payload(paths, loaded)
    state = job_state(payload)
    if state in TERMINAL_JOB_STATES:
        return payload

    changed = False
    timestamp = utc_now()
    cancel_request: dict[str, Any] = {}
    if paths["cancelFile"].is_file():
        try:
            loaded_cancel = json.loads(paths["cancelFile"].read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            loaded_cancel = {}
        if isinstance(loaded_cancel, dict):
            cancel_request = loaded_cancel
    if cancel_request:
        if cancel_request.get("requestedAt"):
            payload.setdefault("cancelRequestedAt", cancel_request.get("requestedAt"))
        if cancel_request.get("signal"):
            payload.setdefault("cancelSignal", cancel_request.get("signal"))
    cancel_requested = bool(payload.get("cancelRequestedAt")) or bool(cancel_request)
    if cancel_requested and state not in {"cancelling", "cancelled"}:
        payload["state"] = "cancelling"
        payload.setdefault("phase", "cancelling")
        changed = True

    pid = payload.get("pid")
    if pid is not None and not process_exists(pid):
        if cancel_requested:
            cancel_signal_name = str(payload.get("cancelSignal") or "SIGTERM")
            try:
                cancel_signal_value = int(getattr(signal, cancel_signal_name))
            except AttributeError:
                cancel_signal_name = "SIGTERM"
                cancel_signal_value = int(signal.SIGTERM)
            payload["state"] = "cancelled"
            payload.setdefault("cancelSignal", cancel_signal_name)
            payload.setdefault("error", "worker stopped after cancellation request")
            payload.setdefault("returncode", 128 + cancel_signal_value)
        else:
            payload["state"] = "failed"
            payload.setdefault(
                "error",
                "worker process is no longer running and did not report a terminal state",
            )
            payload.setdefault("returncode", 1)
        payload["phase"] = "finished"
        payload.setdefault("finishedAt", timestamp)
        changed = True

    if changed:
        payload["updatedAt"] = timestamp
        return write_job_payload(paths, payload)
    return payload


def list_job_payloads() -> list[dict[str, Any]]:
    job_root = default_job_root()
    jobs: list[dict[str, Any]] = []
    if not job_root.is_dir():
        return jobs
    for child in job_root.iterdir():
        if not child.is_dir():
            continue
        paths = build_job_paths(child)
        if not paths["statusFile"].is_file():
            continue
        try:
            jobs.append(read_job_payload(paths))
        except SystemExit:
            continue
    jobs.sort(
        key=lambda item: (
            str(item.get("updatedAt") or ""),
            str(item.get("createdAt") or ""),
            str(item.get("jobId") or ""),
        ),
        reverse=True,
    )
    return jobs


def resolve_job_ref(job_ref: str) -> dict[str, Any]:
    ref = job_ref.strip()
    if not ref:
        raise SystemExit("job reference is empty")

    if ref == "latest":
        jobs = list_job_payloads()
        if not jobs:
            raise SystemExit(
                f"no detached Claude review jobs found under {default_job_root()}"
            )
        return build_job_paths(Path(str(jobs[0]["jobDir"])))

    ref_path = Path(ref).expanduser()
    if ref_path.exists():
        return build_job_paths(ref_path if ref_path.is_dir() else ref_path.parent)

    if "/" in ref or ref.startswith(".") or ref.startswith("~"):
        return build_job_paths(ref_path)

    return build_job_paths(default_job_root() / ref)


def build_detached_argv(args: argparse.Namespace, *, job_dir: Path) -> list[str]:
    raw_argv = list(getattr(args, "raw_argv", []))
    if not raw_argv:
        raise SystemExit("missing raw argv for detach mode")

    child_argv = [part for part in raw_argv if part != "--detach"]
    if not sys.stdin.isatty() and not has_prompt_source(args):
        prompt_path = job_dir / "stdin-prompt.txt"
        prompt_path.write_text(sys.stdin.read(), encoding="utf-8")
        child_argv.extend(["--brief-file", str(prompt_path)])
    return child_argv


def spawn_detached_run(args: argparse.Namespace) -> int:
    paths = create_detached_job_paths()
    job_dir = paths["jobDir"]
    status_file = paths["statusFile"]
    stdout_file = paths["stdoutFile"]
    stderr_file = paths["stderrFile"]
    cancel_file = paths["cancelFile"]
    child_argv = build_detached_argv(args, job_dir=job_dir)
    env = os.environ.copy()
    for key, value in [
        (JOB_ID_ENV, str(paths["jobId"])),
        (JOB_DIR_ENV, str(job_dir)),
        (JOB_STATUS_FILE_ENV, str(status_file)),
        (JOB_STDOUT_FILE_ENV, str(stdout_file)),
        (JOB_STDERR_FILE_ENV, str(stderr_file)),
        (JOB_CANCEL_FILE_ENV, str(cancel_file)),
    ]:
        env[key] = value

    queued_at = utc_now()
    payload = write_job_payload(
        paths,
        {
            "jobId": paths["jobId"],
            "command": "review",
            "state": "queued",
            "phase": "queued",
            "cwd": str(Path(args.cwd).expanduser().resolve()),
            "createdAt": queued_at,
            "updatedAt": queued_at,
        },
    )

    with stdout_file.open("w", encoding="utf-8") as stdout_handle, stderr_file.open(
        "w", encoding="utf-8"
    ) as stderr_handle:
        proc = subprocess.Popen(
            [sys.executable, str(Path(__file__).resolve()), *child_argv],
            stdin=subprocess.DEVNULL,
            stdout=stdout_handle,
            stderr=stderr_handle,
            cwd=os.getcwd(),
            env=env,
            start_new_session=True,
            text=True,
        )

    started_at = utc_now()
    payload.update(
        {
            "state": "running",
            "phase": "booting",
            "pid": proc.pid,
            "updatedAt": started_at,
            "startedAt": started_at,
        }
    )
    payload = write_job_payload(paths, payload)

    if args.output_format in {"json", "stream-json"}:
        print_json(payload)
        return 0

    print(f"Claude review job {paths['jobId']}")
    print(f"  state      {payload.get('state')}")
    print(f"  pid        {proc.pid}")
    print(f"  status     {status_file}")
    print(f"  stdout     {stdout_file}")
    print(f"  stderr     {stderr_file}")
    return 0


def print_text_job_status(payload: dict[str, Any]) -> None:
    print(f"Claude review job {payload.get('jobId')}")
    rows = [
        ("state", payload.get("state")),
        ("phase", payload.get("phase")),
        ("pid", payload.get("pid")),
        ("session", payload.get("sessionId")),
        ("cwd", payload.get("cwd")),
        ("created", payload.get("createdAt")),
        ("updated", payload.get("updatedAt")),
        ("active", payload.get("lastActivityAt")),
        ("finished", payload.get("finishedAt")),
        ("reason", payload.get("stopReason")),
        ("cancelled", payload.get("cancelRequestedAt")),
        ("signal", payload.get("cancelSignal")),
        ("code", payload.get("returncode")),
        ("status", payload.get("statusFile")),
        ("stdout", payload.get("stdoutFile")),
        ("stderr", payload.get("stderrFile")),
        ("cancel", payload.get("cancelFile")),
        ("error", payload.get("error")),
    ]
    for label, value in rows:
        if value not in {"", None}:
            print(f"  {label:<11}{value}")


def print_text_job_list(payloads: list[dict[str, Any]]) -> None:
    print(f"Claude review jobs {len(payloads)}")
    print(f"  root       {default_job_root()}")
    if not payloads:
        return
    print(f"{'JOB ID':<25}{'STATE':<12}{'UPDATED':<22}{'SESSION':<26}")
    for payload in payloads:
        print(
            f"{str(payload.get('jobId') or '-'):<25}"
            f"{str(payload.get('state') or '-'):12}"
            f"{str(payload.get('updatedAt') or '-'):22}"
            f"{str(payload.get('sessionId') or '-'):26}"
        )


def job_terminal_exit_code(payload: dict[str, Any]) -> int:
    raw_code = payload.get("returncode")
    try:
        code = int(raw_code) if raw_code is not None else None
    except (TypeError, ValueError):
        code = None

    state = job_state(payload)
    if state == "completed":
        return 0 if code is None else code
    if state == "cancelled":
        return 130 if code is None else code
    if state == "failed":
        return 1 if code is None else code
    return 1


def wait_for_job(paths: dict[str, Any], *, timeout: float, poll_interval: float) -> tuple[dict[str, Any], bool]:
    started_at = time.monotonic()
    interval = max(0.1, poll_interval)
    while True:
        payload = read_job_payload(paths)
        if job_state(payload) in TERMINAL_JOB_STATES:
            return payload, False
        if timeout > 0 and time.monotonic() - started_at >= timeout:
            return payload, True
        time.sleep(interval)


def print_job_payload(payload: dict[str, Any], *, output_format: str) -> None:
    if output_format == "json":
        print_json(payload)
        return
    print_text_job_status(payload)


def run_jobs(args: argparse.Namespace) -> int:
    payloads = list_job_payloads()
    filters = {state.strip() for state in args.state if state.strip()}
    if filters:
        payloads = [payload for payload in payloads if job_state(payload) in filters]
    if args.limit > 0:
        payloads = payloads[: args.limit]

    if args.output_format == "json":
        print_json({"jobRoot": str(default_job_root()), "jobs": payloads})
        return 0

    print_text_job_list(payloads)
    return 0


def run_job_status(args: argparse.Namespace) -> int:
    paths = resolve_job_ref(args.job_ref)
    payload = read_job_payload(paths)
    print_job_payload(payload, output_format=args.output_format)
    return 0


def run_job_wait(args: argparse.Namespace) -> int:
    paths = resolve_job_ref(args.job_ref)
    payload, timed_out = wait_for_job(
        paths,
        timeout=max(0.0, args.timeout),
        poll_interval=max(0.1, args.poll_interval),
    )
    print_job_payload(payload, output_format=args.output_format)
    if timed_out:
        return 1
    return job_terminal_exit_code(payload)


def run_job_cancel(args: argparse.Namespace) -> int:
    paths = resolve_job_ref(args.job_ref)
    payload = read_job_payload(paths)
    if job_state(payload) in TERMINAL_JOB_STATES:
        print_job_payload(payload, output_format=args.output_format)
        return 0

    signal_name = f"SIG{args.signal}"
    signal_value = int(getattr(signal, signal_name))
    requested_at = utc_now()
    write_json_atomically(
        paths["cancelFile"],
        {
            "requestedAt": requested_at,
            "signal": signal_name,
        },
    )
    payload.update(
        {
            "state": "cancelling",
            "phase": "cancelling",
            "cancelRequestedAt": requested_at,
            "cancelSignal": signal_name,
        }
    )
    payload = write_job_payload(paths, payload)

    pid = payload.get("pid")
    if pid is not None and process_exists(pid):
        try:
            os.killpg(int(pid), signal_value)
        except (ProcessLookupError, PermissionError):
            try:
                os.kill(int(pid), signal_value)
            except ProcessLookupError:
                pass
    else:
        payload.update(
            {
                "state": "cancelled",
                "phase": "finished",
                "returncode": 128 + signal_value,
                "finishedAt": requested_at,
            }
        )
        payload = write_job_payload(paths, payload)

    if args.no_wait:
        payload = read_job_payload(paths)
        print_job_payload(payload, output_format=args.output_format)
        return 0

    payload, timed_out = wait_for_job(
        paths,
        timeout=max(0.0, args.timeout),
        poll_interval=max(0.1, args.poll_interval),
    )
    print_job_payload(payload, output_format=args.output_format)
    if timed_out:
        return 1
    if job_state(payload) in {"cancelled", "completed"}:
        return 0
    return job_terminal_exit_code(payload)


def install_job_signal_handlers(job_status: JobStatusWriter | None) -> None:
    if not has_live_job_status(job_status):
        return

    def handler(signum: int, _frame: Any) -> None:
        signal_name = signal.Signals(signum).name
        job_status.update(
            state="cancelled",
            phase="finished",
            error=f"terminated by {signal_name}",
            returncode=128 + signum,
            finishedAt=utc_now(),
        )
        raise SystemExit(128 + signum)

    signal.signal(signal.SIGTERM, handler)
    signal.signal(signal.SIGINT, handler)


def initialize_connection(
    args: argparse.Namespace,
    *,
    output_format: str,
    permission_strategy: str,
    job_status: JobStatusWriter | None = None,
) -> tuple[AcpConnection, dict[str, Any]]:
    connection = AcpConnection(
        command=resolve_agent_command(args.agent_command),
        output_format=output_format,
        permission_strategy=permission_strategy,
        verbose_updates=args.verbose_updates,
        activity_callback=job_status.heartbeat if job_status is not None else None,
    )
    initialize_result = connection.initialize()
    return connection, initialize_result


def run_prompt(args: argparse.Namespace, *, job_status: JobStatusWriter | None = None) -> int:
    if args.detach:
        return spawn_detached_run(args)

    cwd = str(Path(args.cwd).expanduser().resolve())
    if job_status is not None:
        job_status.update(state="running", phase="initializing", cwd=cwd)
    prompt_blocks = resolve_prompt_blocks(args)

    connection, initialize_result = initialize_connection(
        args,
        output_format=args.output_format,
        permission_strategy=args.permission_strategy,
        job_status=job_status,
    )
    try:
        if job_status is not None:
            job_status.update(state="running", phase="session", cwd=cwd)
        session_result = connection.request(
            "session/new",
            {
                "cwd": cwd,
                "mcpServers": [],
            },
        )
        session_id = session_result.get("sessionId")
        if not session_id:
            raise SystemExit("session/new did not yield a session id")
        if job_status is not None:
            job_status.update(state="running", phase="prompting", sessionId=session_id)
        connection.emit_event(
            "session",
            {
                "method": "session/new",
                "sessionId": session_id,
                "result": session_result,
            },
        )

        prompt_result = connection.request(
            "session/prompt",
            {
                "sessionId": session_id,
                "prompt": prompt_blocks,
            },
        )
        connection.emit_event(
            "prompt_result",
            {
                "sessionId": session_id,
                "result": prompt_result,
            },
        )

        connection.finish_text_output()
        if job_status is not None:
            job_status.update(
                state="completed",
                phase="completed",
                sessionId=session_id,
                stopReason=prompt_result.get("stopReason"),
                returncode=0,
            )
        if args.output_format == "json":
            print_json(
                {
                    "initialize": initialize_result,
                    "session": {
                        "method": "session/new",
                        "sessionId": session_id,
                        "result": session_result,
                    },
                    "prompt": prompt_result,
                    "sessionUpdateCount": len(connection.session_updates),
                }
            )
        return 0
    finally:
        connection.close()


def main(argv: list[str] | None = None) -> int:
    raw_argv = list(argv if argv is not None else sys.argv[1:])
    args = parse_args(raw_argv)
    args.raw_argv = preprocess_argv(raw_argv)
    job_status = JobStatusWriter(command=args.command) if args.command == "review" else None
    live_job_status = job_status if has_live_job_status(job_status) else None
    install_job_signal_handlers(live_job_status)
    if live_job_status is not None:
        live_job_status.update(state="starting", phase="booting")
    try:
        if args.command == "jobs":
            return run_jobs(args)
        if args.command == "job-status":
            return run_job_status(args)
        if args.command == "job-wait":
            return run_job_wait(args)
        if args.command == "job-cancel":
            return run_job_cancel(args)
        return run_prompt(
            args,
            job_status=live_job_status,
        )
    except RpcError as exc:
        record_job_failure(job_status, error=str(exc), returncode=1)
        raise SystemExit(str(exc)) from exc
    except SystemExit as exc:
        if exc.code not in {None, 0}:
            error_text = str(exc)
            if not error_text or error_text == "1":
                error_text = "command exited with a non-zero status"
            try:
                returncode = int(exc.code)
            except (TypeError, ValueError):
                returncode = 1
            record_job_failure(job_status, error=error_text, returncode=returncode)
        raise
    except Exception as exc:
        record_job_failure(job_status, error=str(exc), returncode=1)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
