variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project name (used for resource naming)"
  type        = string
  default     = "auditoria-gov"
}

variable "db_password" {
  description = "RDS PostgreSQL password"
  type        = string
  sensitive   = true
}

variable "redis_password" {
  description = "ElastiCache Redis AUTH token"
  type        = string
  sensitive   = true
  default     = ""
}

variable "cpf_hash_salt" {
  description = "LGPD CPF hash salt"
  type        = string
  sensitive   = true
}

variable "internal_api_key" {
  description = "Internal API authentication key"
  type        = string
  sensitive   = true
}

variable "portal_transparencia_token" {
  description = "Portal da Transparência API token"
  type        = string
  sensitive   = true
  default     = ""
}

variable "budget_email" {
  description = "Email for budget alerts"
  type        = string
}

variable "budget_ceiling_usd" {
  description = "Monthly budget ceiling in USD (triggers kill-switch)"
  type        = number
  default     = 20
}

variable "domain_name" {
  description = "Custom domain name (optional, leave empty for CloudFront default)"
  type        = string
  default     = ""
}

variable "certificate_arn" {
  description = "ACM certificate ARN for ALB HTTPS listener. Request via: aws acm request-certificate --domain-name api.yourdomain.com --validation-method DNS. Leave empty for HTTP-only (dev/first-run)."
  type        = string
  default     = ""
}

variable "api_desired_count" {
  description = "Desired count for API ECS service (0 to stop)"
  type        = number
  default     = 1
}

variable "enable_schedules" {
  description = "Enable EventBridge scheduled tasks"
  type        = bool
  default     = true
}

variable "api_cpu" {
  description = "API task CPU units (256 = 0.25 vCPU)"
  type        = number
  default     = 256
}

variable "api_memory" {
  description = "API task memory in MB"
  type        = number
  default     = 512
}

variable "worker_cpu" {
  description = "Worker task CPU units (512 = 0.5 vCPU)"
  type        = number
  default     = 512
}

variable "worker_memory" {
  description = "Worker task memory in MB"
  type        = number
  default     = 1024
}

variable "github_org" {
  description = "GitHub org/user for OIDC federation"
  type        = string
  default     = "claudioemmanuel"
}

variable "github_repo" {
  description = "GitHub repository name for OIDC federation"
  type        = string
  default     = "auditoria-gov"
}
