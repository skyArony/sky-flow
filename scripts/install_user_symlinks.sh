#!/usr/bin/env bash
set -euo pipefail

# Link this Sky Flow checkout into common user-level skill locations.
# The canonical source remains this repository checkout.
SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILL_NAME="sky-flow"

if [ ! -f "$SOURCE_DIR/SKILL.md" ]; then
  echo "SKILL.md not found under $SOURCE_DIR"
  exit 1
fi

mkdir -p "$HOME/.agents/skills"
mkdir -p "$HOME/.claude/skills"
mkdir -p "$HOME/.codex/skills"

link_path() {
  local link_path="$1"
  local target="$2"

  if [ -L "$link_path" ]; then
    local current
    current="$(readlink "$link_path")"
    if [ "$current" = "$target" ]; then
      echo "ok: $link_path -> $target"
      return
    fi
    rm "$link_path"
  elif [ -e "$link_path" ]; then
    echo "refusing to replace non-symlink path: $link_path"
    exit 1
  fi

  ln -s "$target" "$link_path"
  echo "linked: $link_path -> $target"
}

if [[ "$SOURCE_DIR" == "$HOME/"* ]]; then
  AGENTS_TARGET="../../${SOURCE_DIR#"$HOME/"}"
else
  AGENTS_TARGET="$SOURCE_DIR"
fi

link_path "$HOME/.agents/skills/$SKILL_NAME" "$AGENTS_TARGET"
link_path "$HOME/.claude/skills/$SKILL_NAME" "../../.agents/skills/$SKILL_NAME"
link_path "$HOME/.codex/skills/$SKILL_NAME" "../../.agents/skills/$SKILL_NAME"

echo "Sky Flow user-level skill links are ready."
