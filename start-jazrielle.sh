#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

if ! command -v conda >/dev/null 2>&1; then
  for conda_init in \
    "${CONDA_PREFIX:-}/etc/profile.d/conda.sh" \
    "$HOME/anaconda3/etc/profile.d/conda.sh"; do
    if [[ -f "$conda_init" ]]; then
      # shellcheck source=/dev/null
      source "$conda_init"
      break
    fi
  done
fi

if ! command -v conda >/dev/null 2>&1; then
  echo "conda was not found. Initialize Conda before running this script." >&2
  exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "npm was not found. Install Node.js before running this script." >&2
  exit 1
fi

cleanup() {
  kill "$backend_pid" "$frontend_pid" 2>/dev/null || true
}

trap cleanup INT TERM EXIT

(
  cd "$ROOT_DIR/backend"
  exec conda run --no-capture-output -n jazrielle-backend \
    uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
) &
backend_pid=$!

(
  cd "$ROOT_DIR/frontend"
  exec npm run dev
) &
frontend_pid=$!

wait "$backend_pid" "$frontend_pid"
