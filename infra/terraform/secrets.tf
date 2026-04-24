resource "aws_secretsmanager_secret" "oauth_google" {
  name        = "${local.prefix}/oauth/google"
  description = "Placeholder for Gmail/Google OAuth client credentials (set value in Console)."
}

resource "aws_secretsmanager_secret_version" "oauth_google_placeholder" {
  secret_id     = aws_secretsmanager_secret.oauth_google.id
  secret_string = jsonencode({ placeholder = "replace-via-aws-console-or-cli" })
}

resource "aws_secretsmanager_secret" "oauth_microsoft" {
  name        = "${local.prefix}/oauth/microsoft"
  description = "Placeholder for Microsoft Graph OAuth client credentials (set value in Console)."
}

resource "aws_secretsmanager_secret_version" "oauth_microsoft_placeholder" {
  secret_id     = aws_secretsmanager_secret.oauth_microsoft.id
  secret_string = jsonencode({ placeholder = "replace-via-aws-console-or-cli" })
}

resource "aws_secretsmanager_secret" "app_encryption" {
  name        = "${local.prefix}/app/encryption-key"
  description = "Placeholder for application encryption material (replace for real workloads)."
}

resource "aws_secretsmanager_secret_version" "app_encryption_placeholder" {
  secret_id     = aws_secretsmanager_secret.app_encryption.id
  secret_string = jsonencode({ placeholder = "replace-via-aws-console-or-cli" })
}
