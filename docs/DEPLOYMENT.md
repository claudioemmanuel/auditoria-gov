# Deploying OpenWatch on AWS

Step-by-step guide to deploy OpenWatch on AWS using ECS Fargate,
RDS PostgreSQL, ElastiCache Redis, and S3/CloudFront.

## Prerequisites

- AWS account with billing alerts enabled
- AWS CLI v2 configured (`aws configure`)
- Terraform >= 1.5 installed
- Docker installed (for building images)
- GitHub repository with Actions enabled
- Domain name (optional, but recommended)

## Architecture

```text
CloudFront --> S3 (static frontend)
ALB --> ECS Fargate (API service)
EventBridge --> ECS Fargate Tasks (workers, on-demand)
RDS PostgreSQL 17 + pgvector
ElastiCache Redis
CloudWatch + Lambda (budget kill-switch)
```

## Step 1: Configure Terraform Variables

```bash
cd infra/aws
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars`:
```hcl
aws_region           = "us-east-1"
project_name         = "openwatch"
db_password          = "generate-with-openssl-rand-hex-32"
redis_password       = "generate-with-openssl-rand-hex-32"
cpf_hash_salt        = "generate-with-openssl-rand-hex-32"
internal_api_key     = "generate-with-openssl-rand-hex-32"
budget_email         = "your-email@example.com"
budget_ceiling_usd   = 20
domain_name          = ""
portal_transparencia_token = "your-token"
```

## Step 2: Deploy Infrastructure

```bash
cd infra/aws
terraform init
terraform plan
terraform apply
```

Terraform outputs:
- `alb_dns_name` — API endpoint
- `cloudfront_url` — Frontend URL
- `ecr_api_repo` — ECR repository for API image
- `ecr_worker_repo` — ECR repository for worker image
- `rds_endpoint` — Database endpoint

## Step 3: Build & Push Docker Images

```bash
# Login to ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin <account>.dkr.ecr.us-east-1.amazonaws.com

# Build and push API
docker build -t auditoria-api -f api/Dockerfile .
docker tag auditoria-api:latest <ecr_api_repo>:latest
docker push <ecr_api_repo>:latest

# Build and push Worker
docker build -t auditoria-worker -f worker/Dockerfile .
docker tag auditoria-worker:latest <ecr_worker_repo>:latest
docker push <ecr_worker_repo>:latest
```

## Step 4: Build & Deploy Frontend

```bash
cd web
NEXT_PUBLIC_API_URL=https://<alb_dns_name> npm run build
aws s3 sync out/ s3://<frontend-bucket> --delete
aws cloudfront create-invalidation --distribution-id <dist_id> --paths "/*"
```

## Step 5: Run Database Migrations

```bash
aws ecs run-task \
  --cluster openwatch \
  --task-definition openwatch-api \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[<subnet>],securityGroups=[<sg>],assignPublicIp=DISABLED}" \
  --overrides '{"containerOverrides":[{"name":"api","command":["alembic","-c","api/alembic.ini","upgrade","head"]}]}'
```

## Step 6: Verify

- Frontend: visit CloudFront URL
- API health: `curl https://<alb_dns_name>/health`
- API docs: `https://<alb_dns_name>/docs`
- Trigger pipeline: `curl -X POST https://<alb_dns_name>/internal/ingest/all -H "X-Internal-Api-Key: <key>"`

## CI/CD (GitHub Actions)

After initial deploy, pushes to `main` automatically:
1. Build and push images to ECR
2. Update ECS API service
3. Run migrations via one-off task
4. Build frontend and sync to S3

### Required GitHub Secrets

| Secret | Source |
|--------|--------|
| `AWS_ROLE_ARN` | Terraform output: `github_actions_role_arn` |
| `AWS_REGION` | `us-east-1` |
| `ECR_API_REPO` | Terraform output: `ecr_api_repo` |
| `ECR_WORKER_REPO` | Terraform output: `ecr_worker_repo` |
| `ECS_CLUSTER` | Terraform output: `ecs_cluster_name` |
| `ECS_API_SERVICE` | Terraform output: `ecs_api_service_name` |
| `ECS_API_TASK_DEF` | `openwatch-api` |
| `ECS_NETWORK_CONFIG` | VPC config from Terraform |
| `API_URL` | Terraform output: `alb_dns_name` |
| `S3_BUCKET` | Terraform output: `frontend_bucket` |
| `CLOUDFRONT_DIST_ID` | Terraform output: `cloudfront_distribution_id` |

## Monitoring

- **CloudWatch Dashboard:** auto-created by Terraform
- **Budget Alerts:** email at $15 (warning), $18 (forecast), $20 (kill-switch)
- **Logs:** CloudWatch Logs at `/ecs/openwatch/*`

## Stopping Everything (Save Costs)

```bash
cd infra/aws
# Stop compute (keep data)
terraform apply -var="api_desired_count=0" -var="enable_schedules=false"
# Or destroy everything
terraform destroy
```

## Local Development

For local development, use Docker Compose instead:

```bash
cp .env.example .env
docker compose up --build
```

See [README.md](../README.md) for the full local development guide.
