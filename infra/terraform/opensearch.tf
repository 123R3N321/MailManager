resource "aws_opensearch_domain" "email_vector_db" {
  domain_name    = "mailmanager-vectors"
  engine_version = "OpenSearch_2.11"

  cluster_config {
    instance_type  = "t3.small.search"
    instance_count = 1
  }

  ebs_options {
    ebs_enabled = true
    volume_size = 10
  }

  encrypt_at_rest {
    enabled = true
  }

  node_to_node_encryption {
    enabled = true
  }

  domain_endpoint_options {
    enforce_https       = true
    tls_security_policy = "Policy-Min-TLS-1-2-2019-07"
  }

  # Embedding the policy here prevents the "List vs Object" API error
  access_policies = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "AllowLocalVerification"
        Action    = "es:*"
        Principal = "*"
        Effect    = "Allow"
        Resource  = "arn:aws:es:us-east-1:377100338169:domain/mailmanager-vectors/*"
        Condition = {
          IpAddress = {
            "aws:SourceIp" = ["72.79.57.110/32"]
          }
        }
      },
      {
        Sid       = "AllowAPILambdaRead"
        Action    = "es:*"
        Principal = {
          "AWS": "arn:aws:iam::377100338169:role/mailmanager-demo-9f53-api-lambda"
        }
        Effect    = "Allow"
        Resource  = "arn:aws:es:us-east-1:377100338169:domain/mailmanager-vectors/*"
      },
      {
        Sid       = "AllowIngestWorkerWrite"
        Action    = ["es:ESHttpPut", "es:ESHttpPost"]
        Principal = {
          "AWS": "arn:aws:iam::377100338169:role/mailmanager-demo-9f53-ingest-worker-lambda"
        }
        Effect    = "Allow"
        Resource  = "arn:aws:es:us-east-1:377100338169:domain/mailmanager-vectors/*"
      }
    ]
  })
}