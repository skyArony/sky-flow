#!/usr/bin/env python3
"""Manage Sky Flow skill installation, updates, and readiness.

Agent note:
- Keep this script deterministic. It expects explicit command verbs plus exact
  local skill names.
- If a user asks in natural language or by group, resolve that in the agent
  layer before calling this script.
- Sky Flow is a nested suite in-repo, but Claude does not discover nested
  skills. This manager therefore links the suite entry skill and each callable
  child skill separately into the target runtime directories.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
REPO_ROOT = Path(__file__).resolve().parents[1]
CLAUDE_SKILLS_DIR = Path.home() / ".claude" / "skills"
AGENTS_SKILLS_DIR = Path.home() / ".agents" / "skills"
TARGET_ORDER = ["claude", "codex"]
DEFAULT_INSTALL_TARGETS = list(TARGET_ORDER)
TARGET_ALIASES = {
    "claude": "claude",
    "claude-code": "claude",
    "codex": "codex",
    "agents": "codex",
    "agent": "codex",
}
TARGET_DIRS = {
    "claude": CLAUDE_SKILLS_DIR,
    "codex": AGENTS_SKILLS_DIR,
}
TARGET_LABELS = {
    "claude": "Claude",
    "codex": "Codex",
}

PACKAGE_MAP = {
    "brew": {
        "python3": "python",
        "git": "git",
        "npm": "node",
        "npx": "node",
    },
    "apt-get": {
        "python3": "python3",
        "git": "git",
        "npm": "nodejs",
        "npx": "nodejs",
    },
    "apt": {
        "python3": "python3",
        "git": "git",
        "npm": "nodejs",
        "npx": "nodejs",
    },
}

COMMAND_INSTALLERS = {
    "claude-agent-acp": {
        "helper_commands": ["npm"],
        "package_label": "@agentclientprotocol/claude-agent-acp",
        "install_command": ["npm", "install", "-g", "@agentclientprotocol/claude-agent-acp"],
        "reason": "install via npm global package",
    }
}

ANSI_CODES = {
    "bold": "1",
    "dim": "2",
    "red": "31",
    "green": "32",
    "yellow": "33",
    "blue": "34",
    "cyan": "36",
    "magenta": "35",
}

STATUS_LABELS = {
    "ready": "READY",
    "ok": "OK",
    "linked": "LINKED",
    "copied": "COPIED",
    "partial": "PARTIAL",
    "missing": "MISSING",
    "broken": "BROKEN",
    "failed": "FAILED",
    "blocked": "BLOCKED",
    "dry-run": "DRY-RUN",
    "would-link": "DRY-RUN",
    "would-copy": "DRY-RUN",
    "skipped-existing": "SKIP",
    "needs-attention": "NOT READY",
}

STATUS_TONES = {
    "ready": ("green", "bold"),
    "ok": ("green", "bold"),
    "linked": ("green", "bold"),
    "copied": ("green", "bold"),
    "partial": ("yellow", "bold"),
    "missing": ("yellow", "bold"),
    "broken": ("red", "bold"),
    "failed": ("red", "bold"),
    "blocked": ("yellow", "bold"),
    "dry-run": ("blue", "bold"),
    "would-link": ("blue", "bold"),
    "would-copy": ("blue", "bold"),
    "skipped-existing": ("dim",),
    "needs-attention": ("yellow", "bold"),
}

ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*m")
PLACEHOLDER_RE = re.compile(r"{([A-Za-z0-9_]+)}")
FIELD_LABEL_WIDTH = 10


@dataclass(frozen=True)
class SkillMeta:
    name: str
    path: Path
    skill_doc: Path
    relative_dir: Path
    install_targets: list[str]
    commands: list[str]
    python_packages: list[str]
    required_skills: list[str]
    guidance: dict[str, object]
    is_suite_entry: bool


def supports_color() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("FORCE_COLOR"):
        return True
    term = os.environ.get("TERM", "")
    return sys.stdout.isatty() and term.lower() != "dumb"


def style(text: object, *tokens: str) -> str:
    rendered = str(text)
    if not tokens or not supports_color():
        return rendered
    codes = [ANSI_CODES[token] for token in tokens if token in ANSI_CODES]
    if not codes:
        return rendered
    return f"\033[{';'.join(codes)}m{rendered}\033[0m"


def status_badge(status: str) -> str:
    label = STATUS_LABELS.get(status, status.replace("-", " ").upper())
    tones = STATUS_TONES.get(status, ("cyan", "bold"))
    return style(f"[{label}]", *tones)


def status_word(status: str) -> str:
    label = STATUS_LABELS.get(status, status.replace("-", " ").upper())
    tones = STATUS_TONES.get(status, ("cyan", "bold"))
    return style(label, *tones)


def print_heading(title: str, status: str | None = None, subtitle: str | None = None) -> None:
    parts = [style(title, "bold", "cyan")]
    if subtitle:
        parts.append(style(subtitle, "dim"))
    if status:
        parts.append(status_badge(status))
    print(" ".join(parts))


def print_subheading(title: str) -> None:
    print(style(title, "bold"))


def print_field(label: str, value: object, indent: int = 2) -> None:
    prefix = " " * indent
    print(f"{prefix}{style(label.ljust(FIELD_LABEL_WIDTH), 'dim')}{value}")


def print_status_line(name: str, status: str, detail: str = "", indent: int = 2) -> None:
    prefix = " " * indent
    line = f"{prefix}{status_badge(status)} {style(name, 'bold')}"
    if detail:
        line += f" {style(detail, 'dim')}"
    print(line)


def visible_width(text: object) -> int:
    return len(ANSI_ESCAPE_RE.sub("", str(text)))


def pad_visible(text: object, width: int) -> str:
    rendered = str(text)
    padding = max(0, width - visible_width(rendered))
    return f"{rendered}{' ' * padding}"


def print_table(headers: list[str], rows: list[list[str]], indent: int = 2) -> None:
    widths = [visible_width(header) for header in headers]
    for row in rows:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], visible_width(cell))

    prefix = " " * indent
    header_line = "  ".join(
        pad_visible(style(header, "bold"), widths[index]) for index, header in enumerate(headers)
    )
    divider = "  ".join("-" * width for width in widths)
    print(f"{prefix}{header_line}")
    print(f"{prefix}{divider}")
    for row in rows:
        print(f"{prefix}{'  '.join(pad_visible(cell, widths[index]) for index, cell in enumerate(row))}")


def compact_text(text: str, max_len: int = 180) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= max_len:
        return normalized
    return f"{normalized[: max_len - 3]}..."


def display_path(value: object) -> str:
    text = str(value)
    home = str(Path.home())
    if text.startswith(home):
        return f"~{text[len(home):]}"
    return text


def format_items(items: list[str]) -> str:
    if not items:
        return style("-", "dim")
    return ", ".join(items)


def format_skill_selection(items: list[str], max_inline: int = 6) -> str:
    if len(items) <= max_inline:
        return format_items(items)
    return f"{len(items)} skills"


def count_phrase(count: int, noun: str) -> str:
    return f"{count} {noun}" if count == 1 else f"{count} {noun}s"


def format_command(cmd: list[str]) -> str:
    return " ".join(shlex.quote(part) for part in cmd)


def print_dry_run(command: str) -> None:
    print(f"{status_badge('dry-run')} {command}")


def summary_status(ok: bool) -> str:
    return "ready" if ok else "needs-attention"


def unique_items(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if not item or item in seen:
            continue
        seen.add(item)
        ordered.append(item)
    return ordered


INSTALL_REPAIR_STEP_RE = re.compile(r"^Run `\./install\.sh(?: [^`]+)?` to install or repair local links\.$")


def strip_scalar(value: str) -> str:
    value = value.strip()
    if value.startswith(("'", '"', "`")) and value.endswith(("'", '"', "`")):
        return value[1:-1]
    return value


def parse_inline_list(value: str) -> list[str]:
    value = value.strip()
    if not (value.startswith("[") and value.endswith("]")):
        return []
    inner = value[1:-1].strip()
    if not inner:
        return []
    return [strip_scalar(part) for part in inner.split(",") if part.strip()]


def extract_frontmatter(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    return match.group(1) if match else ""


def extract_frontmatter_section(frontmatter: str, section_name: str) -> list[str]:
    lines = frontmatter.splitlines()
    section_indent: int | None = None
    capture = False
    collected: list[str] = []

    for raw in lines:
        if not capture:
            if re.match(rf"^{re.escape(section_name)}:\s*$", raw):
                capture = True
                section_indent = len(raw) - len(raw.lstrip(" "))
            continue

        if section_indent is None:
            break

        stripped = raw.strip()
        if stripped and not stripped.startswith("#"):
            indent = len(raw) - len(raw.lstrip(" "))
            if indent <= section_indent:
                break
        trim = section_indent + 2
        collected.append(raw[trim:] if len(raw) >= trim else "")

    return collected


def parse_frontmatter_scalar(value: str) -> object:
    value = value.strip()
    if not value:
        return ""
    if value.startswith("[") and value.endswith("]"):
        return parse_inline_list(value)
    return strip_scalar(value)


def parse_frontmatter_section_block(lines: list[str]) -> object:
    tokens: list[tuple[int, str]] = []
    for raw in lines:
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        tokens.append((indent, stripped))

    if not tokens:
        return {}

    def parse_block(index: int, expected_indent: int) -> tuple[object, int]:
        if index >= len(tokens):
            return {}, index

        indent, text = tokens[index]
        if indent < expected_indent:
            return {}, index

        if text.startswith("- "):
            items: list[object] = []
            while index < len(tokens):
                current_indent, current_text = tokens[index]
                if current_indent < expected_indent:
                    break
                if current_indent != expected_indent or not current_text.startswith("- "):
                    break
                item_value = current_text[2:].strip()
                index += 1
                if item_value:
                    items.append(parse_frontmatter_scalar(item_value))
                else:
                    child, index = parse_block(index, expected_indent + 2)
                    items.append(child)
            return items, index

        mapping: dict[str, object] = {}
        while index < len(tokens):
            current_indent, current_text = tokens[index]
            if current_indent < expected_indent:
                break
            if current_indent != expected_indent or current_text.startswith("- "):
                break
            key, _, raw_value = current_text.partition(":")
            index += 1
            key = key.strip()
            value = raw_value.strip()
            if value:
                mapping[key] = parse_frontmatter_scalar(value)
            else:
                child, index = parse_block(index, expected_indent + 2)
                mapping[key] = child
        return mapping, index

    parsed, _ = parse_block(0, tokens[0][0])
    return parsed


def frontmatter_value(frontmatter: str, key: str) -> object:
    lines = frontmatter.splitlines()
    for index, raw in enumerate(lines):
        match = re.match(rf"^{re.escape(key)}:\s*(.*)$", raw)
        if not match:
            continue

        value = match.group(1).strip()
        if value:
            return parse_frontmatter_scalar(value)

        base_indent = len(raw) - len(raw.lstrip(" "))
        block: list[str] = []
        for next_raw in lines[index + 1 :]:
            stripped = next_raw.strip()
            if stripped and not stripped.startswith("#"):
                indent = len(next_raw) - len(next_raw.lstrip(" "))
                if indent <= base_indent:
                    break
            trim = base_indent + 2
            block.append(next_raw[trim:] if len(next_raw) >= trim else "")
        return parse_frontmatter_section_block(block)
    return ""


def frontmatter_line_value(frontmatter: str, key: str) -> str:
    match = re.search(rf"^{re.escape(key)}:\s*(.+)$", frontmatter, re.M)
    if not match:
        return ""
    return strip_scalar(match.group(1))


def parse_required(frontmatter: str) -> dict[str, object]:
    result: dict[str, object] = {
        "skills": [],
        "commands": [],
        "python_packages": [],
    }
    lines = frontmatter.splitlines()
    in_required = False
    current_key: str | None = None
    for raw in lines:
        if not in_required:
            if raw.startswith("required:"):
                in_required = True
            continue
        if raw and not raw.startswith(" "):
            break
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("- ") and current_key:
            current = result.setdefault(current_key, [])
            if isinstance(current, list):
                current.append(strip_scalar(stripped[2:]))
            continue
        if ":" in stripped:
            key, value = stripped.split(":", 1)
            key = key.strip()
            value = value.strip()
            if value.startswith("[") and value.endswith("]"):
                result[key] = parse_inline_list(value)
                current_key = None
            elif value:
                result[key] = strip_scalar(value)
                current_key = None
            else:
                result.setdefault(key, [])
                current_key = key
    return result


def parse_guidance(frontmatter: str) -> dict[str, object]:
    block = extract_frontmatter_section(frontmatter, "guidance")
    parsed = parse_frontmatter_section_block(block)
    return parsed if isinstance(parsed, dict) else {}


def string_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def string_dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def normalize_install_targets(raw: object, skill_name: str) -> list[str]:
    if raw is None or raw == "" or raw == []:
        return list(DEFAULT_INSTALL_TARGETS)

    if isinstance(raw, str):
        requested = [raw]
    elif isinstance(raw, list):
        requested = [str(item) for item in raw if str(item).strip()]
    else:
        raise SystemExit(f"invalid install_targets for {skill_name}: expected a string or list")

    normalized: list[str] = []
    invalid: list[str] = []
    for item in requested:
        key = TARGET_ALIASES.get(item.strip().lower(), "")
        if not key:
            invalid.append(item)
            continue
        if key not in normalized:
            normalized.append(key)

    if invalid:
        valid = ", ".join(sorted(TARGET_ORDER))
        raise SystemExit(
            f"invalid install_targets for {skill_name}: {', '.join(invalid)}; valid values: {valid}"
        )

    return normalized or list(DEFAULT_INSTALL_TARGETS)


def render_template(text: str, context: dict[str, object]) -> str:
    def replace(match: re.Match[str]) -> str:
        return str(context.get(match.group(1), match.group(0)))

    return PLACEHOLDER_RE.sub(replace, text)


def render_templates(templates: object, context: dict[str, object]) -> list[str]:
    return [render_template(item, context) for item in string_list(templates)]


def readiness_guidance(skill: SkillMeta) -> dict[str, object]:
    return string_dict(skill.guidance.get("readiness"))


def guidance_steps_for_key(skill: SkillMeta, key: str, extra: dict[str, object] | None = None) -> list[str]:
    context = {"skill": skill.name}
    if extra:
        context.update(extra)
    return render_templates(readiness_guidance(skill).get(key), context)


def discover_skills() -> dict[str, SkillMeta]:
    registry: dict[str, SkillMeta] = {}
    candidates: list[Path] = []
    root_skill = REPO_ROOT / "SKILL.md"
    if root_skill.is_file():
        candidates.append(root_skill)
    skills_dir = REPO_ROOT / "skills"
    if skills_dir.is_dir():
        candidates.extend(sorted(path for path in skills_dir.rglob("SKILL.md") if ".git" not in path.parts))

    for skill_doc in candidates:
        relative_doc = skill_doc.relative_to(REPO_ROOT)
        if any(part.startswith(".") for part in relative_doc.parts):
            continue
        frontmatter = extract_frontmatter(skill_doc)
        if not frontmatter:
            continue
        required = parse_required(frontmatter)
        guidance = parse_guidance(frontmatter)
        name = frontmatter_line_value(frontmatter, "name") or skill_doc.parent.name
        install_targets = normalize_install_targets(frontmatter_value(frontmatter, "install_targets"), name)
        path = skill_doc.parent
        meta = SkillMeta(
            name=name,
            path=path,
            skill_doc=skill_doc,
            relative_dir=path.relative_to(REPO_ROOT),
            install_targets=install_targets,
            commands=string_list(required.get("commands")),
            python_packages=string_list(required.get("python_packages")),
            required_skills=string_list(required.get("skills")),
            guidance=guidance,
            is_suite_entry=skill_doc == root_skill,
        )
        if name in registry:
            raise SystemExit(f"duplicate skill name discovered: {name}")
        registry[name] = meta
    return registry


def suite_entry_name(registry: dict[str, SkillMeta]) -> str:
    for skill in registry.values():
        if skill.is_suite_entry:
            return skill.name
    raise SystemExit("suite entry SKILL.md was not found at repository root")


def resolve_skills(registry: dict[str, SkillMeta], names: list[str]) -> list[SkillMeta]:
    requested = list(names) if names else sorted(registry)
    suite_entry = suite_entry_name(registry)
    if suite_entry in requested:
        requested = sorted({*requested, *registry.keys()})
    visiting: set[str] = set()
    visited: set[str] = set()
    ordered: list[str] = []

    def visit(name: str) -> None:
        if name in visited:
            return
        if name in visiting:
            raise SystemExit(f"circular skill dependency detected at {name}")
        if name not in registry:
            raise SystemExit(f"unknown skill: {name}")
        visiting.add(name)
        for dep in registry[name].required_skills:
            visit(dep)
        visiting.remove(name)
        visited.add(name)
        ordered.append(name)

    for name in requested:
        visit(name)
    return [registry[name] for name in ordered]


def detect_package_manager() -> str | None:
    if shutil.which("brew"):
        return "brew"
    if shutil.which("apt-get"):
        return "apt-get"
    if shutil.which("apt"):
        return "apt"
    return None


def run(cmd: list[str], dry_run: bool = False, cwd: Path | None = None) -> int:
    if dry_run:
        print_dry_run(format_command(cmd))
        return 0
    return subprocess.run(cmd, cwd=cwd, check=False).returncode


def install_command_dependencies(commands: list[str], dry_run: bool) -> dict[str, object]:
    missing = sorted({cmd for cmd in commands if shutil.which(cmd) is None})
    if not missing:
        return {"missing": [], "installed": [], "unresolved": [], "custom_installs": []}

    manager = detect_package_manager()
    unresolved: set[str] = set()
    package_labels: set[str] = set()
    custom_installs: list[dict[str, object]] = []

    custom_commands = [command for command in missing if command in COMMAND_INSTALLERS]
    generic_commands = [command for command in missing if command not in COMMAND_INSTALLERS]
    helper_commands = sorted(
        {
            helper
            for command in custom_commands
            for helper in string_list(COMMAND_INSTALLERS[command].get("helper_commands"))
            if helper and shutil.which(helper) is None
        }
    )

    manager_targets = sorted({*generic_commands, *helper_commands})
    manager_ready = {command for command in manager_targets if shutil.which(command)}
    manager_failures: set[str] = set()

    if manager_targets:
        if not manager:
            unresolved.update(generic_commands)
        else:
            packages: set[str] = set()
            manager_map = PACKAGE_MAP.get(manager, {})
            for command in manager_targets:
                package = manager_map.get(command)
                if package:
                    packages.add(package)
                elif command in generic_commands:
                    unresolved.add(command)
                else:
                    manager_failures.add(command)

            if packages:
                package_labels.update(packages)
                package_list = sorted(packages)
                if manager == "brew":
                    install_rc = run(["brew", "install", *package_list], dry_run=dry_run)
                else:
                    install_rc = run(["sudo", manager, "install", "-y", *package_list], dry_run=dry_run)
                if install_rc != 0 and not dry_run:
                    manager_failures.update(manager_targets)

            if dry_run:
                manager_ready.update(command for command in manager_targets if command not in manager_failures)
            else:
                manager_ready.update(command for command in manager_targets if shutil.which(command))

    for command in generic_commands:
        if command not in manager_ready:
            unresolved.add(command)

    for command in custom_commands:
        installer = COMMAND_INSTALLERS[command]
        helper_list = string_list(installer.get("helper_commands"))
        missing_helpers = [helper for helper in helper_list if helper not in manager_ready and shutil.which(helper) is None]
        install_command = [str(part) for part in installer.get("install_command", []) if str(part)]
        display = format_command(install_command) if install_command else ""

        if missing_helpers or not install_command:
            custom_installs.append(
                {
                    "command": command,
                    "status": "blocked",
                    "package": str(installer.get("package_label", "")),
                    "reason": (
                        f"missing helper commands: {', '.join(missing_helpers)}"
                        if missing_helpers
                        else "no install command is registered"
                    ),
                    "install_command_display": display,
                }
            )
            unresolved.add(command)
            continue

        if dry_run:
            print_dry_run(display)
            custom_installs.append(
                {
                    "command": command,
                    "status": "dry-run",
                    "package": str(installer.get("package_label", "")),
                    "reason": str(installer.get("reason", "")),
                    "install_command_display": display,
                }
            )
            continue

        install_rc = run(install_command, dry_run=False)
        available = shutil.which(command) is not None
        status = "ok" if install_rc == 0 and available else "failed"
        reason = str(installer.get("reason", ""))
        if install_rc == 0 and not available:
            reason = "installer ran but the command is still not on PATH"
        custom_installs.append(
            {
                "command": command,
                "status": status,
                "package": str(installer.get("package_label", "")),
                "reason": reason,
                "install_command_display": display,
            }
        )
        if status != "ok":
            unresolved.add(command)

    return {
        "missing": missing,
        "installed": sorted(package_labels),
        "unresolved": sorted(unresolved),
        "custom_installs": custom_installs,
    }


def install_python_packages(packages: list[str], dry_run: bool) -> list[str]:
    unique = sorted({pkg for pkg in packages if pkg})
    if unique:
        run(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--user",
                "--quiet",
                "--disable-pip-version-check",
                *unique,
            ],
            dry_run=dry_run,
        )
    return unique


def remove_path(path: Path, dry_run: bool) -> None:
    if dry_run:
        print_dry_run(f"rm -rf {display_path(path)}")
        return
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)


def link_or_copy_skill(src: Path, dest: Path, copy_mode: bool, force: bool, dry_run: bool) -> str:
    if copy_mode:
        if dest.exists() or dest.is_symlink():
            if not force:
                return "skipped-existing"
            remove_path(dest, dry_run=dry_run)
        if dry_run:
            print_dry_run(f"cp -R {display_path(src)} {display_path(dest)}")
            return "would-copy"
        shutil.copytree(src, dest, symlinks=False)
        return "copied"

    if dest.is_symlink():
        try:
            if dest.resolve() == src.resolve():
                return "would-link" if dry_run else "linked"
        except OSError:
            pass
        remove_path(dest, dry_run=dry_run)
    elif dest.exists():
        if not force:
            return "skipped-existing"
        remove_path(dest, dry_run=dry_run)

    if dry_run:
        print_dry_run(f"ln -s {display_path(src)} {display_path(dest)}")
        return "would-link"
    dest.symlink_to(src, target_is_directory=True)
    return "linked"


def install_target_dirs(skill: SkillMeta) -> list[Path]:
    return [TARGET_DIRS[name] for name in skill.install_targets]


def install_skills(skills: list[SkillMeta], copy_mode: bool, force: bool, dry_run: bool) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    targets: list[Path] = []
    for skill in skills:
        for target_dir in install_target_dirs(skill):
            if target_dir not in targets:
                targets.append(target_dir)

    for target_dir in targets:
        if dry_run:
            print_dry_run(f"mkdir -p {display_path(target_dir)}")
        else:
            target_dir.mkdir(parents=True, exist_ok=True)
        for skill in skills:
            if target_dir not in install_target_dirs(skill):
                continue
            dest = target_dir / skill.name
            status = link_or_copy_skill(skill.path, dest, copy_mode=copy_mode, force=force, dry_run=dry_run)
            result.setdefault(skill.name, {})[str(target_dir)] = status
    return result


def command_dependencies_for_install(skills: list[SkillMeta]) -> tuple[list[str], list[str]]:
    commands = sorted({cmd for skill in skills for cmd in skill.commands})
    python_packages = sorted({pkg for skill in skills for pkg in skill.python_packages})
    return commands, python_packages


def inspect_install_state(skill: SkillMeta) -> dict[str, object]:
    targets: dict[str, str] = {}
    for logical_target in skill.install_targets:
        target_dir = TARGET_DIRS[logical_target]
        dest = target_dir / skill.name
        if not dest.exists() and not dest.is_symlink():
            targets[logical_target] = "missing"
            continue
        if dest.is_symlink():
            try:
                targets[logical_target] = "linked" if dest.resolve() == skill.path.resolve() else "broken"
            except OSError:
                targets[logical_target] = "broken"
            continue
        if dest.is_dir() and (dest / "SKILL.md").is_file():
            targets[logical_target] = "copied"
            continue
        targets[logical_target] = "broken"

    values = list(targets.values())
    if values and all(value in {"linked", "copied"} for value in values):
        status = "ready"
    elif any(value == "broken" for value in values):
        status = "broken"
    elif any(value in {"linked", "copied"} for value in values):
        status = "partial"
    else:
        status = "missing"
    return {"status": status, "targets": targets}


def render_install_targets(target_statuses: dict[str, str]) -> str:
    if not target_statuses:
        return style("-", "dim")
    parts = []
    for logical_target in TARGET_ORDER:
        if logical_target not in target_statuses:
            continue
        detail = "via ~/.claude/skills" if logical_target == "claude" else "via ~/.agents/skills"
        parts.append(f"{TARGET_LABELS[logical_target]} {status_badge(target_statuses[logical_target])} {style(detail, 'dim')}")
    return "  ".join(parts)


def build_install_payload(
    skills: list[SkillMeta],
    *,
    copy_mode: bool,
    force: bool,
    dry_run: bool,
    no_deps: bool,
) -> dict[str, object]:
    all_commands, all_python_packages = command_dependencies_for_install(skills)
    missing_commands = sorted({cmd for cmd in all_commands if shutil.which(cmd) is None})
    dep_result = {
        "missing": missing_commands,
        "installed": [],
        "unresolved": [],
        "skipped": missing_commands if no_deps else [],
        "custom_installs": [],
    }
    if not no_deps:
        dep_result = install_command_dependencies(all_commands, dry_run=dry_run)
        dep_result.setdefault("skipped", [])
        install_python_packages(all_python_packages, dry_run=dry_run)

    install_result = install_skills(skills, copy_mode=copy_mode, force=force, dry_run=dry_run)
    ready = not dep_result["unresolved"] and all(
        status in {"linked", "copied", "would-link", "would-copy"}
        for skill_targets in install_result.values()
        for status in skill_targets.values()
    )
    return {
        "skills": [skill.name for skill in skills],
        "command_dependencies": dep_result,
        "python_packages": all_python_packages,
        "install": install_result,
        "dry_run": dry_run,
        "ready": ready,
        "ok": ready,
    }


def print_next_steps(steps: list[str]) -> None:
    deduped = unique_items([step for step in steps if step])
    if not deduped:
        return
    print()
    print_subheading("Next steps")
    for step in deduped:
        print(f"  - {compact_text(step, max_len=240)}")


def render_install_result_cell(status_map: dict[str, str]) -> str:
    reverse_map = {str(path): logical for logical, path in TARGET_DIRS.items()}
    if not status_map:
        return style("-", "dim")
    parts = []
    for path_str, status in status_map.items():
        logical = reverse_map.get(path_str, path_str)
        label = TARGET_LABELS.get(logical, path_str)
        parts.append(f"{label} {status_badge(status)}")
    return "  ".join(parts)


def print_install_payload(payload: dict[str, object], action_label: str) -> None:
    heading_status = (
        "dry-run"
        if payload.get("dry_run")
        else summary_status(bool(payload.get("ready", payload.get("ok", True))))
    )
    selected_skills = [str(name) for name in payload.get("skills", []) or []]
    print_heading(action_label, status=heading_status)
    print_field("skills", format_skill_selection(selected_skills))
    print_field("targets", "Claude -> ~/.claude/skills | Codex -> ~/.agents/skills")

    dep_result = payload.get("command_dependencies", {})
    if isinstance(dep_result, dict):
        missing = [str(item) for item in dep_result.get("missing", [])]
        unresolved = [str(item) for item in dep_result.get("unresolved", [])]
        skipped = [str(item) for item in dep_result.get("skipped", [])]
        custom_installs = dep_result.get("custom_installs", [])
        print()
        print_subheading("Runtime")
        if unresolved:
            print_field("commands", style(f"missing: {', '.join(unresolved)}", "yellow"))
        elif skipped:
            print_field("commands", style(f"skipped: {', '.join(skipped)}", "yellow"))
        elif missing:
            print_field("commands", f"handled: {', '.join(missing)}")
        else:
            print_field("commands", style("ready", "green"))
        print_field("python", format_items([str(item) for item in payload.get("python_packages", []) or []]))
        if isinstance(custom_installs, list) and custom_installs:
            for item in custom_installs:
                if not isinstance(item, dict):
                    continue
                print_status_line(
                    str(item.get("command", "command")),
                    str(item.get("status", "unknown")),
                    detail=", ".join(
                        part
                        for part in [
                            str(item.get("package", "")).strip(),
                            str(item.get("reason", "")).strip(),
                        ]
                        if part
                    ),
                    indent=4,
                )

    install_result = payload.get("install", {})
    if isinstance(install_result, dict):
        print()
        print_subheading("Links")
        for skill_name in payload.get("skills", []) or []:
            skill_targets = install_result.get(str(skill_name), {})
            if isinstance(skill_targets, dict):
                print(f"  {style(str(skill_name), 'bold')}  {render_install_result_cell(skill_targets)}")

    steps: list[str] = []
    unresolved = []
    if isinstance(dep_result, dict):
        unresolved = [str(item) for item in dep_result.get("unresolved", [])]
    if unresolved:
        selected = " ".join(selected_skills) if len(selected_skills) <= 3 else ""
        if selected:
            steps.append(f"Run `./install.sh doctor {selected}` after fixing missing commands: {', '.join(unresolved)}.")
        else:
            steps.append(f"Run `./install.sh doctor` after fixing missing commands: {', '.join(unresolved)}.")
    if payload.get("dry_run"):
        selected = " ".join(selected_skills) if len(selected_skills) <= 3 else ""
        rerun = f"./install.sh {selected}".strip()
        steps.insert(0, f"Run `{rerun}` without `--dry-run` to apply the install.")
    print_next_steps(steps)


def summarize_skill_statuses(skills: list[SkillMeta], registry: dict[str, SkillMeta]) -> list[dict[str, object]]:
    cache: dict[str, dict[str, object]] = {}

    def evaluate(skill: SkillMeta) -> dict[str, object]:
        if skill.name in cache:
            return cache[skill.name]

        install_state = inspect_install_state(skill)
        missing_commands = sorted(cmd for cmd in skill.commands if shutil.which(cmd) is None)
        dependency_states = [evaluate(registry[name]) for name in skill.required_skills]
        blocked_by = [str(dep["name"]) for dep in dependency_states if not dep.get("ready")]

        notes: list[str] = []
        if install_state["status"] != "ready":
            notes.append(
                "install: " + ", ".join(f"{target}={status}" for target, status in install_state["targets"].items())
            )
        if missing_commands:
            notes.append(f"commands: {', '.join(missing_commands)}")
        if blocked_by:
            notes.append(f"depends on: {', '.join(blocked_by)}")

        steps: list[str] = []
        if install_state["status"] != "ready":
            steps.append(f"Run `./install.sh {skill.name}` to install or repair local links.")
        if missing_commands:
            guided = guidance_steps_for_key(
                skill,
                "missing_required_commands",
                extra={"missing_required_commands_csv": ", ".join(missing_commands)},
            )
            if guided:
                steps.extend(guided)
            else:
                steps.append(
                    f"Install the missing commands for `{skill.name}`: {', '.join(missing_commands)}."
                )
        if blocked_by:
            steps.append(f"Fix these required skills first: {', '.join(blocked_by)}.")

        ready = install_state["status"] == "ready" and not missing_commands and not blocked_by
        row = {
            "name": skill.name,
            "install_state": install_state,
            "missing_commands": missing_commands,
            "blocked_by": blocked_by,
            "ready": ready,
            "notes": notes,
            "next_steps": unique_items(steps),
        }
        cache[skill.name] = row
        return row

    return [evaluate(skill) for skill in skills]


def build_list_payload(skills: list[SkillMeta]) -> list[dict[str, object]]:
    return [
        {
            "name": skill.name,
            "path": str(skill.path),
            "skill_doc": str(skill.skill_doc),
            "install_targets": skill.install_targets,
            "required_skills": skill.required_skills,
            "commands": skill.commands,
            "python_packages": skill.python_packages,
            "is_suite_entry": skill.is_suite_entry,
            "guidance": skill.guidance,
        }
        for skill in skills
    ]


def cmd_list(args: argparse.Namespace, registry: dict[str, SkillMeta]) -> int:
    skills = resolve_skills(registry, args.skills)
    if args.json:
        print(json.dumps(build_list_payload(skills), indent=2))
        return 0

    print_heading("Skills", subtitle=count_phrase(len(skills), "skill"))
    print_field("targets", "Claude -> ~/.claude/skills | Codex -> ~/.agents/skills")
    print()
    rows: list[list[str]] = []
    for skill in skills:
        role = "suite" if skill.is_suite_entry else display_path(skill.relative_dir)
        runtime = []
        if skill.commands:
            runtime.append(f"cmd {', '.join(skill.commands)}")
        if skill.python_packages:
            runtime.append(f"py {', '.join(skill.python_packages)}")
        if not runtime:
            runtime.append("-")
        rows.append(
            [
                style(skill.name, "bold"),
                role,
                format_items(skill.install_targets),
                format_items(skill.required_skills),
                " | ".join(runtime),
            ]
        )
    print_table(["Skill", "Path", "Install", "Requires", "Runtime"], rows)
    return 0


def cmd_install(args: argparse.Namespace, registry: dict[str, SkillMeta]) -> int:
    skills = resolve_skills(registry, args.skills)
    payload = build_install_payload(
        skills,
        copy_mode=args.copy,
        force=args.force,
        dry_run=args.dry_run,
        no_deps=args.no_deps,
    )
    if args.json:
        print(json.dumps(payload, indent=2))
        return 0 if payload.get("ok", True) else 1
    print_install_payload(payload, action_label="Install")
    return 0 if payload.get("ok", True) else 1


def cmd_update(args: argparse.Namespace, registry: dict[str, SkillMeta]) -> int:
    rc = run(["git", "pull", "--ff-only"], dry_run=args.dry_run, cwd=REPO_ROOT)
    if rc != 0:
        return rc
    refreshed = discover_skills()
    skills = resolve_skills(refreshed, args.skills)
    payload = build_install_payload(
        skills,
        copy_mode=args.copy,
        force=args.force,
        dry_run=args.dry_run,
        no_deps=args.no_deps,
    )
    if args.json:
        print(json.dumps(payload, indent=2))
        return 0 if payload.get("ok", True) else 1
    print_install_payload(payload, action_label="Update")
    return 0 if payload.get("ok", True) else 1


def cmd_doctor(args: argparse.Namespace, registry: dict[str, SkillMeta]) -> int:
    skills = resolve_skills(registry, args.skills)
    rows = summarize_skill_statuses(skills, registry)
    ok = all(bool(row.get("ready")) for row in rows)

    payload = {
        "skills": [skill.name for skill in skills],
        "readiness": rows,
        "ok": ok,
    }
    if args.json:
        print(json.dumps(payload, indent=2))
        return 0 if ok else 1

    print_heading("Doctor", status=summary_status(ok))
    print_field("skills", format_skill_selection([str(skill) for skill in payload["skills"]]))
    print_field("targets", "Claude -> ~/.claude/skills | Codex -> ~/.agents/skills")
    print()
    table_rows: list[list[str]] = []
    for row in rows:
        table_rows.append(
            [
                style(str(row["name"]), "bold"),
                render_install_targets(dict(row["install_state"]["targets"])),
                status_word("missing" if row["missing_commands"] else "ready"),
                status_word("blocked" if row["blocked_by"] else "ready"),
                status_word("ready" if row["ready"] else "needs-attention"),
            ]
        )
    print_table(["Skill", "Installed", "Commands", "Deps", "Ready"], table_rows)

    notes = [row for row in rows if row["notes"]]
    if notes:
        print()
        print_subheading("Needs attention")
        for row in notes:
            print(f"  - {row['name']}: {compact_text('; '.join(str(note) for note in row['notes']), max_len=220)}")

    steps = [str(step) for row in rows for step in row["next_steps"]]
    if len(skills) > 5:
        install_steps = [step for step in steps if INSTALL_REPAIR_STEP_RE.match(step)]
        other_steps = [step for step in steps if step not in install_steps]
        if install_steps:
            steps = ["Run `./install.sh` to install or repair the suite links.", *other_steps]
    print_next_steps(steps)
    return 0 if ok else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
        metavar="{list,install,update,doctor}",
    )

    def add_common_install_flags(p: argparse.ArgumentParser) -> None:
        p.add_argument("skills", nargs="*", help="Skill names to operate on. Defaults to all.")
        p.add_argument("--dry-run", action="store_true")
        p.add_argument("--force", action="store_true", help="Replace existing non-symlink installs.")
        p.add_argument("--copy", action="store_true", help="Copy instead of symlink.")
        p.add_argument("--no-deps", action="store_true", help="Skip command/package install.")
        p.add_argument("--json", action="store_true")

    list_parser = subparsers.add_parser("list")
    list_parser.add_argument("skills", nargs="*", help="Skill names to list. Defaults to all.")
    list_parser.add_argument("--json", action="store_true")

    install_parser = subparsers.add_parser("install")
    add_common_install_flags(install_parser)

    update_parser = subparsers.add_parser("update")
    add_common_install_flags(update_parser)

    doctor_parser = subparsers.add_parser("doctor")
    doctor_parser.add_argument("skills", nargs="*", help="Skill names to inspect. Defaults to all.")
    doctor_parser.add_argument("--json", action="store_true")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv if argv is not None else sys.argv[1:]))
    registry = discover_skills()

    if args.command == "list":
        return cmd_list(args, registry)
    if args.command == "install":
        return cmd_install(args, registry)
    if args.command == "update":
        return cmd_update(args, registry)
    if args.command == "doctor":
        return cmd_doctor(args, registry)
    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
