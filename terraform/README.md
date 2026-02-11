# Terraform

Infrastructure as Code (IaC) for deploying TrendFunnel on AWS.

## 🎯 Purpose

Provisions and manages all AWS infrastructure required for TrendFunnel:
- Database (RDS PostgreSQL)
- Compute (Lambda, ECS)
- Networking (VPC, Security Groups)
- Scheduling (EventBridge)
- Messaging (SES, SNS)
- Container Registry (ECR)

## 📁 Structure

```
terraform/
├── main.tf        # Main infrastructure definitions
└── variables.tf   # Input variable declarations
```

## 🏗️ Resources Provisioned

| Resource | Purpose |
|----------|---------|
| **RDS PostgreSQL** | Primary database for all application data |
| **ECR Repositories** | Container registries for Lambda/ECS images |
| **Lambda Functions** | Alert system, Google Trends, LLM summary, Weekly report |
| **ECS Cluster** | Bluesky pipeline and Dashboard hosting |
| **EventBridge Rules** | Scheduled triggers (5-min, daily, weekly) |
| **Security Groups** | Network access control for RDS, Lambda, ECS |
| **IAM Roles** | Execution roles for Lambda and ECS |
| **SES** | Email sending for alerts and reports |

## 🚀 Deployment

### Prerequisites

- Terraform 1.0+
- AWS CLI configured with appropriate credentials
- Existing VPC (referenced by ID)

### Variables

Create a `terraform.tfvars` file:

```hcl
aws_region           = "eu-west-2"
vpc_id               = "vpc-xxxxxxxx"
db_name              = "trendfunnel"
db_username          = "admin"
db_password          = "your-secure-password"
db_instance_class    = "db.t3.micro"
db_allocated_storage = 20
publicly_accessible  = true
environment          = "production"
openrouter_api_key   = "your-openrouter-key"
ses_sender_email     = "alerts@yourdomain.com"
```

### Deploy

```bash
# Initialize Terraform
terraform init

# Preview changes
terraform plan

# Apply infrastructure
terraform apply

# Destroy (when needed)
terraform destroy
```

## 🔧 Architecture Components

### Scheduling (EventBridge)

| Schedule | Target | Purpose |
|----------|--------|---------|
| Every 5 min | Alert Lambda | Spike detection |
| Daily | Google Trends Lambda | Search volume updates |
| Daily | LLM Summary Lambda | AI insights generation |
| Weekly | Report Lambda | Weekly email reports |

### Networking

- RDS in public subnets (configurable)
- Lambda functions with VPC access to RDS
- ECS tasks in private subnets with NAT gateway access

## 📝 Notes

- Use `terraform.tfvars` for sensitive values (add to `.gitignore`)
- State should be stored remotely (S3 + DynamoDB) for team use
- Consider using Terraform workspaces for dev/staging/prod
