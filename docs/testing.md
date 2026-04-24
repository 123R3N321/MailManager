# Testing strategy

Tests are split into **Tier A** (always, no AWS apply), **Tier B** (optional static analysis), and **Tier C** (post-apply smoke, requires credentials).

## Tier A — Terraform static workflow (CI + local)

Run from repository root:

```bash
make tf-check
```

`tf-check` runs `terraform fmt -check`, `init`, and `validate` under [`infra/terraform/`](../infra/terraform/). It does **not** run `plan` (plan needs AWS credentials and refreshes remote state against your account).

**Full local validation including plan**

```bash
make tf-plan
```

Or manually:

```bash
cd infra/terraform
terraform init -input=false
terraform fmt -check -recursive
terraform validate
terraform plan -input=false -var-file=examples/demo.tfvars
```

**What “green” means**

- `fmt -check`: no formatting drift.
- `validate`: configuration is syntactically valid and internally consistent.
- `plan` (local): produces a plan without error against your credentials.

CI (GitHub Actions) runs **fmt + init + validate** only; see [`.github/workflows/terraform.yml`](../.github/workflows/terraform.yml).

## Tier B — Optional linters (local)

If installed on the developer machine:

- [tflint](https://github.com/terraform-linters/tflint)
- [tfsec](https://github.com/aquasecurity/tfsec) or [checkov](https://www.checkov.io/)

Example:

```bash
cd infra/terraform && tflint --minimum-failure-severity=warning
```

These are **not required** for the default Makefile target to pass.

## Tier C — Post-apply smoke tests

Requires:

- Valid AWS credentials (`AWS_PROFILE` or environment variables).
- Successful `terraform apply`.

**Phase 1**

- `curl` the `api_invoke_url` output (documented in [manual-runbook.md](manual-runbook.md)).

**Phase 2**

```bash
./scripts/smoke_phase2.sh
```

Set `API_URL` if you want an optional HTTP check; set `QUEUE_NAME_PREFIX` to match your `project_name` if non-default.

## When to run which tier

| Event | Tier A | Tier C |
|-------|--------|--------|
| Every commit / PR | Yes | Optional (if CI has AWS) |
| Before demo | Yes | Yes |
| After destroy | Yes | No |
