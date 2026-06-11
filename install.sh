#!/bin/zsh

set -euo pipefail

SCRIPT_DIR="${0:A:h}"
ACTION="install"

usage() {
  cat <<'EOF'
Install the full suite:
  ./install.sh
  ./install.sh --dry-run
  ./install.sh update

Install a specific skill scope:
  ./install.sh to-claude-review
  ./install.sh update to-claude-review

Inspect what is available or ready:
  ./install.sh list
  ./install.sh doctor
  ./install.sh doctor to-claude-review

Command forms:
  ./install.sh [install] [skill-name ...] [--dry-run] [--force] [--copy] [--no-deps]
  ./install.sh update [skill-name ...] [--dry-run] [--force] [--copy] [--no-deps]
  ./install.sh doctor [skill-name ...] [--json]
  ./install.sh list [skill-name ...] [--json]

What happens:
  - Default action is `install`, so `./install.sh` installs the full Sky Flow suite.
  - Claude installs live under ~/.claude/skills.
  - Codex installs live under ~/.agents/skills, so a separate ~/.codex/skills layer is not needed.
  - The manager links the suite entry skill and each callable child skill separately because Claude does not discover nested skills.
  - Nested skill `install_targets` are respected, so Codex-only skills such as `to-claude-review` stay out of Claude installs.
  - `install` and `update` auto-install supported runtime commands when possible.
  - `doctor` checks local links plus per-skill runtime readiness.
EOF
}

if [[ $# -gt 0 ]]; then
  case "$1" in
    install|update|doctor|list)
      ACTION="$1"
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    -*)
      ;;
    *)
      ;;
  esac
fi

exec python3 "${SCRIPT_DIR}/scripts/skill_manager.py" "${ACTION}" "$@"
