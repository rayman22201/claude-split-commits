#!/usr/bin/env bash
# Install the split-commits skill + git-hunk-tool for Claude Code.
#
# Usage:
#   bash install.sh
#
# What it does:
#   1. Detects the correct Python 3 binary (python or python3)
#   2. Installs git-hunk-tool as a Python package
#   3. Copies the split-commits skill to ~/.claude/commands/
#      with the correct python command baked in

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# --- Detect Python 3 ---
PYTHON=""
for candidate in python python3; do
    if command -v "$candidate" &>/dev/null; then
        version=$("$candidate" -c "import sys; print(sys.version_info.major)" 2>/dev/null || echo "")
        if [ "$version" = "3" ]; then
            PYTHON="$candidate"
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    echo "Error: Python 3 not found. Install Python 3 and ensure 'python' or 'python3' is on PATH." >&2
    exit 1
fi

echo "Using Python 3 via: $PYTHON"

# --- Detect matching pip ---
PIP=""
for candidate in pip pip3; do
    if command -v "$candidate" &>/dev/null; then
        owner=$("$candidate" --version 2>/dev/null | grep -oP 'python \K[0-9]+' || echo "")
        if [ "$owner" = "3" ]; then
            PIP="$candidate"
            break
        fi
    fi
done

# Fallback: use python -m pip
if [ -z "$PIP" ]; then
    PIP="$PYTHON -m pip"
fi

echo "Using pip via: $PIP"

# --- Install package ---
echo ""
echo "=== Installing git-hunk-tool Python package ==="
$PIP install "$SCRIPT_DIR"

# --- Install skill with correct python command ---
echo ""
echo "=== Installing split-commits Claude Code skill ==="
CLAUDE_COMMANDS_DIR="$HOME/.claude/commands"
mkdir -p "$CLAUDE_COMMANDS_DIR"
sed "s|{{PYTHON}}|$PYTHON|g" "$SCRIPT_DIR/skill/split-commits.md" > "$CLAUDE_COMMANDS_DIR/split-commits.md"

echo ""
echo "Done! You can now use /split-commits in Claude Code."
echo ""
echo "Verify with:"
echo "  $PYTHON -m git_hunk_tool --help"
