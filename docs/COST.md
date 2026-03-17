# AuditorIA Gov — Infrastructure Cost Breakdown

Transparent breakdown of production infrastructure costs.
This project is designed to run within a $20/month ceiling on AWS.

## Monthly Costs (Active Usage)

| Service | Spec | Est. Cost |
|---------|------|-----------|
| RDS PostgreSQL | db.t3.micro, 20GB gp3 | ~$13 |
| ElastiCache Redis | cache.t3.micro | ~$12 |
| ECS Fargate (API) | 0.25 vCPU, 0.5GB, always-on | ~$5 |
| ECS Fargate (workers) | 0.5 vCPU, 1GB, ~2h/day on-demand | ~$1 |
| ALB | 1 LCU average | ~$16 |
| S3 + CloudFront | Static site, minimal traffic | ~$0.50 |
| ECR | <500MB images | $0 |
| EventBridge | <1M events/month | $0 |
| CloudWatch | Basic metrics + 5GB logs | $0 |
| **Total (active)** | | **~$15-20/mo** |
| **Total (idle)** | S3 + storage only | **~$1-2/mo** |

## Cost Optimization Options

| Optimization | Savings | Trade-off |
|-------------|---------|-----------|
| Replace ElastiCache with Fargate Valkey | ~$11/mo | Slightly higher latency, not managed |
| Replace ALB with API Gateway HTTP | ~$15/mo | 1M req/mo free tier, less flexible |
| Stop RDS when not ingesting | ~$8/mo | 15-min cold start on resume |
| Use Fargate Spot for workers | ~$0.50/mo | Possible interruption (tasks are idempotent) |

## Budget Guardrails

1. **CloudWatch Billing Alarm** at $15 — email notification
2. **AWS Budget** with forecast alert at $18
3. **Lambda kill-switch** at $20 — automatically:
   - Stops all ECS tasks (API + workers)
   - Stops RDS instance
   - Disables EventBridge schedules
   - Sends email alert
4. **Manual restart required** after kill-switch triggers

## Sponsor

Infrastructure costs are funded by community sponsors.
See [SPONSORS.md](../SPONSORS.md) for details.
