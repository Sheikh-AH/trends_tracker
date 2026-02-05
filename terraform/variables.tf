variable "aws_region" {
  description = "AWS region"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID to deploy into"
  type        = string
}

variable "db_name" {
  description = "Name of the database"
  type        = string
}

variable "db_username" {
  description = "Master username for the database"
  type        = string
}

variable "db_password" {
  description = "Master password for the database"
  type        = string
  sensitive   = true
}

variable "db_instance_class" {
  description = "RDS instance type"
  type        = string
}

variable "db_allocated_storage" {
  description = "Allocated storage in GB"
  type        = number
}

variable "publicly_accessible" {
  description = "Whether the database is publicly accessible"
  type        = bool
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "public_subnet_ids" {
  description = "Public subnet IDs for Lambda VPC config"
  type        = list(string)
  default     = [
    "subnet-0b2624702047deb8b",
    "subnet-0fbc8bed69fb32837",
    "subnet-00c5753756bd9f245"
  ]
}
variable "openrouter_api_key" {
  description = "API key for OpenRouter"
  type        = string
  sensitive   = true
}