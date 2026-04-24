locals {
  prefix = "${var.project_name}-${random_id.suffix.hex}"
}
