resource "aws_budgets_budget" "monthly" {
  name         = "${var.project_name}-monthly"
  budget_type  = "COST"
  limit_amount = tostring(var.budget_ceiling_usd)
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 75
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = [var.budget_email]
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 90
    threshold_type             = "PERCENTAGE"
    notification_type          = "FORECASTED"
    subscriber_email_addresses = [var.budget_email]
  }
}

resource "aws_cloudwatch_metric_alarm" "billing_killswitch" {
  provider            = aws.us_east_1
  alarm_name          = "${var.project_name}-budget-killswitch"
  alarm_description   = "Kill-switch: stops all services when spend exceeds $${var.budget_ceiling_usd}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "EstimatedCharges"
  namespace           = "AWS/Billing"
  period              = 21600
  statistic           = "Maximum"
  threshold           = var.budget_ceiling_usd
  treat_missing_data  = "notBreaching"

  dimensions = {
    Currency = "USD"
  }

  alarm_actions = [aws_sns_topic.alerts.arn]
}

data "archive_file" "killswitch" {
  type        = "zip"
  source_file = "${path.module}/lambda/budget_killswitch.py"
  output_path = "${path.module}/lambda/budget_killswitch.zip"
}

resource "aws_lambda_function" "budget_killswitch" {
  function_name    = "${var.project_name}-budget-killswitch"
  filename         = data.archive_file.killswitch.output_path
  source_code_hash = data.archive_file.killswitch.output_base64sha256
  handler          = "budget_killswitch.handler"
  runtime          = "python3.12"
  role             = aws_iam_role.budget_killswitch.arn
  timeout          = 60

  environment {
    variables = {
      ECS_CLUSTER    = aws_ecs_cluster.main.name
      ECS_SERVICE    = aws_ecs_service.api.name
      RDS_IDENTIFIER = aws_db_instance.postgres.identifier
      PROJECT_NAME   = var.project_name
    }
  }
}

resource "aws_sns_topic_subscription" "killswitch" {
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "lambda"
  endpoint  = aws_lambda_function.budget_killswitch.arn
}

resource "aws_lambda_permission" "sns" {
  statement_id  = "AllowSNS"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.budget_killswitch.function_name
  principal     = "sns.amazonaws.com"
  source_arn    = aws_sns_topic.alerts.arn
}
