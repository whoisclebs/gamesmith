#!/usr/bin/env sh
# Copy gamesmith skills into Claude Code and Codex skill folders.
# Usage: scripts/install.sh [--project DIR]   (default: user-level ~/.claude/skills and ~/.agents/skills)
set -eu
src="$(cd "$(dirname "$0")/.." && pwd)/skills"
base="$HOME"
if [ "${1:-}" = "--project" ]; then base="${2:?usage: --project DIR}"; fi
for dest in "$base/.claude/skills" "$base/.agents/skills"; do
  mkdir -p "$dest"
  for skill in "$src"/*/; do
    name="$(basename "$skill")"
    rm -rf "${dest:?}/$name"
    cp -R "$skill" "$dest/$name"
  done
  echo "Installed $(ls "$src" | wc -l | tr -d ' ') skills into $dest"
done
echo "Restart Claude Code / Codex to load them."
