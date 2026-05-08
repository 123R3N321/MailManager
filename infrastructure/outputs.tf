output "api_url" {
  description = "Paste this URL into the Chrome extension Options page → AWS Backend (RAG)"
  value       = aws_apigatewayv2_stage.default.invoke_url
}

output "dynamodb_table" {
  description = "DynamoDB table storing email embeddings"
  value       = aws_dynamodb_table.email_store.name
}

output "lambda_function" {
  description = "Lambda function name (use for logs: aws logs tail /aws/lambda/<name> --follow)"
  value       = aws_lambda_function.api.function_name
}
