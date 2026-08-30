#!/usr/bin/env bash
# uninstall.sh — remove the agentzero pipeline layer from a project
#
# Usage:
#   ./dist/uninstall.sh                  # remove from current directory
#   ./dist/uninstall.sh /path/to/project # remove from a specific directory
#
# What is removed:   .agents/skills/,  .claude/skills symlink, .worktrees/
# Prompted removal:  pipeline/,  eval/,  knowledge_base/
# Always kept:       agent-config.yml,  .env.example,  scripts/,  your source code

set -euo pipefail

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; BOLD='\033[1m'; NC='\033[0m'
info()   { echo -e "${GREEN}-${NC} $*"; }
warn()   { echo -e "${YELLOW}!${NC} $*"; }
kept()   { echo -e "  kept  $*"; }
error()  { echo -e "${RED}✗${NC} $*" >&2; }
confirm(){ read -r -p "$1 [y/N] " _r; [[ "$_r" =~ ^[Yy]$ ]]; }

TARGET="${1:-$(pwd)}"
if [ ! -d "$TARGET" ]; then
  error "Target directory does not exist: $TARGET"
  exit 1
fi
TARGET="$(cd "$TARGET" && pwd)"

echo ""
echo -e "${BOLD}agentzero — uninstaller${NC}"
echo "  Target: $TARGET"
echo ""
echo "The following will be removed automatically:"
echo "  .agents/skills/       (all pipeline skills)"
echo "  .claude/skills        (symlink only)"
echo "  .worktrees/           (any leftover worktrees)"
echo ""
echo "You will be asked about:"
echo "  pipeline/             (run state — may contain in-progress work)"
echo "  eval/                 (golden tests and scores)"
echo "  knowledge_base/       (lessons and guardrails)"
echo ""
echo "Always kept:"
echo "  agent-config.yml      source/scripts/  .env.example  your code"
echo ""

confirm "Proceed with uninstall?" || { echo "Aborted."; exit 0; }
echo ""

# ── skills ───────────────────────────────────────────────────────────────────
if [ -d "$TARGET/.agents/skills" ]; then
  rm -rf "$TARGET/.agents/skills"
  info ".agents/skills/ removed"
  if [ -d "$TARGET/.agents" ] && [ -z "$(ls -A "$TARGET/.agents" 2>/dev/null)" ]; then
    rmdir "$TARGET/.agents"
    info ".agents/ removed (was empty)"
  fi
else
  kept ".agents/skills/ (not found)"
fi

# ── .claude/skills symlink ───────────────────────────────────────────────────
if [ -L "$TARGET/.claude/skills" ]; then
  rm "$TARGET/.claude/skills"
  info ".claude/skills symlink removed"
else
  kept ".claude/skills (not a symlink or not found)"
fi

# ── worktrees ────────────────────────────────────────────────────────────────
if [ -d "$TARGET/.worktrees" ]; then
  # deregister any registered worktrees first
  if command -v git &>/dev/null && [ -d "$TARGET/.git" ]; then
    while IFS= read -r wt_path; do
      [ -z "$wt_path" ] && continue
      git -C "$TARGET" worktree remove --force "$wt_path" 2>/dev/null || true
      info ".worktrees/$(basename "$wt_path") deregistered"
    done < <(find "$TARGET/.worktrees" -mindepth 1 -maxdepth 1 -type d)
  fi
  rm -rf "$TARGET/.worktrees"
  info ".worktrees/ removed"
else
  kept ".worktrees/ (not found)"
fi

# ── CLAUDE.md agentzero block ────────────────────────────────────────────────
# If agentzero block was appended to an existing CLAUDE.md, offer to remove it
MARKER="Autonomous Multi-Agent Pipeline"
for claude_candidate in "$TARGET/CLAUDE.md" "$TARGET/.claude/CLAUDE.md"; do
  if [ -f "$claude_candidate" ] && grep -q "$MARKER" "$claude_candidate" 2>/dev/null; then
    if confirm "Remove agentzero block from $(basename "$claude_candidate")?"; then
      # Remove from the marker line to end of file (agentzero block was appended)
      # Use awk: print lines before the marker
      awk "/^# $MARKER$/{found=1} !found{print}" "$claude_candidate" > "${claude_candidate}.tmp" \
        && mv "${claude_candidate}.tmp" "$claude_candidate"
      # Remove trailing blank lines
      sed -i '' -e 's/[[:space:]]*$//' "$claude_candidate" 2>/dev/null || true
      info "$(basename "$claude_candidate"): agentzero block removed"
    else
      kept "$(basename "$claude_candidate")"
    fi
  fi
done

# ── prompted: pipeline/ ──────────────────────────────────────────────────────
echo ""
if [ -d "$TARGET/pipeline" ]; then
  # Check for in-progress runs
  in_progress=$(find "$TARGET/pipeline" -name "state.md" -exec grep -l "in_progress" {} \; 2>/dev/null | wc -l | tr -d ' ')
  if [ "$in_progress" -gt 0 ]; then
    warn "pipeline/ has $in_progress in-progress run(s). Removing will lose their state."
  fi
  if confirm "Remove pipeline/ (all run state)?"; then
    rm -rf "$TARGET/pipeline"
    info "pipeline/ removed"
  else
    kept "pipeline/"
  fi
fi

# ── prompted: eval/ ──────────────────────────────────────────────────────────
if [ -d "$TARGET/eval" ]; then
  if confirm "Remove eval/ (golden tests and scores)?"; then
    rm -rf "$TARGET/eval"
    info "eval/ removed"
  else
    kept "eval/"
  fi
fi

# ── prompted: knowledge_base/ ────────────────────────────────────────────────
if [ -d "$TARGET/knowledge_base" ]; then
  lesson_count=$(find "$TARGET/knowledge_base/lessons/distilled" -name "*.md" 2>/dev/null | wc -l | tr -d ' ')
  if [ "$lesson_count" -gt 0 ]; then
    warn "knowledge_base/ contains $lesson_count distilled lesson(s). Removing will lose them."
  fi
  if confirm "Remove knowledge_base/ (lessons and guardrails)?"; then
    rm -rf "$TARGET/knowledge_base"
    info "knowledge_base/ removed"
  else
    kept "knowledge_base/"
  fi
fi

# ── done ─────────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}Uninstall complete.${NC}"
echo ""
echo "Kept: agent-config.yml  .env.example  scripts/"
echo "      (remove manually if no longer needed)"
echo ""
