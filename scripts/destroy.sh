#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}/infra/terraform"
terraform init -input=false
terraform destroy -input=false -var-file="${VAR_FILE:-examples/demo.tfvars}" "$@"
