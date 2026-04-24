# Non-secret demo values. Copy to `my.tfvars` (gitignored) if you customize further.
aws_region   = "us-east-1"
project_name = "mailmanager-demo"

# Keep false for class demos unless you explicitly want scheduled Lambda invocations.
enable_scheduled_sync = false
schedule_expression   = "rate(24 hours)"
