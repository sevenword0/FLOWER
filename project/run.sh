#!/usr/bin/env bash
# Convenience wrapper so biogen runs without installation.
# Usage: ./run.sh <command> [args]   e.g.  ./run.sh simulate
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONPATH="${HERE}/src:${PYTHONPATH:-}"
exec python3 -m biogen.cli "$@"
