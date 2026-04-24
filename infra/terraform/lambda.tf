resource "aws_lambda_function" "api" {
  function_name = "${local.prefix}-api"
  role          = aws_iam_role.api_lambda.arn
  handler       = "handler.handler"
  runtime       = "python3.12"
  timeout       = 15
  memory_size   = 128

  filename         = data.archive_file.api_zip.output_path
  source_code_hash = data.archive_file.api_zip.output_base64sha256

  depends_on = [aws_cloudwatch_log_group.api]

  environment {
    variables = {
      TABLE_NAME  = aws_dynamodb_table.metadata.name
      BUCKET_NAME = aws_s3_bucket.raw_mail.bucket
      QUEUE_URL   = aws_sqs_queue.ingest.url
    }
  }
}

resource "aws_lambda_function" "ingest_worker" {
  function_name = "${local.prefix}-ingest-worker"
  role          = aws_iam_role.ingest_worker_lambda.arn
  handler       = "handler.handler"
  runtime       = "python3.12"
  timeout       = 30
  memory_size   = 128

  filename         = data.archive_file.ingest_worker_zip.output_path
  source_code_hash = data.archive_file.ingest_worker_zip.output_base64sha256

  depends_on = [aws_cloudwatch_log_group.ingest_worker]
}

resource "aws_lambda_function" "schedule_stub" {
  function_name = "${local.prefix}-schedule-stub"
  role          = aws_iam_role.schedule_stub_lambda.arn
  handler       = "handler.handler"
  runtime       = "python3.12"
  timeout       = 10
  memory_size   = 128

  filename         = data.archive_file.schedule_stub_zip.output_path
  source_code_hash = data.archive_file.schedule_stub_zip.output_base64sha256

  depends_on = [aws_cloudwatch_log_group.schedule_stub]
}

resource "aws_lambda_event_source_mapping" "ingest" {
  event_source_arn = aws_sqs_queue.ingest.arn
  function_name    = aws_lambda_function.ingest_worker.arn
  batch_size       = 5
  enabled          = true
}
