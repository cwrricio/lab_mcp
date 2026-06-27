#!/usr/bin/env bash
# Wrapper so you can type `sentinel` instead of `uv run lab-sentinel`.
# Usage: add the alias below to your ~/.bashrc or ~/.zshrc:
#   alias sentinel='bash /path/to/lab_mcp/sentinel.sh'
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
export PATH="$HOME/.local/bin:$PATH"
exec uv run lab-sentinel "$@"
