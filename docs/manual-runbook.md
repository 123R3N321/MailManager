# Manual runbook (operators and graders)

This guide explains how to **deploy**, **verify**, and **destroy** the MailManager infrastructure, and how each AWS component can be inspected manually.

## Prerequisites

- [Terraform](https://www.terraform.io/downloads) `>= 1.6.0`
- [AWS CLI](https://aws.amazon.com/cli/) v2 configured (`aws sts get-caller-identity` works)
- An AWS account with permission to create API Gateway, Lambda, IAM roles, DynamoDB, S3, SQS, Secrets Manager, EventBridge, and CloudWatch Logs

## One-time setup

```bash
cd infra/terraform
terraform init -input=false
```

Copy variables (optional—defaults exist):

```bash
cp examples/demo.tfvars my.tfvars
# edit project_name / aws_region if desired
terraform apply -input=false -var-file=my.tfvars
```

**Save outputs** (invoke URL, queue names):

```bash
terraform output -json > ../../outputs.json
```

## Phase 1 — Verify API, Lambda, DynamoDB, S3

### 1) HTTP health check

After `apply`, read the invoke URL:

```bash
terraform output -raw api_invoke_url
```

Call health (note: no trailing slash required):

```bash
curl -sS "$(terraform output -raw api_invoke_url)health" | jq .
```

**Expected**: HTTP `200`, JSON containing `"status": "ok"`.

**Optional — enqueue via HTTP (Phase 2)**

```bash
curl -sS -X POST "$(terraform output -raw api_invoke_url)enqueue" \
  -H 'Content-Type: application/json' \
  -d '{"source":"manual-runbook","note":"hello"}' | jq .
```

**Expected**: HTTP `202` and JSON indicating the message was enqueued. Confirm the ingest worker logs show the payload.

### 2) CloudWatch Logs (API Lambda)

1. AWS Console → **Lambda** → function named like `{project}-api`.
2. **Monitor** → **View CloudWatch Logs**.
3. Invoke `/health` again; confirm a new log stream and log lines.

### 3) DynamoDB

1. Console → **DynamoDB** → **Tables** → `{project}-metadata-*`.
2. **Explore table items** → you should see `PK=HEALTH`, `SK=CHECK` after hitting `/health`.

CLI:

```bash
aws dynamodb scan --table-name "$(terraform output -raw dynamodb_table_name)" --max-items 5
```

### 4) S3

```bash
aws s3api head-bucket --bucket "$(terraform output -raw s3_bucket_name)"
```

(Optional) Upload a test object via Console or CLI to confirm access patterns later used by ingestion.

### 5) API Gateway

Console → **API Gateway** → **APIs** → HTTP API type → routes show `GET /health` → **Stages** → `$default` → copy invoke URL (should match Terraform output).

---

## Phase 2 — Verify Secrets Manager and SQS

### 1) Secrets exist (placeholders)

Console → **Secrets Manager** → secrets named with `{project}-` prefix.

**Important**: Do **not** put real OAuth secrets in `.tfvars`. Update secret **values** in the Console or:

```bash
aws secretsmanager put-secret-value --secret-id <arn> --secret-string '{"client_id":"..."}'
```

### 2) SQS ingest + DLQ

Console → **SQS** → two queues: ingest and DLQ.

**Send a test message** (Console **Send and receive messages**) with body `hello-mailmanager`.

### 3) Worker Lambda logs

Open **Lambda** `{project}-ingest-worker` → CloudWatch Logs. You should see the message body logged and the message **removed** from the main queue on success.

### 4) Automated smoke script

From repo root (after `apply`):

```bash
export AWS_REGION=us-east-1   # match your deployment
export QUEUE_NAME_PREFIX=my-mailmanager   # match project_name in tfvars
./scripts/smoke_phase2.sh
```

---

## Phase 3 — EventBridge schedule (optional)

By default **`enable_scheduled_sync=false`**: the EventBridge rule exists in **DISABLED** state and will not run on schedule.

### Enable for a demo

```bash
terraform apply -input=false -var-file=examples/demo.tfvars -var='enable_scheduled_sync=true'
```

Wait for the schedule (default `rate(24 hours)` is slow). For a quicker test, temporarily set `schedule_expression` to `rate(5 minutes)` in a private `tfvars` (not committed), apply, watch **CloudWatch Logs** for `{project}-schedule-stub`.

### Disable again

```bash
terraform apply -input=false -var-file=examples/demo.tfvars -var='enable_scheduled_sync=false'
```

Console → **EventBridge** → **Rules** → confirm **State** is **Disabled**.

---

## Teardown (must work for class billing)

```bash
cd infra/terraform
terraform destroy -input=false -var-file=examples/demo.tfvars
```

Confirm:

- API Gateway APIs list no longer shows the HTTP API (or it is gone).
- S3 bucket deleted (empty or `force_destroy` cleared it).
- DynamoDB table deleted.
- SQS queues deleted.
- Secrets deleted (if destroy succeeded fully).

If destroy fails on a secret or bucket, read the error: empty the bucket or remove **deletion protection** (not enabled in this prototype), then re-run `destroy`.

---

## Common failures

| Symptom | Likely cause | What to do |
|---------|----------------|------------|
| `403` from `curl` | Wrong URL path | Use `{invoke_url}health` exactly (`invoke_url` already ends with `/` in output). |
| Lambda timeout | Cold start + VPC (if you added VPC later) | Increase timeout or remove VPC for API Lambda. |
| SQS redrives to DLQ | Worker throws repeatedly | Check worker logs; fix message format or handler. |
| Bedrock `AccessDenied` | Model access / IAM not set | See [architecture.md](architecture.md) Bedrock section—Console model access + future IAM policy. |
