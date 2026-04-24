resource "aws_sqs_queue" "ingest_dlq" {
  name = "${local.prefix}-ingest-dlq"
}

resource "aws_sqs_queue" "ingest" {
  name                       = "${local.prefix}-ingest"
  visibility_timeout_seconds = var.sqs_visibility_timeout_seconds
  receive_wait_time_seconds  = 0

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.ingest_dlq.arn
    maxReceiveCount     = var.sqs_max_receive_count
  })
}
