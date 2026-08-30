#!/usr/bin/env bash
# install.sh — deploy the agentzero multi-agent pipeline into a project
#
# Usage:
#   ./dist/install.sh                  # install into current directory
#   ./dist/install.sh /path/to/project # install into a specific directory
#
# Works for both greenfield (new project) and brownfield (existing project).
# Brownfield: merges pipeline files without overwriting your existing code or config.

set -euo pipefail

# ── colours ─────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; BOLD='\033[1m'; NC='\033[0m'
info()  { echo -e "${GREEN}+${NC} $*"; }
skip()  { echo -e "${YELLOW}~${NC} $*"; }
error() { echo -e "${RED}✗${NC} $*" >&2; }
header(){ echo -e "\n${BOLD}$*${NC}"; }

# ── paths ────────────────────────────────────────────────────────────────────
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET="${1:-$(pwd)}"

if [ ! -d "$TARGET" ]; then
  error "Target directory does not exist: $TARGET"
  exit 1
fi
TARGET="$(cd "$TARGET" && pwd)"

# ── detect greenfield vs brownfield ─────────────────────────────────────────
# brownfield = has recognisable project files or a non-empty git history
is_brownfield() {
  [ -f "$TARGET/package.json" ]   && return 0
  [ -f "$TARGET/pyproject.toml" ] && return 0
  [ -f "$TARGET/go.mod" ]         && return 0
  [ -f "$TARGET/Cargo.toml" ]     && return 0
  [ -f "$TARGET/pom.xml" ]        && return 0
  [ -f "$TARGET/build.gradle" ]   && return 0
  if [ -d "$TARGET/.git" ]; then
    commit_count=$(git -C "$TARGET" rev-list --count HEAD 2>/dev/null || echo 0)
    [ "$commit_count" -gt 0 ] && return 0
  fi
  return 1
}

if is_brownfield; then
  MODE=brownfield
else
  MODE=greenfield
fi

# ── header ───────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}agentzero — autonomous multi-agent pipeline installer${NC}"
echo "  Mode:   $MODE"
echo "  Source: $REPO_ROOT"
echo "  Target: $TARGET"
echo ""

if [ "$MODE" = brownfield ]; then
  echo "Brownfield mode: existing files will not be overwritten."
  echo "New pipeline files will be added alongside your project."
  echo ""
fi

# ── 1. .agents/skills ────────────────────────────────────────────────────────
header "1/9  Skills"

if [ -d "$TARGET/.agents/skills" ]; then
  skip ".agents/skills/ already exists — merging new skills only"
  added=0
  for skill_dir in "$REPO_ROOT/.agents/skills"/*/; do
    skill_name=$(basename "$skill_dir")
    dest="$TARGET/.agents/skills/$skill_name"
    if [ -d "$dest" ]; then
      skip "  skip .agents/skills/$skill_name (exists)"
    else
      cp -r "$skill_dir" "$dest"
      info "  .agents/skills/$skill_name"
      added=$((added + 1))
    fi
  done
  [ "$added" -eq 0 ] && skip "  no new skills to add" || info "  $added skill(s) added"
else
  mkdir -p "$TARGET/.agents"
  cp -r "$REPO_ROOT/.agents/skills" "$TARGET/.agents/skills"
  skill_count=$(ls "$REPO_ROOT/.agents/skills" | wc -l | tr -d ' ')
  info ".agents/skills/ ($skill_count skills)"
fi

# ── 2. .claude/ setup ────────────────────────────────────────────────────────
header "2/9  Claude Code config"
mkdir -p "$TARGET/.claude"

# 2a. CLAUDE.md
MARKER="Autonomous Multi-Agent Pipeline"
claude_md_target=""

if [ -f "$TARGET/.claude/CLAUDE.md" ]; then
  claude_md_target="$TARGET/.claude/CLAUDE.md"
elif [ -f "$TARGET/CLAUDE.md" ]; then
  claude_md_target="$TARGET/CLAUDE.md"
fi

if [ -n "$claude_md_target" ]; then
  if grep -q "$MARKER" "$claude_md_target" 2>/dev/null; then
    skip "CLAUDE.md: agentzero block already present"
  else
    printf '\n\n' >> "$claude_md_target"
    cat "$REPO_ROOT/CLAUDE.md" >> "$claude_md_target"
    skip "CLAUDE.md: agentzero block appended to existing file"
  fi
else
  cp "$REPO_ROOT/CLAUDE.md" "$TARGET/CLAUDE.md"
  info "CLAUDE.md"
fi

# 2b. .claude/skills symlink
if [ -L "$TARGET/.claude/skills" ]; then
  skip ".claude/skills symlink already exists"
elif [ -d "$TARGET/.claude/skills" ]; then
  skip ".claude/skills is a real directory — remove it to install the symlink"
else
  ln -sf ../.agents/skills "$TARGET/.claude/skills"
  info ".claude/skills -> ../.agents/skills (symlink)"
fi

# ── 3. agent-config.yml ──────────────────────────────────────────────────────
header "3/9  Pipeline config"

if [ -f "$TARGET/agent-config.yml" ]; then
  skip "agent-config.yml already exists — skipped (compare with $REPO_ROOT/agent-config.yml for new fields)"
else
  cp "$REPO_ROOT/agent-config.yml" "$TARGET/agent-config.yml"
  info "agent-config.yml"
fi

# ── 4. .env.example ──────────────────────────────────────────────────────────
header "4/9  Environment template"

if [ -f "$TARGET/.env.example" ]; then
  skip ".env.example already exists"
else
  cp "$REPO_ROOT/.env.example" "$TARGET/.env.example"
  info ".env.example"
fi

# ── 5. knowledge_base ────────────────────────────────────────────────────────
header "5/9  Knowledge base"

if [ -d "$TARGET/knowledge_base" ]; then
  skip "knowledge_base/ already exists"
else
  mkdir -p "$TARGET/knowledge_base/lessons/raw" \
           "$TARGET/knowledge_base/lessons/distilled"
  cp "$REPO_ROOT/knowledge_base/index.md" \
     "$TARGET/knowledge_base/index.md"
  cp "$REPO_ROOT/knowledge_base/guardrails_candidates.md" \
     "$TARGET/knowledge_base/guardrails_candidates.md"
  info "knowledge_base/ (lessons/raw, lessons/distilled, index, guardrails)"
fi

# ── 6. eval ──────────────────────────────────────────────────────────────────
header "6/9  Eval golden tests"

if [ -d "$TARGET/eval" ]; then
  skip "eval/ already exists"
else
  cp -r "$REPO_ROOT/eval" "$TARGET/eval"
  info "eval/ (scores-log, golden tests for orchestrator / analyst / coder)"
fi

# ── 7. pipeline working directory ────────────────────────────────────────────
header "7/9  Pipeline run directory"

if [ -d "$TARGET/pipeline" ]; then
  skip "pipeline/ already exists"
else
  mkdir -p "$TARGET/pipeline"
  touch "$TARGET/pipeline/.gitkeep"
  info "pipeline/"
fi

# ── 8. scripts ───────────────────────────────────────────────────────────────
header "8/9  Utility scripts"

if [ -d "$TARGET/scripts" ]; then
  skip "scripts/ already exists"
else
  cp -r "$REPO_ROOT/scripts" "$TARGET/scripts"
  info "scripts/ (check_providers.py, validate_config.py)"
fi

# ── 9. .gitignore ────────────────────────────────────────────────────────────
header "9/9  .gitignore"

declare -a GITIGNORE_LINES=(
  ".env"
  ".env.*"
  "pipeline-log.md"
  ".worktrees/"
)

if [ -f "$TARGET/.gitignore" ]; then
  for line in "${GITIGNORE_LINES[@]}"; do
    if grep -qxF "$line" "$TARGET/.gitignore" 2>/dev/null; then
      skip ".gitignore: $line (already present)"
    else
      echo "$line" >> "$TARGET/.gitignore"
      info ".gitignore += $line"
    fi
  done
else
  printf '%s\n' "${GITIGNORE_LINES[@]}" > "$TARGET/.gitignore"
  info ".gitignore (created)"
fi

# ── done ─────────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}Installation complete.${NC}"
echo ""
echo "Next steps:"
echo ""
echo "  1.  Set up API credentials:"
echo "        cp $TARGET/.env.example $TARGET/.env"
echo "        # edit .env and fill in ANTHROPIC_API_KEY, OPENAI_API_KEY, etc."
echo ""
echo "  2.  Review agent-config.yml:"
echo "        # set cost_governance.max_cost_per_run to your budget"
echo "        # set deploy.target_environment to local | staging | production"
echo "        # set test_env.runtime to docker | podman | none"
echo ""
echo "  3.  Install Python dependencies (for validation scripts):"
echo "        cd $TARGET && python3 -m venv .venv && .venv/bin/pip install -r scripts/requirements.txt"
echo ""
echo "  4.  Validate config and check connectivity:"
echo "        python3 scripts/validate_config.py"
echo "        python3 scripts/check_providers.py"
echo ""
if [ "$MODE" = greenfield ]; then
  echo "  5.  Start your project in Claude Code:"
  echo "        /proj-start"
else
  echo "  5.  Start a pipeline run in Claude Code:"
  echo "        /proj-new-feature   — single feature or bug fix"
  echo "        /proj-epic          — multiple related features"
fi
echo ""
