# AWS infrastructure and push-to-deploy setup

This Terraform configuration creates exactly the services needed for the
assignment:

- one EC2 instance running the existing Docker Compose application;
- a private, versioned S3 bucket for frontend files and immutable release
  bundles;
- CloudFront with a default HTTPS URL, private S3 origin access control, and
  `/api/*` plus `/feedback-api/*` routing to EC2;
- IAM roles for the EC2 instance and GitHub Actions OIDC;
- a security group that admits HTTP origin traffic only from CloudFront;
- a monthly $5 forecasted-cost alert at 80%.

It deliberately does **not** create EKS, RDS, NAT Gateway, an ALB, a custom
domain, or a public database port.

## One-time bootstrap

Terraform must be applied once from an AWS-authenticated machine because the
GitHub Actions OIDC role does not exist until Terraform creates it. This is the
only infrastructure operation that is not a normal push-to-deploy release.

`terraform.tfvars` contains identifiers and an alert email only; it never
contains passwords or AWS keys.

```powershell
cd infra
Copy-Item terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars: set github_repository and budget_alert_email.
terraform init
terraform fmt -recursive
terraform validate
terraform plan
terraform apply
```

`terraform init` downloads the declared providers. `plan` shows the exact AWS
resources Terraform will create; review it before `apply` creates anything.

After apply, record these non-secret outputs:

```powershell
terraform output frontend_url
terraform output github_actions_role_arn
```

## GitHub configuration

Create a GitHub Environment named `production`, then add these **environment
variables**:

| Variable | Value |
|---|---|
| `AWS_REGION` | Same region used in `terraform.tfvars`, for example `ap-south-1` |
| `PROJECT_NAME` | `triageiq`, unless you changed it in Terraform |
| `ENVIRONMENT` | `prod`, unless you changed it in Terraform |
| `AWS_DEPLOY_ROLE_ARN` | `terraform output -raw github_actions_role_arn` |

Add these **environment secrets**. Never add them to a file or commit them:

| Secret | Purpose |
|---|---|
| `POSTGRES_PASSWORD` | Database password used only inside the Compose network |
| `GATEWAY_HTPASSWD` | Apache htpasswd hash for the reviewer gateway |
| `GRAFANA_ADMIN_PASSWORD` | Local observability dashboard password |
| `SMOKE_PASSWORD` | Password paired with the fixed `smoke` user for automated smoke checks |

Create the gateway hash locally, then paste only the generated hash into the
GitHub secret:

```powershell
docker run --rm httpd:2.4-alpine htpasswd -nbB smoke "choose-a-long-password"
```

The command runs the `htpasswd` utility in a temporary Docker container. It
prints a `username:hash` line; save the **entire line** in `GATEWAY_HTPASSWD`
and save the original password in `SMOKE_PASSWORD`.

## Automatic releases

After the one-time setup, every push to `main` runs `.github/workflows/ci.yml`
and `.github/workflows/deploy.yml`:

1. CI lints, tests, validates Compose, builds images, and performs secret,
   dependency, SAST, and filesystem vulnerability scans.
2. The deploy workflow trains the baseline model, uploads the static frontend
   to S3, invalidates CloudFront, uploads the commit-specific backend bundle,
   and asks EC2 to deploy it through Systems Manager.
3. The EC2 script reads secrets from Parameter Store, persists PostgreSQL on its
   Docker volume, starts only the lean app services, and checks gateway/model
   health before the workflow succeeds.

Do not run `docker compose down -v` on EC2: it removes the PostgreSQL volume.
The deployment uses `docker compose up -d --build` and preserves that volume.

## Cost guardrails

Use an instance type that AWS marks Free Tier eligible for the actual account.
The application is memory-intensive, so `t3.small` is the starting point, not
`t3.micro`. The Terraform budget is an alert, not a hard spending cap. Keep the
CloudFront default domain instead of buying a domain, and delete the stack with
`terraform destroy` when the assignment is no longer being demonstrated.
