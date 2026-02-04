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

  schedule_expression = "cron(0 15 * * ? *)"

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

# ECR Repository for BlueSky Pipeline
resource "aws_ecr_repository" "bluesky_pipeline" {
  name                 = "c21-bluesky-pipeline"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Name        = "c21-bluesky-pipeline"
    Environment = var.environment
  }
}

output "bluesky_pipeline_ecr_uri" {
  description = "ECR repository URI for BlueSky pipeline"
  value       = aws_ecr_repository.bluesky_pipeline.repository_url
}
# Reference existing ECS Cluster
data "aws_ecs_cluster" "c21_cluster" {
  cluster_name = "c21-ecs-cluster"
}

# IAM Role for ECS Task Execution
resource "aws_iam_role" "bluesky_task_execution_role" {
  name = "c21-bluesky-task-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name        = "c21-bluesky-task-execution-role"
    Environment = var.environment
  }
}

# Attach managed policy for ECR access and logging
resource "aws_iam_role_policy_attachment" "bluesky_task_execution_policy" {
  role       = aws_iam_role.bluesky_task_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# IAM Role for ECS Task (runtime permissions)
resource "aws_iam_role" "bluesky_task_role" {
  name = "c21-bluesky-task-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name        = "c21-bluesky-task-role"
    Environment = var.environment
  }
}

# Security Group for BlueSky ECS Service
resource "aws_security_group" "bluesky_ecs_sg" {
  name        = "c21-bluesky-ecs-sg"
  description = "Security group for BlueSky ECS service"
  vpc_id      = data.aws_vpc.main.id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "c21-bluesky-ecs-sg"
    Environment = var.environment
  }
}

# CloudWatch Log Group for BlueSky
resource "aws_cloudwatch_log_group" "bluesky_logs" {
  name              = "/ecs/c21-bluesky-pipeline"
  retention_in_days = 7

  tags = {
    Name        = "c21-bluesky-logs"
    Environment = var.environment
  }
}

# ECS Task Definition
resource "aws_ecs_task_definition" "bluesky_task" {
  family                   = "c21-bluesky-pipeline"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "256"
  memory                   = "512"
  execution_role_arn       = aws_iam_role.bluesky_task_execution_role.arn
  task_role_arn            = aws_iam_role.bluesky_task_role.arn

  container_definitions = jsonencode([
    {
      name      = "bluesky-pipeline"
      image     = "${aws_ecr_repository.bluesky_pipeline.repository_url}:latest"
      essential = true

      environment = [
        { name = "DB_HOST", value = aws_db_instance.trends_db.address },
        { name = "DB_PORT", value = "5432" },
        { name = "DB_NAME", value = var.db_name },
        { name = "DB_USER", value = var.db_username },
        { name = "DB_PASSWORD", value = var.db_password }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.bluesky_logs.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }
    }
  ])

  tags = {
    Name        = "c21-bluesky-task"
    Environment = var.environment
  }
}

# ECS Service
resource "aws_ecs_service" "bluesky_service" {
  name            = "c21-bluesky-service"
  cluster         = data.aws_ecs_cluster.c21_cluster.id
  task_definition = aws_ecs_task_definition.bluesky_task.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.public_subnet_ids
    security_groups  = [aws_security_group.bluesky_ecs_sg.id]
    assign_public_ip = true
  }

  tags = {
    Name        = "c21-bluesky-service"
    Environment = var.environment
  }
}

# ECR Repository for Alert System
resource "aws_ecr_repository" "alert_system" {
  name                 = "c21-trends-alert-system"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Name        = "c21-trends-alert-system"
    Environment = var.environment
  }
}

output "alert_system_ecr_uri" {
  description = "ECR repository URI for Alert System"
  value       = aws_ecr_repository.alert_system.repository_url
}

# IAM Role for Alert Lambda
resource "aws_iam_role" "alert_lambda_role" {
  name = "c21-trends-alert-lambda-role"

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
    Name        = "c21-trends-alert-lambda-role"
    Environment = var.environment
  }
}

# IAM Policy for Alert Lambda (CloudWatch Logs + VPC + SES)
resource "aws_iam_role_policy" "alert_lambda_policy" {
  name = "c21-trends-alert-lambda-policy"
  role = aws_iam_role.alert_lambda_role.id

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
      },
      {
        Effect = "Allow"
        Action = [
          "ses:SendEmail",
          "ses:SendRawEmail"
        ]
        Resource = "*"
      }
    ]
  })
}

# Security Group for Alert Lambda
resource "aws_security_group" "alert_lambda_sg" {
  name        = "c21-trends-alert-lambda-sg"
  description = "Security group for Alert Lambda"
  vpc_id      = data.aws_vpc.main.id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "c21-trends-alert-lambda-sg"
    Environment = var.environment
  }
}

# Alert Lambda Function
# Uses ECR URI: 129033205317.dkr.ecr.eu-west-2.amazonaws.com/c21-trends-alert-system
resource "aws_lambda_function" "alert_system" {
  function_name = "c21-trends-alert-system"
  role          = aws_iam_role.alert_lambda_role.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.alert_system.repository_url}:latest"
  timeout       = 300
  memory_size   = 512

  vpc_config {
    subnet_ids         = var.public_subnet_ids
    security_group_ids = [aws_security_group.alert_lambda_sg.id]
  }

  environment {
    variables = {
      DB_HOST      = aws_db_instance.trends_db.address
      DB_PORT      = "5432"
      DB_NAME      = var.db_name
      DB_USER      = var.db_username
      DB_PASSWORD  = var.db_password
      AWS_REGION_NAME   = var.aws_region
      SENDER_EMAIL = "sl-coaches@proton.me"
    }
  }

  tags = {
    Name        = "c21-trends-alert-system"
    Environment = var.environment
  }
}

# VPC Endpoint for SES
resource "aws_vpc_endpoint" "ses" {
  vpc_id              = data.aws_vpc.main.id
  service_name        = "com.amazonaws.eu-west-2.email-smtp"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = var.public_subnet_ids
  security_group_ids  = [aws_security_group.alert_lambda_sg.id]
  private_dns_enabled = true

  tags = {
    Name        = "c21-ses-endpoint"
    Environment = var.environment
  }
}

# IAM Role for Alert Scheduler
resource "aws_iam_role" "alert_scheduler_role" {
  name = "c21-trends-alert-scheduler-role"

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
    Name        = "c21-trends-alert-scheduler-role"
    Environment = var.environment
  }
}

# IAM Policy for Alert Scheduler to invoke Lambda
resource "aws_iam_role_policy" "alert_scheduler_policy" {
  name = "c21-trends-alert-scheduler-policy"
  role = aws_iam_role.alert_scheduler_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = "lambda:InvokeFunction"
        Resource = aws_lambda_function.alert_system.arn
      }
    ]
  })
}

# EventBridge Schedule (runs every 5 minutes)
resource "aws_scheduler_schedule" "alert_system_schedule" {
  name       = "c21-trends-alert-system-schedule"
  group_name = "default"

  flexible_time_window {
    mode = "OFF"
  }

  schedule_expression = "rate(5 minutes)"

  target {
    arn      = aws_lambda_function.alert_system.arn
    role_arn = aws_iam_role.alert_scheduler_role.arn
  }
}