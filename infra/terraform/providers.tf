provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "MailManager"
      Environment = var.environment
      ManagedBy   = "terraform"
      NamePrefix  = var.project_name
    }
  }
}
