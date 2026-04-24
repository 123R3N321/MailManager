.PHONY: terraform-fmt terraform-init terraform-validate terraform-plan tf-check tf-plan

TF_DIR := infra/terraform
VAR_FILE := examples/demo.tfvars

terraform-fmt:
	cd $(TF_DIR) && terraform fmt -recursive

terraform-init:
	cd $(TF_DIR) && terraform init -input=false

terraform-validate: terraform-init
	cd $(TF_DIR) && terraform validate

terraform-plan: terraform-init
	cd $(TF_DIR) && terraform plan -input=false -var-file=$(VAR_FILE)

# Tier A checks suitable for CI (no AWS API calls required for validate).
tf-check:
	cd $(TF_DIR) && terraform fmt -check -recursive
	cd $(TF_DIR) && terraform init -input=false
	cd $(TF_DIR) && terraform validate

# Full local check including plan (may require valid AWS credentials).
tf-plan: terraform-fmt terraform-plan
