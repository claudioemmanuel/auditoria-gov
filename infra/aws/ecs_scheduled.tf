resource "aws_cloudwatch_event_rule" "pipeline_full" {
  count               = var.enable_schedules ? 1 : 0
  name                = "${var.project_name}-pipeline-full"
  description         = "Daily full pipeline: ingest → ER → baselines → signals → cases"
  schedule_expression = "cron(0 3 * * ? *)"
  state               = "ENABLED"
}

resource "aws_cloudwatch_event_target" "pipeline_full" {
  count     = var.enable_schedules ? 1 : 0
  rule      = aws_cloudwatch_event_rule.pipeline_full[0].name
  target_id = "pipeline-full"
  arn       = aws_ecs_cluster.main.arn
  role_arn  = aws_iam_role.eventbridge_ecs.arn

  ecs_target {
    task_definition_arn = aws_ecs_task_definition.worker.arn
    task_count          = 1
    launch_type         = "FARGATE"

    network_configuration {
      subnets          = aws_subnet.private[*].id
      security_groups  = [aws_security_group.ecs.id]
      assign_public_ip = false
    }
  }

  input = jsonencode({
    containerOverrides = [{
      name    = "worker"
      command = ["--run-pipeline", "--pipeline", "full"]
    }]
  })
}

resource "aws_cloudwatch_event_rule" "pipeline_bulk" {
  count               = var.enable_schedules ? 1 : 0
  name                = "${var.project_name}-pipeline-bulk"
  description         = "Daily bulk ingestion (TSE, Receita CNPJ)"
  schedule_expression = "cron(0 0 * * ? *)"
  state               = "ENABLED"
}

resource "aws_cloudwatch_event_target" "pipeline_bulk" {
  count     = var.enable_schedules ? 1 : 0
  rule      = aws_cloudwatch_event_rule.pipeline_bulk[0].name
  target_id = "pipeline-bulk"
  arn       = aws_ecs_cluster.main.arn
  role_arn  = aws_iam_role.eventbridge_ecs.arn

  ecs_target {
    task_definition_arn = aws_ecs_task_definition.worker.arn
    task_count          = 1
    launch_type         = "FARGATE"

    network_configuration {
      subnets          = aws_subnet.private[*].id
      security_groups  = [aws_security_group.ecs.id]
      assign_public_ip = false
    }
  }

  input = jsonencode({
    containerOverrides = [{
      name    = "worker"
      command = ["--run-pipeline", "--pipeline", "bulk"]
    }]
  })
}

resource "aws_cloudwatch_event_rule" "pipeline_maintenance" {
  count               = var.enable_schedules ? 1 : 0
  name                = "${var.project_name}-pipeline-maintenance"
  description         = "Weekly maintenance: cleanup, vacuum, coverage"
  schedule_expression = "cron(0 2 ? * SUN *)"
  state               = "ENABLED"
}

resource "aws_cloudwatch_event_target" "pipeline_maintenance" {
  count     = var.enable_schedules ? 1 : 0
  rule      = aws_cloudwatch_event_rule.pipeline_maintenance[0].name
  target_id = "pipeline-maintenance"
  arn       = aws_ecs_cluster.main.arn
  role_arn  = aws_iam_role.eventbridge_ecs.arn

  ecs_target {
    task_definition_arn = aws_ecs_task_definition.worker.arn
    task_count          = 1
    launch_type         = "FARGATE"

    network_configuration {
      subnets          = aws_subnet.private[*].id
      security_groups  = [aws_security_group.ecs.id]
      assign_public_ip = false
    }
  }

  input = jsonencode({
    containerOverrides = [{
      name    = "worker"
      command = ["--run-pipeline", "--pipeline", "maintenance"]
    }]
  })
}
