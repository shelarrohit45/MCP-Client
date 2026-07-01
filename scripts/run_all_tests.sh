#!/usr/bin/env bash
# Run the full MCP client test suite locally.
#
# Usage:
#   ./scripts/run_all_tests.sh           # all tests (needs .env + MCP servers)
#   ./scripts/run_all_tests.sh --unit    # code/unit tests only (no live GitHub/Email MCP)
#   ./scripts/run_all_tests.sh --live    # integration tests only (steps 3–5)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PYTHON="${ROOT}/venv/bin/python"
MODE="all"

for arg in "$@"; do
  case "$arg" in
    --unit) MODE="unit" ;;
    --live) MODE="live" ;;
    -h|--help)
      sed -n '2,6p' "$0"
      exit 0
      ;;
    *)
      echo "Unknown option: $arg (use --unit, --live, or no flag for all)"
      exit 1
      ;;
  esac
done

if [[ ! -x "$PYTHON" ]]; then
  echo "Virtualenv not found. Run:"
  echo "  python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
  exit 1
fi

UNIT_TESTS=(
  scripts/test_step01.py
  scripts/test_step02.py
  scripts/test_step10.py
  scripts/test_step11.py
)

LIVE_TESTS=(
  scripts/check_prerequisites.py
  scripts/test_step03.py
  scripts/test_step04.py
  scripts/test_step05.py
  scripts/test_step06.py
  scripts/test_step07.py
  scripts/test_step08.py
  scripts/test_step09.py
)

run_tests() {
  local label="$1"
  shift
  local tests=("$@")
  local failed=0

  echo "========================================"
  echo "$label"
  echo "========================================"

  for test in "${tests[@]}"; do
    echo
    echo "--- $test ---"
    if "$PYTHON" "$test"; then
      echo "[OK] $test"
    else
      echo "[FAIL] $test"
      failed=$((failed + 1))
    fi
  done

  return "$failed"
}

total_failed=0

case "$MODE" in
  unit)
    run_tests "Unit / code tests (no live MCP)" "${UNIT_TESTS[@]}" || total_failed=$?
    ;;
  live)
    run_tests "Live integration tests (GitHub + Email MCP)" "${LIVE_TESTS[@]}" || total_failed=$?
    ;;
  all)
    run_tests "Unit / code tests" "${UNIT_TESTS[@]}" || total_failed=$?
    echo
    run_tests "Live integration tests" "${LIVE_TESTS[@]}" || total_failed=$?
    ;;
esac

echo
if [[ "$total_failed" -eq 0 ]]; then
  echo "All test groups passed."
  exit 0
fi

echo "$total_failed test script(s) failed."
exit 1
