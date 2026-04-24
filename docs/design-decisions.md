# Design decisions (ADR-style)

Short records of **why** the infrastructure is shaped this way. Supersedes informal chat when tradeoffs matter for grading or handoff.

---

## ADR-001: Single Terraform root, local state

**Context**

- Academic project with **low traffic** and need to **destroy quickly** to control cost.

**Decision**

- One root module in [`infra/terraform/`](../infra/terraform/).
- **Local** `terraform.tfstate` (not committed); no S3+DynamoDB remote state in v1.

**Consequences**

- **Pros**: simplest workflow; no extra state bucket to manage; fast teardown.
- **Cons**: state file must be **backed up manually** if you need recovery; team merges require coordination.

---

## ADR-002: API Gateway HTTP API (v2), not REST API (v1)

**Context**

- Need a public HTTPS endpoint for a future SPA and Lambda backend.

**Decision**

- Use **HTTP API** (`aws_apigatewayv2_*`) with Lambda proxy integration.

**Consequences**

- **Pros**: lower cost and simpler configuration than REST API v1 for this use case.
- **Cons**: fewer edge features than REST API v1; acceptable for the prototype.

---

## ADR-003: No VPC for Lambda by default

**Context**

- NAT Gateways and VPC Lambda attachments are common **student bill surprises**.

**Decision**

- Lambdas run in the **AWS-managed default network** (no VPC attachment) unless a future requirement forces VPC (for example RDS in-VPC).

**Consequences**

- **Pros**: minimal networking cost and simpler Terraform.
- **Cons**: if later you add **RDS inside a VPC**, Lambdas that query RDS will need VPC config + (often) **VPC endpoints** or NAT—plan that as a separate ADR.

---

## ADR-004: DynamoDB on-demand

**Context**

- Metadata volume is tiny for demos; traffic is negligible.

**Decision**

- `PAY_PER_REQUEST` billing mode.

**Consequences**

- **Pros**: no capacity planning; scales to near-zero usage cost.
- **Cons**: per-request pricing; still fine at demo scale.

---

## ADR-005: S3 `force_destroy` on the raw-mail bucket

**Context**

- `terraform destroy` fails if buckets are non-empty.

**Decision**

- Set `force_destroy = true` on the artifacts bucket used for prototypes.

**Consequences**

- **Pros**: reliable teardown for class demos.
- **Cons**: accidental `destroy` deletes objects—acceptable for non-production prototypes; do not store irreplaceable data.

---

## ADR-006: Secrets Manager placeholders in Terraform

**Context**

- OAuth client secrets must not live in git.

**Decision**

- Terraform creates **secret resources** and an initial **placeholder** secret string; operators **overwrite** values in Secrets Manager after apply.

**Consequences**

- **Pros**: no secrets in `.tfvars`; rotation story is “replace in console”.
- **Cons**: placeholder briefly exists in state for the initial version—replace before any real integration.

---

## ADR-007: EventBridge schedule disabled by default

**Context**

- Scheduled sync is easy to leave on and generate unnecessary invocations or provider API usage.

**Decision**

- Variable `enable_scheduled_sync` defaults to `false`; rule **state** is `DISABLED` until enabled.

**Consequences**

- **Pros**: predictable bills; explicit opt-in for recurring work.
- **Cons**: demo requires toggling variable or setting `true` in a dedicated `tfvars` for that session.
