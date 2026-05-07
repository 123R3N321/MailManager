# --- Common Assume Role Policy ---
data "aws_iam_policy_document" "lambda_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

# --- 1. The API Role & Policies ---
resource "aws_iam_role" "api_lambda" {
  name               = "${local.prefix}-api-lambda"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
}

resource "aws_iam_role_policy" "api_lambda_permissions" {
  name = "${local.prefix}-api-lambda-policy"
  role = aws_iam_role.api_lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "Logs"
        Effect   = "Allow"
        Action   = ["logs:CreateLogStream", "logs:PutLogEvents"]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Sid      = "DynamoAccess"
        Effect   = "Allow"
        Action   = ["dynamodb:PutItem", "dynamodb:GetItem", "dynamodb:UpdateItem", "dynamodb:Query", "dynamodb:Scan"]
        Resource = ["${aws_dynamodb_table.metadata.arn}", "${aws_dynamodb_table.metadata.arn}/index/*"]
      },
      {
        Sid      = "S3Access"
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:PutObject", "s3:ListBucket"]
        Resource = ["${aws_s3_bucket.raw_mail.arn}", "${aws_s3_bucket.raw_mail.arn}/*"]
      },
      {
        Sid      = "BedrockAccess"
        Effect   = "Allow"
        # API needs to invoke Claude for RAG answers
        Action   = ["bedrock:InvokeModel"]
        Resource = "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0"
      },
      {
        Sid      = "OpenSearchRead"
        Effect   = "Allow"
        Action   = ["es:ESHttpPost", "es:ESHttpGet"]
        Resource = "${aws_opensearch_domain.email_vector_db.arn}/*"
      },
      {
        Sid      = "SqsProduce"
        Effect   = "Allow"
        Action   = ["sqs:SendMessage"]
        Resource = ["${aws_sqs_queue.ingest.arn}"]
      }
    ]
  })
}

# --- 2. The Ingest Worker Role & Policies ---
resource "aws_iam_role" "ingest_worker_lambda" {
  name               = "${local.prefix}-ingest-worker"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
}

resource "aws_iam_role_policy" "ingest_worker_permissions" {
  name = "${local.prefix}-ingest-worker-policy"
  role = aws_iam_role.ingest_worker_lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "Logs"
        Effect   = "Allow"
        Action   = ["logs:CreateLogStream", "logs:PutLogEvents"]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Sid      = "SqsConsume"
        Effect   = "Allow"
        Action   = ["sqs:ReceiveMessage", "sqs:DeleteMessage", "sqs:GetQueueAttributes", "sqs:ChangeMessageVisibility"]
        Resource = ["${aws_sqs_queue.ingest.arn}"]
      },
      {
        Sid      = "DynamoWrite"
        Effect   = "Allow"
        Action   = ["dynamodb:UpdateItem", "dynamodb:PutItem"]
        Resource = ["${aws_dynamodb_table.metadata.arn}"]
      },
      {
        Sid      = "BedrockEmbedding"
        Effect   = "Allow"
        # Worker needs to invoke Titan for embeddings
        Action   = ["bedrock:InvokeModel"]
        Resource = "arn:aws:bedrock:us-east-1::foundation-model/amazon.titan-embed-text-v1"
      },
      {
        Sid      = "OpenSearchWrite"
        Effect   = "Allow"
        Action   = ["es:ESHttpPost", "es:ESHttpPut", "es:ESHttpGet"]
        Resource = "${aws_opensearch_domain.email_vector_db.arn}/*"
      },
      {
        Sid      = "S3Read"
        Effect   = "Allow"
        Action   = ["s3:GetObject"]
        Resource = ["${aws_s3_bucket.raw_mail.arn}/*"]
      }
    ]
  })
}

# --- 3. The Schedule Stub Role ---
resource "aws_iam_role" "schedule_stub_lambda" {
  name               = "${local.prefix}-schedule-stub"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
}

resource "aws_iam_role_policy" "schedule_stub_logs" {
  name = "${local.prefix}-schedule-stub-logs"
  role = aws_iam_role.schedule_stub_lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["logs:CreateLogStream", "logs:PutLogEvents"]
      Resource = "arn:aws:logs:*:*:*"
    }]
  })
}
