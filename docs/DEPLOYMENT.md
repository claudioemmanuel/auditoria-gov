# Deployment

## Local Development

See [README.md](../README.md#quick-start) for the full local setup guide.

**TL;DR:**
```bash
cp .env.example .env  # configure
make install
make dev              # starts postgres + redis
make migrate
uv run uvicorn api.app.main:app --reload --port 8000
```

## Docker Compose (staging / single-server)

```bash
# Copy and configure environment
cp .env.example .env
# Set APP_ENV=production, strong secrets, CORE_SERVICE_URL

# Start full public stack
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

# Check logs
docker compose logs -f api
```

The `docker-compose.prod.yml` override enables Caddy for TLS and disables the web container (frontend uses Vercel).

### Required `.env` values for production

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string |
| `REDIS_URL` | Redis connection string |
| `CPF_HASH_SALT` | Random hex string (LGPD compliance) |
| `INTERNAL_API_KEY` | Strong random key (`openssl rand -hex 32`) |
| `CORE_SERVICE_URL` | URL of running `openwatch-core` internal API |
| `CORE_API_KEY` | Shared key between public and core services |
| `ALLOWED_ORIGINS` | Comma-separated CORS allowed origins |
| `API_DOMAIN` | Domain for Caddy TLS (e.g. `api.yourdomain.com`) |

## Frontend (Vercel)

Deploy `apps/web/` to Vercel:

1. Connect the `openwatch` GitHub repository.
2. Set root directory to `apps/web`.
3. Set environment variable: `NEXT_PUBLIC_API_URL=https://api.yourdomain.com`
4. Deploy.

## AWS ECS (Production)

See the GitHub Actions workflow at `.github/workflows/deploy.yml`.

The workflow:
1. Builds and pushes the API Docker image to ECR
2. Deploys to ECS Fargate
3. Runs database migrations as a one-off ECS task
4. Deploys the frontend to Vercel (triggered via webhook)

### Infrastructure

AWS infrastructure is defined in Terraform inside `openwatch-core/infra/aws/`. It includes:
- VPC with public/private subnets
- ECS Fargate cluster
- RDS PostgreSQL (or Aurora)
- ElastiCache Redis
- ALB + HTTPS listener
- S3 + CloudFront for static assets
- Secrets Manager for sensitive config
- Budget guardrail + killswitch Lambda
