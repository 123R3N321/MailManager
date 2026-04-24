# Phase plan (infrastructure)

This document tracks what each phase delivers, exit criteria, and how it maps to coursework demos.

## Goals (all phases)

- One Terraform root under [`infra/terraform/`](../infra/terraform/) so **`terraform destroy`** removes provisioned AWS resources (plus documented external OAuth console steps, which are not AWS billable).
- **Demo over robustness**: low traffic, no high availability requirements.
- **Cost guardrails**: no NAT Gateway, no VPC-by-default, no Amazon OpenSearch in v1, no always-on containers.

## Non-goals (v1)

- Production-grade multi-tenant isolation, SOC2 controls, full abuse prevention.
- Full Gmail/Outlook sync implementation (application code); this repository focuses on **Terraform primitives** and runbooks.

---

## Phase 0 — Scope and conventions

**Deliverables**

- Documentation skeleton: architecture, design decisions, testing strategy, manual runbook, this phase file.

**Exit criteria**

- A reader can explain what will be built, what is deferred, and how to tear down safely.

**Tests**

- Documentation review only.

---

## Phase 1 — Foundation (HTTP API + Lambda + DynamoDB + S3)

**Deliverables**

- Amazon API Gateway **HTTP API** with `GET /health`.
- **Lambda** (Python) proving DynamoDB write on health check and returning JSON.
- **DynamoDB** table (`PK`, `SK`, on-demand billing).
- **S3** bucket for raw mail artifacts with `force_destroy` for easy teardown.
- Explicit **CloudWatch** log groups for Lambdas.

**Exit criteria**

- `curl` against the invoke URL returns HTTP 200 and JSON.
- DynamoDB shows a health-check item after calling `/health`.
- `terraform destroy` removes the stack.

**Tests**

- Automated: `terraform fmt`, `validate`, `plan` (see [testing.md](testing.md)).
- Manual: [manual-runbook.md](manual-runbook.md) Phase 1 section.

---

## Phase 2 — Secrets placeholders + ingestion queue

**Deliverables**

- **AWS Secrets Manager** secrets with **placeholder** values (replace via Console/CLI for real OAuth later).
- **SQS** ingest queue + **DLQ** with redrive policy.
- **Ingest worker Lambda** subscribed to the queue (logs bodies; deletes messages on success).
- **IAM**: API Lambda may publish to the ingest queue (for future app use); worker consumes from the queue.

**Exit criteria**

- Sending a message to the ingest queue results in worker logs and the message leaving the main queue (or landing in DLQ on repeated failure—documented separately).

**Tests**

- Automated: same Tier A as Phase 1.
- Manual / smoke: [`scripts/smoke_phase2.sh`](../scripts/smoke_phase2.sh).

---

## Phase 3 — Scheduling hook (off by default)

**Deliverables**

- **Amazon EventBridge** rule on a schedule expression, default **DISABLED** via `enable_scheduled_sync` (no surprise invocations).
- **Schedule stub Lambda** invoked by EventBridge when the rule is enabled.

**Exit criteria**

- With `enable_scheduled_sync=false`, the rule exists but does not invoke on schedule.
- With `enable_scheduled_sync=true`, scheduled invocations appear in CloudWatch Logs.

**Tests**

- `terraform plan` diff for toggling the variable (documented).
- Manual: runbook Phase 3 section.

---

## Phase 4+ — Application and AI (roadmap)

**Documented now; Terraform optional later**

- **Amazon Bedrock** and optional **RDS PostgreSQL + pgvector**: see [future-bedrock-rds.md](future-bedrock-rds.md) and [architecture.md](architecture.md).

---

## Destroy checklist

1. Run `terraform destroy` from [`infra/terraform/`](../infra/terraform/) (or `make destroy`).
2. Confirm S3 buckets empty or `force_destroy` removed bucket.
3. In AWS Console **Resource Groups** or **Tag Editor**, search for your `project_name` tag; ensure no stray resources.
4. OAuth apps (Google Cloud / Microsoft Entra) are **external**: disable or delete test apps if you created them for class.
