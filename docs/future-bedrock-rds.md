# Future work: Bedrock and optional RDS pgvector

This module intentionally **does not** provision Amazon Bedrock model access, OpenSearch, or RDS in v1. Use this document when extending the prototype toward **LLM summarization** and **semantic inbox search**.

## Amazon Bedrock

**Typical prerequisites (console)**

1. Pick an AWS **Region** where Bedrock exposes the chat and embedding models you want.
2. In the AWS Console, open **Amazon Bedrock** → **Model access** (or equivalent) and enable the models your account is allowed to use.
3. Attach an IAM policy to the invoking Lambda (least privilege), for example actions:
   - `bedrock:InvokeModel`
   - `bedrock:InvokeModelWithResponseStream` (only if you stream tokens)

**Terraform shape (later)**

- IAM policy documents referencing `arn:aws:bedrock:${region}::foundation-model/...` or inference profiles—**ARNs vary** by model and account features; validate in your target region before codifying.

**Manual test**

- From a one-off Lambda test harness or AWS CLI (where supported), invoke the same model ID you enabled in Console and confirm a JSON response.

## Optional RDS PostgreSQL + pgvector

**When to add**

- You need durable vector search beyond “tiny corpus in DynamoDB/S3,” and you accept **VPC + RDS** complexity and **instance-hour** cost.

**Suggested module contract (not implemented in v1)**

- Boolean input `enable_vector_db` default **`false`**.
- If `true`:
  - Create **VPC** subnets (public/private per your security story), **security groups**, and a small **RDS PostgreSQL** instance (for example `db.t4g.micro` where available).
  - Enable **`pgvector`** via `rds` parameter group or `CREATE EXTENSION` bootstrap (application migration).
  - Attach **Lambda VPC configuration** for functions that must query the database; add **VPC interface endpoints** (Secrets Manager, S3, DynamoDB, SQS) or **NAT**—**NAT is a common cost trap**; prefer endpoints for a class budget where possible.

**Manual test**

- `psql` from a bastion or **RDS Query Editor** (if used): `CREATE EXTENSION IF NOT EXISTS vector;`
- Insert a test embedding row and run a `<->` neighbor query.

**Operational note**

- RDS **stop/start** helps between demos but has service limits; do not rely on “stopped forever” for long periods.

## Cost reminder

Bedrock charges **per token**; RDS charges for **storage + instance hours**; NAT charges for **per-hour + data processing**. Keep features behind flags and document **destroy** paths in [manual-runbook.md](manual-runbook.md).
