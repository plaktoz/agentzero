#!/usr/bin/env bash
# install.sh — deploy the agentzero multi-agent pipeline into a project
#
# Remote (curl | bash):
#   curl -fsSL https://raw.githubusercontent.com/plaktoz/agentzero/main/dist/install.sh | bash
#   curl -fsSL https://raw.githubusercontent.com/plaktoz/agentzero/main/dist/install.sh | bash -s -- my-project
#
# Local (from a cloned copy):
#   ./dist/install.sh                  # install into current directory
#   ./dist/install.sh /path/to/project # install into a specific directory
#
# Works for both greenfield (new project) and brownfield (existing project).
# Brownfield: merges pipeline files without overwriting your existing code or config.

set -euo pipefail

REPO="plaktoz/agentzero"
BRANCH="main"

# ── colours ─────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; BOLD='\033[1m'; NC='\033[0m'
info()  { echo -e "${GREEN}+${NC} $*"; }
skip()  { echo -e "${YELLOW}~${NC} $*"; }
error() { echo -e "${RED}!${NC} $*" >&2; exit 1; }
header(){ echo -e "\n${BOLD}$*${NC}"; }

# ── detect local vs remote ───────────────────────────────────────────────────
# When piped from curl, BASH_SOURCE[0] is empty or /dev/stdin
_src="${BASH_SOURCE[0]:-}"
if [[ -z "$_src" || "$_src" == /dev/stdin || "$_src" == /proc/self/fd/* ]]; then
  IS_REMOTE=true
else
  IS_REMOTE=false
  REPO_ROOT="$(cd "$(dirname "$_src")/.." && pwd)"
fi

# ── remote: check deps and download template ─────────────────────────────────
if [[ "$IS_REMOTE" == true ]]; then
  command -v curl >/dev/null 2>&1 || error "curl is required but not installed"
  command -v tar  >/dev/null 2>&1 || error "tar is required but not installed"
  command -v git  >/dev/null 2>&1 || error "git is required but not installed"

  TMP_DIR="$(mktemp -d)"
  trap 'rm -rf "$TMP_DIR"' EXIT HUP INT TERM

  echo ""
  echo -e "${BOLD}agentzero — autonomous multi-agent pipeline installer${NC}"
  echo "  Source: https://github.com/${REPO}"

  TARBALL="https://github.com/${REPO}/archive/refs/heads/${BRANCH}.tar.gz"
  curl -fsSL "$TARBALL" | tar -xz -C "$TMP_DIR"
  REPO_ROOT="${TMP_DIR}/$(ls "$TMP_DIR" | head -1)"
  info "Template downloaded"
fi

# ── resolve target ────────────────────────────────────────────────────────────
TARGET="${1:-}"

if [[ -z "$TARGET" ]]; then
  if [[ "$IS_REMOTE" == true ]]; then
    error "No project directory specified. Usage: ... | bash -s -- <project-dir>"
  else
    TARGET="$(pwd)"
  fi
fi

# Create target if it doesn't exist (greenfield remote install)
if [[ ! -d "$TARGET" ]]; then
  mkdir -p "$TARGET"
  info "Created directory: $TARGET"
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
if [[ "$IS_REMOTE" == false ]]; then
  echo ""
  echo -e "${BOLD}agentzero — autonomous multi-agent pipeline installer${NC}"
fi
echo "  Mode:   $MODE"
[[ "$IS_REMOTE" == false ]] && echo "  Source: $REPO_ROOT"
echo "  Target: $TARGET"
echo ""

if [ "$MODE" = brownfield ]; then
  echo "Brownfield mode: existing files will not be overwritten."
  echo "New pipeline files will be added alongside your project."
  echo ""
fi

# ── 1. .agents/skills ────────────────────────────────────────────────────────
header "1/11  Skills"

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
header "2/11  Claude Code config"
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

# 2c. .claude/settings.json (permission allowlist)
if [ -f "$TARGET/.claude/settings.json" ]; then
  skip ".claude/settings.json already exists"
else
  cp "$REPO_ROOT/.claude/settings.json" "$TARGET/.claude/settings.json"
  info ".claude/settings.json (permission allowlist)"
fi

# ── 3. Pipeline config + shared vocabulary ───────────────────────────────────
header "3/11  Pipeline config"

if [ -f "$TARGET/agent-config.yml" ]; then
  skip "agent-config.yml already exists — skipped (compare with source for new fields)"
else
  cp "$REPO_ROOT/agent-config.yml" "$TARGET/agent-config.yml"
  info "agent-config.yml"
fi

if [ -f "$TARGET/CONTEXT.md" ]; then
  skip "CONTEXT.md already exists"
else
  cp "$REPO_ROOT/CONTEXT.md" "$TARGET/CONTEXT.md"
  info "CONTEXT.md (shared pipeline vocabulary)"
fi

# ── 4. .env.example ──────────────────────────────────────────────────────────
header "4/11  Environment template"

if [ -f "$TARGET/.env.example" ]; then
  skip ".env.example already exists"
else
  cp "$REPO_ROOT/.env.example" "$TARGET/.env.example"
  info ".env.example"
fi

# ── 5. knowledge_base ────────────────────────────────────────────────────────
header "5/11  Knowledge base"

if [ -d "$TARGET/knowledge_base" ]; then
  skip "knowledge_base/ already exists"
else
  mkdir -p "$TARGET/knowledge_base/lessons/raw" \
           "$TARGET/knowledge_base/lessons/distilled"
  cp "$REPO_ROOT/knowledge_base/index.md" \
     "$TARGET/knowledge_base/index.md"
  cp "$REPO_ROOT/knowledge_base/guardrails_candidates.md" \
     "$TARGET/knowledge_base/guardrails_candidates.md"
  cp "$REPO_ROOT/knowledge_base/guardrails.yaml" \
     "$TARGET/knowledge_base/guardrails.yaml"
  cp "$REPO_ROOT/knowledge_base/failure-patterns.md" \
     "$TARGET/knowledge_base/failure-patterns.md"
  info "knowledge_base/ (lessons/raw, lessons/distilled, index, guardrails.yaml, failure-patterns)"
fi

# ── 6. eval ──────────────────────────────────────────────────────────────────
header "6/11  Eval golden tests"

if [ -d "$TARGET/eval" ]; then
  skip "eval/ already exists"
else
  cp -r "$REPO_ROOT/eval" "$TARGET/eval"
  # Remove any scores from template runs — start fresh
  echo "| timestamp | run | role | score | notes |" > "$TARGET/eval/scores-log.md"
  echo "|---|---|---|---|---|" >> "$TARGET/eval/scores-log.md"
  info "eval/ (golden tests for orchestrator / analyst / coder)"
fi

# ── 7. pipeline working directory ────────────────────────────────────────────
header "7/11  Pipeline run directory"

if [ -d "$TARGET/pipeline" ]; then
  skip "pipeline/ already exists"
else
  mkdir -p "$TARGET/pipeline"
  touch "$TARGET/pipeline/.gitkeep"
  info "pipeline/"
fi

# ── 8. scripts ───────────────────────────────────────────────────────────────
header "8/11  Utility scripts"

if [ -d "$TARGET/scripts" ]; then
  skip "scripts/ already exists"
else
  cp -r "$REPO_ROOT/scripts" "$TARGET/scripts"
  info "scripts/ (validate_config.py, check_providers.py, call_provider.py, requirements.txt)"
fi

# ── 9. steering ──────────────────────────────────────────────────────────────
header "9/11  Steering files"

if [ -d "$TARGET/steering" ]; then
  skip "steering/ already exists"
else
  cp -r "$REPO_ROOT/steering" "$TARGET/steering"
  role_count=$(ls "$REPO_ROOT/steering/roles" 2>/dev/null | wc -l | tr -d ' ')
  info "steering/ (product.md, tech.md, structure.md, backlog.md, $role_count role guides)"
fi

# ── 10. .gitignore ───────────────────────────────────────────────────────────
header "10/11  .gitignore"

declare -a GITIGNORE_LINES=(
  ".env"
  ".env.*"
  "pipeline-log.md"
  ".worktrees/"
  ".claude/settings.local.json"
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

# ── 11. git init (greenfield only) ───────────────────────────────────────────
header "11/11  Git"

if [ -d "$TARGET/.git" ]; then
  skip "git repo already exists"
elif [ "$MODE" = greenfield ]; then
  git -C "$TARGET" init -q
  git -C "$TARGET" add .
  git -C "$TARGET" commit -q -m "chore: initial commit from agentzero template"
  info "git repository initialised with initial commit"
fi

# ── validate config ───────────────────────────────────────────────────────────
echo ""
if command -v python3 >/dev/null 2>&1 && [ -f "$TARGET/scripts/validate_config.py" ]; then
  python3 "$TARGET/scripts/validate_config.py" "$TARGET/agent-config.yml" 2>/dev/null \
    && info "agent-config.yml validated" \
    || echo -e "${YELLOW}~${NC} Config validation failed — review agent-config.yml before first run"
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
echo "        # cost_governance.max_cost_per_run — your budget cap (default \$5.00)"
echo "        # test_env.runtime                 — docker | podman | none"
echo "        # deploy.target_environment        — local | staging | production"
echo ""
echo "  3.  Install Python dependencies (for validation scripts):"
echo "        cd $TARGET && python3 -m venv .venv && .venv/bin/pip install -r scripts/requirements.txt"
echo ""
if [ "$MODE" = greenfield ]; then
  echo "  4.  Open the project in Claude Code and run:"
  echo "        /proj-start"
else
  echo "  4.  Open the project in Claude Code and run:"
  echo "        /proj-new-feature   — single feature or bug fix"
  echo "        /proj-epic          — multiple related features"
fi
echo ""
