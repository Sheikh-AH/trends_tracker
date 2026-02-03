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