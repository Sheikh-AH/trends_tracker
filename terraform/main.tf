terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# VPC - specific
data "aws_vpc" "main" {
  id = var.vpc_id
}

data "aws_subnets" "public" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.main.id]
  }
  filter {
    name   = "tag:Name"
    values = ["*public*"]
  }
}

# Security Group for RDS
resource "aws_security_group" "rds_sg" {
  name        = "c21-trends-rds-sg"
  description = "Security group for Trends RDS"
  vpc_id      = data.aws_vpc.main.id

  ingress {
    description = "PostgreSQL from anywhere"
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "c21-trends-rds-sg"
    Environment = var.environment
  }
}

resource "aws_db_subnet_group" "trends_subnet_group" {
  name       = "c21-trends-subnet-group"
  subnet_ids = data.aws_subnets.public.ids

  tags = {
    Name        = "C21-Trends-DB-Subnet-Group"
    Environment = var.environment
  }
}

# RDS PostgreSQL Instance
resource "aws_db_instance" "trends_db" {
  identifier     = "c21-trends-db"
  engine         = "postgres"
  engine_version = "15"
  instance_class = var.db_instance_class

  allocated_storage     = var.db_allocated_storage
  max_allocated_storage = 100
  storage_type          = "gp2"

  db_name  = var.db_name
  username = var.db_username
  password = var.db_password

  db_subnet_group_name   = aws_db_subnet_group.trends_subnet_group.name
  vpc_security_group_ids = [aws_security_group.rds_sg.id]

  publicly_accessible = var.publicly_accessible
  skip_final_snapshot = true

  tags = {
    Name        = "c21-trends-db"
    Environment = var.environment
  }
}


# ECR Repository for Google Trends Pipeline
resource "aws_ecr_repository" "gt_pipeline" {
  name                 = "c21-gt-pipeline"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Name        = "c21-gt-pipeline"
    Environment = var.environment
  }
}

# IAM Role for Lambda
resource "aws_iam_role" "gt_lambda_role" {
  name = "c21-gt-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name        = "c21-gt-lambda-role"
    Environment = var.environment
  }
}

# IAM Policy for Lambda (CloudWatch Logs + ECR + VPC)
resource "aws_iam_role_policy" "gt_lambda_policy" {
  name = "c21-gt-lambda-policy"
  role = aws_iam_role.gt_lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect = "Allow"
        Action = [
          "ec2:CreateNetworkInterface",
          "ec2:DescribeNetworkInterfaces",
          "ec2:DeleteNetworkInterface"
        ]
        Resource = "*"
      }
    ]
  })
}

# Security Group for Lambda
resource "aws_security_group" "gt_lambda_sg" {
  name        = "c21-gt-lambda-sg"
  description = "Security group for GT Lambda"
  vpc_id      = data.aws_vpc.main.id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "c21-gt-lambda-sg"
    Environment = var.environment
  }
}

# Lambda Function
resource "aws_lambda_function" "gt_pipeline" {
  function_name = "c21-gt-pipeline"
  role          = aws_iam_role.gt_lambda_role.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.gt_pipeline.repository_url}:latest"
  timeout       = 300
  memory_size   = 512

  vpc_config {
    subnet_ids         = var.public_subnet_ids
    security_group_ids = [aws_security_group.gt_lambda_sg.id]
  }

  environment {
    variables = {
      DB_HOST     = aws_db_instance.trends_db.address
      DB_PORT     = "5432"
      DB_NAME     = var.db_name
      DB_USER     = var.db_username
      DB_PASSWORD = var.db_password
    }
  }

  tags = {
    Name        = "c21-gt-pipeline"
    Environment = var.environment
  }
}

# IAM Role for EventBridge Scheduler
resource "aws_iam_role" "scheduler_role" {
  name = "c21-gt-scheduler-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "scheduler.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name        = "c21-gt-scheduler-role"
    Environment = var.environment
  }
}

# IAM Policy for Scheduler to invoke Lambda
resource "aws_iam_role_policy" "scheduler_policy" {
  name = "c21-gt-scheduler-policy"
  role = aws_iam_role.scheduler_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = "lambda:InvokeFunction"
        Resource = aws_lambda_function.gt_pipeline.arn
      }
    ]
  })
}

# EventBridge Schedule (runs at 7am UTC daily)
resource "aws_scheduler_schedule" "gt_pipeline_schedule" {
  name       = "c21-gt-pipeline-schedule"
  group_name = "default"

  flexible_time_window {
    mode = "OFF"
  }

  schedule_expression = "cron(0 7 * * ? *)"

  target {
    arn      = aws_lambda_function.gt_pipeline.arn
    role_arn = aws_iam_role.scheduler_role.arn
  }
}

output "gt_pipeline_ecr_uri" {
  description = "ECR repository URI for Google Trends pipeline"
  value       = aws_ecr_repository.gt_pipeline.repository_url
}

output "db_endpoint" {
  description = "RDS endpoint"
  value       = aws_db_instance.trends_db.endpoint
}

output "db_name" {
  description = "Database name"
  value       = aws_db_instance.trends_db.db_name
}

output "db_username" {
  description = "Database username"
  value       = aws_db_instance.trends_db.username
}

output "db_port" {
  description = "Database port"
  value       = aws_db_instance.trends_db.port
}