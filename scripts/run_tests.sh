#!/usr/bin/env bash
set -euo pipefail
pytest
ruff check .
mypy specforge_core specforge_cli specforge_daemon
