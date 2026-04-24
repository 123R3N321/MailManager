output "aws_region" {
  description = "Configured deployment region."
  value       = var.aws_region
}

output "api_invoke_url" {
  description = "Base URL for the HTTP API (append health or enqueue paths)."
  value       = "${aws_apigatewayv2_api.http.api_endpoint}/"
}

output "api_id" {
  value = aws_apigatewayv2_api.http.id
}

output "dynamodb_table_name" {
  value = aws_dynamodb_table.metadata.name
}

output "s3_bucket_name" {
  value = aws_s3_bucket.raw_mail.bucket
}

output "lambda_api_function_name" {
  value = aws_lambda_function.api.function_name
}

output "sqs_ingest_queue_url" {
  value = aws_sqs_queue.ingest.url
}

output "sqs_ingest_queue_name" {
  value = aws_sqs_queue.ingest.name
}

output "sqs_dlq_queue_url" {
  value = aws_sqs_queue.ingest_dlq.url
}

output "secrets_oauth_google_arn" {
  value = aws_secretsmanager_secret.oauth_google.arn
}

output "secrets_oauth_microsoft_arn" {
  value = aws_secretsmanager_secret.oauth_microsoft.arn
}

output "secrets_app_encryption_arn" {
  value = aws_secretsmanager_secret.app_encryption.arn
}

output "eventbridge_rule_name" {
  value = aws_cloudwatch_event_rule.sync_schedule.name
}

output "lambda_schedule_stub_function_name" {
  value = aws_lambda_function.schedule_stub.function_name
}

output "lambda_ingest_worker_function_name" {
  value = aws_lambda_function.ingest_worker.function_name
}
