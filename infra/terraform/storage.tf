resource "aws_s3_bucket" "raw_mail" {
  bucket = "${local.prefix}-raw-mail"

  force_destroy = true
}

resource "aws_s3_bucket_public_access_block" "raw_mail" {
  bucket = aws_s3_bucket.raw_mail.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "raw_mail" {
  bucket = aws_s3_bucket.raw_mail.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_dynamodb_table" "metadata" {
  name         = "${local.prefix}-metadata"
  billing_mode = "PAY_PER_REQUEST"

  hash_key  = "PK"
  range_key = "SK"

  attribute {
    name = "PK"
    type = "S"
  }

  attribute {
    name = "SK"
    type = "S"
  }
}
