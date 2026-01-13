#!/bin/bash
# Install git hooks to prevent AI attribution

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
HOOKS_DIR="$REPO_ROOT/.git/hooks"

echo "Installing git hooks..."

# Copy hooks
cp "$SCRIPT_DIR/hooks/commit-msg" "$HOOKS_DIR/commit-msg"
cp "$SCRIPT_DIR/hooks/pre-commit" "$HOOKS_DIR/pre-commit"

# Make executable
chmod +x "$HOOKS_DIR/commit-msg"
chmod +x "$HOOKS_DIR/pre-commit"

echo "Git hooks installed successfully!"
echo ""
echo "Installed hooks:"
echo "  - commit-msg: Prevents AI attribution in commit messages"
echo "  - pre-commit: Prevents AI attribution in staged files"
