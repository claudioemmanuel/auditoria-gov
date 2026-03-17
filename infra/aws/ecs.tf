resource "aws_ecs_cluster" "main" {
  name = var.project_name

  setting {
    name  = "containerInsights"
    value = "disabled"
  }
}

resource "aws_cloudwatch_log_group" "api" {
  name              = "/ecs/${var.project_name}/api"
  retention_in_days = 14
}

resource "aws_cloudwatch_log_group" "worker" {
  name              = "/ecs/${var.project_name}/worker"
  retention_in_days = 14
}

# Non-sensitive environment variables (safe to store in task definition)
locals {
  shared_env = [
    { name = "APP_ENV",      value = "production" },
    { name = "PYTHONPATH",   value = "/app" },
    { name = "LOG_LEVEL",    value = "INFO" },
    { name = "LLM_PROVIDER", value = "none" },
  ]

  # Sensitive variables fetched from Secrets Manager at container startup.
  # Format: { name = "ENV_VAR", valueFrom = "secret_arn:json_key::" }
  shared_secrets = [
    { name = "DATABASE_URL",               valueFrom = "${aws_secretsmanager_secret.app.arn}:DATABASE_URL::" },
    { name = "DATABASE_URL_SYNC",          valueFrom = "${aws_secretsmanager_secret.app.arn}:DATABASE_URL_SYNC::" },
    { name = "REDIS_URL",                  valueFrom = "${aws_secretsmanager_secret.app.arn}:REDIS_URL::" },
    { name = "CELERY_BROKER_URL",          valueFrom = "${aws_secretsmanager_secret.app.arn}:CELERY_BROKER_URL::" },
    { name = "CELERY_RESULT_BACKEND",      valueFrom = "${aws_secretsmanager_secret.app.arn}:CELERY_RESULT_BACKEND::" },
    { name = "CPF_HASH_SALT",              valueFrom = "${aws_secretsmanager_secret.app.arn}:CPF_HASH_SALT::" },
    { name = "INTERNAL_API_KEY",           valueFrom = "${aws_secretsmanager_secret.app.arn}:INTERNAL_API_KEY::" },
    { name = "PORTAL_TRANSPARENCIA_TOKEN", valueFrom = "${aws_secretsmanager_secret.app.arn}:PORTAL_TRANSPARENCIA_TOKEN::" },
  ]
}

resource "aws_ecs_task_definition" "api" {
  family                   = "${var.project_name}-api"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.api_cpu
  memory                   = var.api_memory
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([{
    name      = "api"
    image     = "${aws_ecr_repository.api.repository_url}:latest"
    essential = true

    portMappings = [{
      containerPort = 8000
      protocol      = "tcp"
    }]

    environment = concat(local.shared_env, [
      {
        name  = "ALLOWED_ORIGINS"
        value = var.domain_name != "" ? "https://${var.domain_name}" : "https://${aws_cloudfront_distribution.frontend.domain_name}"
      },
    ])

    # Sensitive values injected from Secrets Manager — never in plaintext task definition
    secrets = local.shared_secrets

    healthCheck = {
      command     = ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"]
      interval    = 30
      timeout     = 5
      retries     = 3
      startPeriod = 60
    }

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.api.name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "api"
      }
    }
  }])
}

resource "aws_ecs_task_definition" "worker" {
  family                   = "${var.project_name}-worker"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.worker_cpu
  memory                   = var.worker_memory
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([{
    name      = "worker"
    image     = "${aws_ecr_repository.worker.repository_url}:latest"
    essential = true

    command = ["--run-pipeline", "--pipeline", "full"]

    environment = local.shared_env

    # Sensitive values injected from Secrets Manager — never in plaintext task definition
    secrets = local.shared_secrets

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.worker.name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "worker"
      }
    }
  }])
}

resource "aws_ecs_service" "api" {
  name            = "${var.project_name}-api"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.api.arn
  desired_count   = var.api_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.api.arn
    container_name   = "api"
    container_port   = 8000
  }

  depends_on = [aws_lb_listener.http]
}
