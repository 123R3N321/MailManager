#!/usr/bin/env bash
# Usage: source scripts/env.sh
# Loads .env from the repo root and exports all variables into the current shell.

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  echo "ERROR: run this with 'source scripts/env.sh', not './' — variables won't survive a subprocess." >&2
  exit 1
fi

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${REPO_ROOT}/.env"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "ERROR: ${ENV_FILE} not found. Copy .env.example to .env and fill in your values." >&2
  return 1 2>/dev/null || exit 1
fi

set -o allexport
# shellcheck source=/dev/null
source "$ENV_FILE"
set +o allexport

echo "Environment loaded from ${ENV_FILE}"
env | grep -E "^(API_URL|REGION|ACCOUNT_ID|TABLE|RAW_BUCKET|FRONTEND_BUCKET|QUEUE_URL|DLQ_URL|LAMBDA_API|LAMBDA_WORKER|LAMBDA_SCHED|OS_ENDPOINT|OS_INDEX)=" | sort
