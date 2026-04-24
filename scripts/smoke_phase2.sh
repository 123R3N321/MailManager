#!/usr/bin/env bash
# Post-apply smoke: SQS send + optional HTTP enqueue.
# Prereqs: terraform apply in infra/terraform, AWS CLI credentials, jq.
# Optional: export API_URL="$(cd infra/terraform && terraform output -raw api_invoke_url)"
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TF_DIR="${ROOT}/infra/terraform"

cd "${TF_DIR}"
QUEUE_URL="$(terraform output -raw sqs_ingest_queue_url)"
QUEUE_NAME="$(terraform output -raw sqs_ingest_queue_name)"
REGION="$(terraform output -raw aws_region)"
REGION="${REGION:-${AWS_REGION:-us-east-1}}"
export AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-${REGION}}"

MSG="smoke-phase2-$(date +%s)"
echo "Sending SQS message to ${QUEUE_NAME} (${QUEUE_URL})..."
aws sqs send-message --queue-url "${QUEUE_URL}" --message-body "${MSG}" >/dev/null
echo "Waiting for worker to consume (up to 60s)..."
for _ in $(seq 1 30); do
  ATTRIBUTES=$(aws sqs get-queue-attributes \
    --queue-url "${QUEUE_URL}" \
    --attribute-names ApproximateNumberOfMessages ApproximateNumberOfMessagesNotVisible \
    --output json)
  VISIBLE=$(echo "${ATTRIBUTES}" | jq -r '.Attributes.ApproximateNumberOfMessages // "0"')
  NOTVIS=$(echo "${ATTRIBUTES}" | jq -r '.Attributes.ApproximateNumberOfMessagesNotVisible // "0"')
  if [[ "${VISIBLE}" == "0" && "${NOTVIS}" == "0" ]]; then
    echo "Queue is empty (message processed or moved)."
    break
  fi
  sleep 2
done

echo "Latest worker log streams (if any):"
FUNC_NAME="$(terraform output -raw lambda_ingest_worker_function_name)"
aws logs describe-log-streams \
  --log-group-name "/aws/lambda/${FUNC_NAME}" \
  --order-by LastEventTime \
  --descending \
  --limit 1 \
  --query 'logStreams[0].logStreamName' \
  --output text 2>/dev/null | while read -r STREAM; do
  [[ -z "${STREAM}" || "${STREAM}" == "None" ]] && continue
  echo "--- tail ${STREAM} ---"
  aws logs get-log-events --log-group-name "/aws/lambda/${FUNC_NAME}" --log-stream-name "${STREAM}" --limit 5 --query 'events[].message' --output text || true
done

if [[ -n "${API_URL:-}" ]]; then
  echo "Optional API_URL smoke: POST ${API_URL}enqueue"
  curl -sS -o /tmp/mm_enqueue.json -w "\nHTTP %{http_code}\n" -X POST "${API_URL}enqueue" -H 'Content-Type: application/json' -d "{\"source\":\"smoke\",\"msg\":\"${MSG}\"}" || true
  cat /tmp/mm_enqueue.json 2>/dev/null || true
fi

echo "Smoke phase2 finished."
