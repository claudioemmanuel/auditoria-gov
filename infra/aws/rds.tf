resource "aws_db_subnet_group" "main" {
  name       = "${var.project_name}-db"
  subnet_ids = aws_subnet.private[*].id

  tags = { Name = "${var.project_name}-db-subnet" }
}

resource "aws_db_parameter_group" "postgres17" {
  family = "postgres17"
  name   = "${var.project_name}-pg17"

  parameter {
    name  = "work_mem"
    value = "8192"
  }

  parameter {
    name  = "max_connections"
    value = "30"
  }

  parameter {
    name         = "shared_preload_libraries"
    value        = "pg_stat_statements"
    apply_method = "pending-reboot"
  }

  parameter {
    name  = "log_min_duration_statement"
    value = "10000"
  }
}

resource "aws_db_instance" "postgres" {
  identifier     = var.project_name
  engine         = "postgres"
  engine_version = "17"
  instance_class = "db.t3.micro"

  allocated_storage     = 20
  max_allocated_storage = 30
  storage_type          = "gp3"

  db_name  = "auditoria"
  username = "auditoria"
  password = var.db_password

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  parameter_group_name   = aws_db_parameter_group.postgres17.name

  publicly_accessible     = false
  skip_final_snapshot     = true
  deletion_protection     = false
  backup_retention_period = 7
  backup_window           = "06:00-07:00"
  maintenance_window      = "sun:07:00-sun:08:00"

  tags = { Name = "${var.project_name}-db" }
}
