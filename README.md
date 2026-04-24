# MailManager

Prototype infrastructure for an **AI-assisted email management** SaaS (summaries, drafts, inbox RAG). This repository currently provisions **AWS resources with Terraform** in phased milestones: HTTP API + Lambda, data stores, async ingestion, and optional scheduling—optimized for **class demos**, **low cost**, and **easy teardown**.

## Documentation

| Doc | Description |
|-----|-------------|
| [docs/architecture.md](docs/architecture.md) | Components, diagrams, external systems |
| [docs/design-decisions.md](docs/design-decisions.md) | ADRs (HTTP API, local state, no VPC, etc.) |
| [docs/phases.md](docs/phases.md) | Phase goals, exit criteria, destroy checklist |
| [docs/testing.md](docs/testing.md) | Automated vs manual tests |
| [docs/manual-runbook.md](docs/manual-runbook.md) | **How to deploy, verify, and destroy** (operators & graders) |
| [docs/future-bedrock-rds.md](docs/future-bedrock-rds.md) | Bedrock + optional RDS/pgvector extension notes |

## Quickstart

**Prerequisites**: Terraform `>= 1.6`, AWS CLI configured.

```bash
cd infra/terraform
terraform init -input=false
terraform apply -input=false -var-file=examples/demo.tfvars
terraform output api_invoke_url
curl -sS "$(terraform output -raw api_invoke_url)health" | jq .
```

**Quick verify** (after apply; run from `infra/terraform`, then the smoke script from repo root):

```bash
curl -sS "$(terraform output -raw api_invoke_url)health" | jq .
curl -sS -X POST "$(terraform output -raw api_invoke_url)enqueue" -H 'Content-Type: application/json' -d '{"demo":true}' | jq .
cd ../.. && API_URL="$(cd infra/terraform && terraform output -raw api_invoke_url)" ./scripts/smoke_phase2.sh
```

**Destroy** (stop AWS charges):

```bash
terraform destroy -input=false -var-file=examples/demo.tfvars
```

From repo root you can use `make tf-check` (see [docs/testing.md](docs/testing.md)).

## Repository layout

- [`infra/terraform/`](infra/terraform/) — Terraform **root module** (local state by default; do not commit `terraform.tfstate`)
- [`scripts/`](scripts/) — helper and smoke scripts
- [`.github/workflows/terraform.yml`](.github/workflows/terraform.yml) — CI for `fmt` + `validate` (+ optional `plan` with secrets)

## State file

This project uses **local Terraform state**. Back up `infra/terraform/terraform.tfstate` if you need recovery after accidental deletion.

Commit [`infra/terraform/.terraform.lock.hcl`](infra/terraform/.terraform.lock.hcl) so teammates and CI resolve the same provider versions.
