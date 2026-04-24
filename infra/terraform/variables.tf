variable "aws_region" {
  type        = string
  description = "AWS region for all resources."
  default     = "us-east-1"
}

variable "project_name" {
  type        = string
  description = "Short lowercase name used in resource names (S3-safe subset)."
  default     = "mailmanager-demo"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{1,30}$", var.project_name))
    error_message = "project_name must start with a letter, be lowercase, and use only letters, digits, or hyphen (2-32 chars)."
  }
}

variable "environment" {
  type        = string
  description = "Tag value for Environment."
  default     = "demo"
}

variable "log_retention_days" {
  type        = number
  description = "CloudWatch log retention in days (keep low for class demos)."
  default     = 7
}

variable "enable_scheduled_sync" {
  type        = bool
  description = "When true, EventBridge rule invokes the schedule stub on schedule_expression."
  default     = false
}

variable "schedule_expression" {
  type        = string
  description = "EventBridge schedule (e.g. rate(24 hours)). Prefer long intervals for cost."
  default     = "rate(24 hours)"
}

variable "sqs_visibility_timeout_seconds" {
  type        = number
  description = "SQS visibility timeout; should be >= Lambda worker timeout."
  default     = 60
}

variable "sqs_max_receive_count" {
  type        = number
  description = "Messages delivered this many times without delete go to DLQ."
  default     = 3
}
