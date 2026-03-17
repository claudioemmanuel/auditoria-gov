# AWS Secrets Manager — stores all sensitive environment variables.
# The ECS execution role reads these at container startup via the "secrets" block
# in the task definition. Values are never stored in plaintext in the task definition.
resource "aws_secretsmanager_secret" "app" {
  name                    = "${var.project_name}/app-secrets"
  recovery_window_in_days = 0  # Allow immediate deletion for dev iteration
}

locals {
  redis_host = aws_elasticache_replication_group.redis.primary_endpoint_address
  # Use rediss:// (TLS) with optional AUTH token to match transit_encryption_enabled
  redis_url_prefix = var.redis_password != "" ? "rediss://:${var.redis_password}@${local.redis_host}" : "rediss://${local.redis_host}"
}

resource "aws_secretsmanager_secret_version" "app" {
  secret_id = aws_secretsmanager_secret.app.id

  secret_string = jsonencode({
    DATABASE_URL               = "postgresql+asyncpg://auditoria:${var.db_password}@${aws_db_instance.postgres.endpoint}/auditoria"
    DATABASE_URL_SYNC          = "postgresql+psycopg://auditoria:${var.db_password}@${aws_db_instance.postgres.endpoint}/auditoria"
    REDIS_URL                  = "${local.redis_url_prefix}:6379/0"
    CELERY_BROKER_URL          = "${local.redis_url_prefix}:6379/1"
    CELERY_RESULT_BACKEND      = "${local.redis_url_prefix}:6379/2"
    CPF_HASH_SALT              = var.cpf_hash_salt
    INTERNAL_API_KEY           = var.internal_api_key
    PORTAL_TRANSPARENCIA_TOKEN = var.portal_transparencia_token
  })
}

# Allow ECS execution role to fetch this secret at container startup
resource "aws_iam_role_policy" "ecs_execution_secrets" {
  name = "read-app-secrets"
  role = aws_iam_role.ecs_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = "secretsmanager:GetSecretValue"
      Resource = aws_secretsmanager_secret.app.arn
    }]
  })
}
