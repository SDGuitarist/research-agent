#!/bin/bash
set -euo pipefail

# Only run in remote (Claude Code on the web) environments
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

# Install package in editable mode with test dependencies
pip install -e "${CLAUDE_PROJECT_DIR:-.}[test]"
