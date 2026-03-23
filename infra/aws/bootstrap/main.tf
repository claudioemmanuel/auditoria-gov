# Bootstrap: creates S3 bucket + DynamoDB table for Terraform remote state.
#
# Run ONCE before the main infra/aws/ apply:
#   cd infra/aws/bootstrap
#   terraform init && terraform apply
#
# Then in infra/aws/main.tf, uncomment the backend "s3" block and run:
#   terraform init -migrate-state

terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project name (used for bucket/table naming)"
  type        = string
  default     = "openwatch"
}

provider "aws" {
  region = var.aws_region
}

resource "aws_s3_bucket" "tfstate" {
  bucket        = "${var.project_name}-tfstate"
  force_destroy = false

  tags = { Name = "${var.project_name}-tfstate", ManagedBy = "terraform-bootstrap" }
}

resource "aws_s3_bucket_versioning" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id
  rule {
    apply_server_side_encryption_by_default { sse_algorithm = "AES256" }
  }
}

resource "aws_s3_bucket_public_access_block" "tfstate" {
  bucket                  = aws_s3_bucket.tfstate.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_dynamodb_table" "tflock" {
  name         = "${var.project_name}-tflock"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "LockID"

  attribute {
    name = "LockID"
    type = "S"
  }

  tags = { Name = "${var.project_name}-tflock", ManagedBy = "terraform-bootstrap" }
}

output "backend_config" {
  description = "Paste this into infra/aws/main.tf backend block, then run: terraform init -migrate-state"
  value       = <<-EOT
    backend "s3" {
      bucket         = "${aws_s3_bucket.tfstate.bucket}"
      key            = "terraform.tfstate"
      region         = "${var.aws_region}"
      encrypt        = true
      dynamodb_table = "${aws_dynamodb_table.tflock.name}"
    }
  EOT
}
