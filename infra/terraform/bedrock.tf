# Policy to allow Lambda to call Bedrock
resource "aws_iam_policy" "bedrock_access" {
  name        = "MailManagerBedrockAccess"
  description = "Allows Lambda to invoke Bedrock models for RAG"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "bedrock:InvokeModel"
        Effect = "Allow"
        Resource = [
          "arn:aws:bedrock:us-east-1:${data.aws_caller_identity.current.account_id}:inference-profile/us.anthropic.claude-haiku-4-5-20251001-v1:0",
          "arn:aws:bedrock:*::foundation-model/anthropic.claude-haiku-4-5-20251001-v1:0",
          "arn:aws:bedrock:us-east-1::foundation-model/amazon.titan-embed-text-v1"
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_bedrock" {
  role       = aws_iam_role.api_lambda.name
  policy_arn = aws_iam_policy.bedrock_access.arn
}
