resource "aws_cloudwatch_log_group" "api" {
  name              = "/aws/lambda/${local.prefix}-api"
  retention_in_days = var.log_retention_days
}

resource "aws_cloudwatch_log_group" "ingest_worker" {
  name              = "/aws/lambda/${local.prefix}-ingest-worker"
  retention_in_days = var.log_retention_days
}

resource "aws_cloudwatch_log_group" "schedule_stub" {
  name              = "/aws/lambda/${local.prefix}-schedule-stub"
  retention_in_days = var.log_retention_days
}
