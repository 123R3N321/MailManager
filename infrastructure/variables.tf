variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "us-east-1"
}

variable "project" {
  description = "Short name prefix applied to every resource for easy identification and cleanup"
  type        = string
  default     = "gmail-ai-reply"
}

variable "dynamodb_table_name" {
  description = "DynamoDB table that stores email text + embedding vectors"
  type        = string
  default     = "gmail-ai-reply-emails"
}

variable "lambda_name" {
  description = "Lambda function name"
  type        = string
  default     = "gmail-ai-reply-api"
}

variable "claude_model_id" {
  description = "Bedrock model ID for reply generation (must be enabled in Model Access)"
  type        = string
  default     = "anthropic.claude-3-haiku-20240307-v1:0"
}

variable "titan_model_id" {
  description = "Bedrock model ID for text embeddings (must be enabled in Model Access)"
  type        = string
  default     = "amazon.titan-embed-text-v2:0"
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days (keeps demo costs near zero)"
  type        = number
  default     = 7
}
