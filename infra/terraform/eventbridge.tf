resource "aws_cloudwatch_event_rule" "sync_schedule" {
  name                = "${local.prefix}-sync-schedule"
  description         = "Optional periodic hook for mail sync demos (disabled by default)."
  schedule_expression = var.schedule_expression
  state               = var.enable_scheduled_sync ? "ENABLED" : "DISABLED"
}

resource "aws_cloudwatch_event_target" "sync_schedule_lambda" {
  rule = aws_cloudwatch_event_rule.sync_schedule.name
  arn  = aws_lambda_function.schedule_stub.arn
}

resource "aws_lambda_permission" "allow_eventbridge_schedule" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.schedule_stub.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.sync_schedule.arn
}
