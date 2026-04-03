resource "aws_elasticache_subnet_group" "main" {
  name       = "${var.project_name}-redis"
  subnet_ids = aws_subnet.private[*].id
}

# Replication group (single node) — required for transit + at-rest encryption.
# aws_elasticache_cluster does not support encryption; replication group with
# num_cache_clusters=1 is functionally equivalent to a single-node cluster.
resource "aws_elasticache_replication_group" "redis" {
  replication_group_id = "${var.project_name}-redis"
  description          = "${var.project_name} Redis cache"

  engine         = "redis"
  engine_version = "7.1"
  node_type      = "cache.t3.micro"

  num_cache_clusters = 1  # single primary, no replicas

  subnet_group_name  = aws_elasticache_subnet_group.main.name
  security_group_ids = [aws_security_group.redis.id]

  transit_encryption_enabled = true
  at_rest_encryption_enabled = true
  # auth_token requires transit_encryption_enabled; set redis_password in tfvars.
  auth_token = var.redis_password != "" ? var.redis_password : null

  snapshot_retention_limit = 0

  tags = { Name = "${var.project_name}-redis" }
}
