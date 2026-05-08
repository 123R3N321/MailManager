## --- API Lambda (FastAPI/RAG Interface) ---
resource "aws_lambda_function" "api" {
  function_name = "${local.prefix}-api"
  role          = aws_iam_role.api_lambda.arn

  # MATCHES: 'def handler' in handler.py
  handler = "handler.handler"

  runtime     = "python3.12"
  timeout     = 30
  memory_size = 512

  filename         = data.archive_file.api_zip.output_path
  source_code_hash = data.archive_file.api_zip.output_base64sha256

  depends_on = [aws_cloudwatch_log_group.api]

  environment {
    variables = {
      TABLE_NAME     = aws_dynamodb_table.metadata.name
      BUCKET_NAME    = aws_s3_bucket.raw_mail.bucket
      QUEUE_URL      = aws_sqs_queue.ingest.url
      APP_AWS_REGION = var.aws_region

      # RAG Integration
      OPENSEARCH_URL = "https://${aws_opensearch_domain.email_vector_db.endpoint}"
      INDEX_NAME     = "mailmanager-index"
      BEDROCK_REGION = var.aws_region
      USE_BEDROCK    = "true"

      BEDROCK_MODEL_ID = "anthropic.claude-3-haiku-20240307-v1:0"
      # Using V1 to maintain compatibility with handler.py JSON structure
      EMBEDDING_MODEL_ID = "amazon.titan-embed-text-v1"
    }
  }
}

## --- Ingest Worker Lambda (Vectorization Engine) ---
resource "aws_lambda_function" "ingest_worker" {
  function_name = "${local.prefix}-ingest-worker"
  role          = aws_iam_role.ingest_worker_lambda.arn

  # MATCHES: 'def handler' in the worker code
  handler = "handler.handler"

  runtime     = "python3.12"
  timeout     = 60
  memory_size = 512

  filename         = data.archive_file.ingest_worker_zip.output_path
  source_code_hash = data.archive_file.ingest_worker_zip.output_base64sha256

  depends_on = [aws_cloudwatch_log_group.ingest_worker]

  environment {
    variables = {
      TABLE_NAME         = aws_dynamodb_table.metadata.name
      APP_AWS_REGION     = var.aws_region
      OPENSEARCH_URL     = "https://${aws_opensearch_domain.email_vector_db.endpoint}"
      INDEX_NAME         = "mailmanager-index"
      BEDROCK_REGION     = var.aws_region
      EMBEDDING_MODEL_ID = "amazon.titan-embed-text-v1"
    }
  }
}

## --- Schedule Stub Lambda (Maintenance) ---
resource "aws_lambda_function" "schedule_stub" {
  function_name = "${local.prefix}-schedule-stub"
  role          = aws_iam_role.schedule_stub_lambda.arn

  handler = "handler.handler"

  runtime     = "python3.12"
  timeout     = 10
  memory_size = 128

  filename         = data.archive_file.schedule_stub_zip.output_path
  source_code_hash = data.archive_file.schedule_stub_zip.output_base64sha256

  depends_on = [aws_cloudwatch_log_group.schedule_stub]
}

## --- Event Source Mapping (SQS -> Ingest Worker) ---
resource "aws_lambda_event_source_mapping" "ingest" {
  event_source_arn = aws_sqs_queue.ingest.arn
  function_name    = aws_lambda_function.ingest_worker.arn
  batch_size       = 5
  enabled          = true
}

## --- S3 Bucket Notification ---
## Temporarily disabled for the demo integration stack.
## Reason:
## AWS rejected the S3 -> SQS notification because the SQS queue policy
## does not currently allow S3 to send messages to the queue.
##
## This does NOT break the main app flow because demo ingestion happens
## through the API endpoint:
## POST /ingest/demo
##
## Re-enable later after adding an SQS queue policy that allows S3
## to publish ObjectCreated events to aws_sqs_queue.ingest.
#
# resource "aws_s3_bucket_notification" "mail_trigger" {
#   bucket = aws_s3_bucket.raw_mail.id
#
#   queue {
#     queue_arn = aws_sqs_queue.ingest.arn
#     events    = ["s3:ObjectCreated:*"]
#   }
# }
