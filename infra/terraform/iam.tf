data "aws_iam_policy_document" "lambda_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "api_lambda" {
  name               = "${local.prefix}-api-lambda"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
}

data "aws_iam_policy_document" "api_lambda" {
  statement {
    sid = "Logs"
    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
    resources = ["${aws_cloudwatch_log_group.api.arn}:*"]
  }

  statement {
    sid = "DynamoDB"
    actions = [
      "dynamodb:GetItem",
      "dynamodb:PutItem",
      "dynamodb:Scan",
      "dynamodb:Query",
      "dynamodb:UpdateItem",
      "dynamodb:BatchWriteItem",
    ]
    resources = [aws_dynamodb_table.metadata.arn]
  }

  statement {
    sid = "S3WriteHealth"
    actions = [
      "s3:PutObject",
      "s3:GetObject",
      "s3:ListBucket",
    ]
    resources = [
      aws_s3_bucket.raw_mail.arn,
      "${aws_s3_bucket.raw_mail.arn}/*",
    ]
  }

  statement {
    sid = "SecretsRead"
    actions = [
      "secretsmanager:GetSecretValue",
    ]
    resources = [
      aws_secretsmanager_secret.oauth_google.arn,
      aws_secretsmanager_secret.oauth_microsoft.arn,
      aws_secretsmanager_secret.app_encryption.arn,
    ]
  }

  statement {
    sid = "SqsSend"
    actions = [
      "sqs:SendMessage",
    ]
    resources = [aws_sqs_queue.ingest.arn]
  }
}

resource "aws_iam_role_policy" "api_lambda" {
  name   = "inline"
  role   = aws_iam_role.api_lambda.id
  policy = data.aws_iam_policy_document.api_lambda.json
}

resource "aws_iam_role" "ingest_worker_lambda" {
  name               = "${local.prefix}-ingest-worker"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
}

data "aws_iam_policy_document" "ingest_worker_lambda" {
  statement {
    sid = "Logs"
    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
    resources = ["${aws_cloudwatch_log_group.ingest_worker.arn}:*"]
  }

  statement {
    sid = "SqsConsume"
    actions = [
      "sqs:ReceiveMessage",
      "sqs:DeleteMessage",
      "sqs:GetQueueAttributes",
      "sqs:ChangeMessageVisibility",
    ]
    resources = [aws_sqs_queue.ingest.arn]
  }
}

resource "aws_iam_role_policy" "ingest_worker_lambda" {
  name   = "inline"
  role   = aws_iam_role.ingest_worker_lambda.id
  policy = data.aws_iam_policy_document.ingest_worker_lambda.json
}

resource "aws_iam_role" "schedule_stub_lambda" {
  name               = "${local.prefix}-schedule-stub"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
}

data "aws_iam_policy_document" "schedule_stub_lambda" {
  statement {
    sid = "Logs"
    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
    resources = ["${aws_cloudwatch_log_group.schedule_stub.arn}:*"]
  }
}

resource "aws_iam_role_policy" "schedule_stub_lambda" {
  name   = "inline"
  role   = aws_iam_role.schedule_stub_lambda.id
  policy = data.aws_iam_policy_document.schedule_stub_lambda.json
}
