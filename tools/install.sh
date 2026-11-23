#!/usr/bin/env bash
# Install X-Android-Skills into an agent's skill directory.
#
#   ./tools/install.sh                      # -> ~/.agents/skills (pi, Claude Code, Codex, ...)
#   ./tools/install.sh --target DIR         # custom destination
#   ./tools/install.sh --domain compose     # only one domain
#   ./tools/install.sh --level core         # only core-level skills
#   ./tools/install.sh --list               # show what would be installed
#   ./tools/install.sh --link               # symlink instead of copy (repo stays authoritative)
#   ./tools/install.sh --uninstall          # remove previously installed skills
set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET="$HOME/.agents/skills"
MODE=copy
DOMAIN=""
LEVEL=""
ACTION=install

while [[ $# -gt 0 ]]; do
  case "$1" in
    --target)    TARGET="$2"; shift 2 ;;
    --domain)    DOMAIN="$2"; shift 2 ;;
    --level)     LEVEL="$2"; shift 2 ;;
    --link)      MODE=link; shift ;;
    --uninstall) ACTION=uninstall; shift ;;
    --list)      ACTION=list; shift ;;
    -h|--help)   sed -n '2,12p' "$0"; exit 0 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done

# Collect skill directories honouring the filters.
mapfile -t SKILLS < <(
  find "$SRC/skills" -name SKILL.md -printf '%h\n' | sort | while read -r dir; do
    if [[ -n "$DOMAIN" ]]; then
      d=$(sed -n 's/^  domain: *//p' "$dir/SKILL.md" | head -1)
      [[ "$d" == "$DOMAIN" ]] || continue
    fi
    if [[ -n "$LEVEL" ]]; then
      lvl=$(sed -n '/^  level:/s/^  level: *//p' "$dir/SKILL.md" | head -1)
      [[ "$lvl" == "$LEVEL" ]] || continue
    fi
    echo "$dir"
  done
)

if [[ ${#SKILLS[@]} -eq 0 ]]; then
  echo "no skills matched (domain='$DOMAIN' level='$LEVEL')" >&2
  exit 1
fi

case "$ACTION" in
  list)
    printf '%s\n' "${SKILLS[@]}" | sed "s|$SRC/||"
    echo "--- ${#SKILLS[@]} skills"
    exit 0
    ;;
  uninstall)
    n=0
    for d in "${SKILLS[@]}"; do
      name=$(basename "$d")
      if [[ -e "$TARGET/$name" || -L "$TARGET/$name" ]]; then rm -rf "$TARGET/${name:?}"; n=$((n+1)); fi
    done
    echo "removed $n from $TARGET"
    exit 0
    ;;
esac

mkdir -p "$TARGET"
n=0
for d in "${SKILLS[@]}"; do
  name=$(basename "$d")
  rm -rf "$TARGET/$name"
  if [[ "$MODE" == link ]]; then ln -s "$d" "$TARGET/$name"; else cp -r "$d" "$TARGET/$name"; fi
  n=$((n+1))
done

cat <<EOF
installed $n skills ($MODE) -> $TARGET

Next: restart the agent so it re-scans the directory.
Verify inside the agent: ask it to list skills, or run a forced load:
  /skill:<name>
EOF
