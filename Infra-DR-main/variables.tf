# DR Infrastructure Variables

# Project
variable "project_name" {
  description = "Project name prefix"
  type        = string
  default     = "portforge-dr"
}

variable "dr_region" {
  description = "DR region"
  type        = string
  default     = "ap-northeast-1"
}

variable "primary_region" {
  description = "Primary region"
  type        = string
  default     = "ap-northeast-2"
}

# VPC
variable "vpc_cidr" {
  description = "VPC CIDR block"
  type        = string
  default     = "10.20.0.0/16"
}

variable "availability_zones" {
  description = "Availability zones"
  type        = list(string)
  default     = ["ap-northeast-1a", "ap-northeast-1c"]
}

variable "public_subnet_cidrs" {
  description = "Public subnet CIDRs"
  type        = list(string)
  default     = ["10.20.1.0/24", "10.20.11.0/24"]
}

variable "private_subnet_cidrs" {
  description = "Private subnet CIDRs"
  type        = list(string)
  default     = ["10.20.2.0/24", "10.20.12.0/24"]
}

variable "db_subnet_cidrs" {
  description = "DB subnet CIDRs"
  type        = list(string)
  default     = ["10.20.3.0/24", "10.20.13.0/24"]
}

# EKS
variable "cluster_name" {
  description = "EKS cluster name"
  type        = string
  default     = "portforge-dr-cluster"
}

variable "cluster_version" {
  description = "EKS version"
  type        = string
  default     = "1.33"
}

variable "admin_principal_arns" {
  description = "IAM principal ARNs for cluster admin"
  type        = list(string)
}

variable "node_group_min_size" {
  description = "Node group min size"
  type        = number
  default     = 2
}

variable "node_group_max_size" {
  description = "Node group max size"
  type        = number
  default     = 4
}

variable "node_group_desired_size" {
  description = "Node group desired size"
  type        = number
  default     = 2
}

variable "node_group_instance_types" {
  description = "Node instance types"
  type        = list(string)
  default     = ["t3.large"]
}

# RDS
variable "primary_db_identifier" {
  description = "Primary RDS identifier"
  type        = string
  default     = "portforge-test-rds"
}

variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.micro"
}

variable "db_port" {
  description = "Database port"
  type        = number
  default     = 3306
}

variable "db_multi_az" {
  description = "Enable Multi-AZ"
  type        = bool
  default     = false
}

variable "db_skip_final_snapshot" {
  description = "Skip final snapshot"
  type        = bool
  default     = true
}

# DynamoDB (Global Table 참조용)
variable "team_chats_table_name" {
  description = "Team chats table name"
  type        = string
  default     = "team_chats_ddb"
}

variable "chat_rooms_table_name" {
  description = "Chat rooms table name"
  type        = string
  default     = "chat_rooms_ddb"
}

# Route 53
variable "domain_name" {
  description = "Domain name"
  type        = string
  default     = ""
}

variable "primary_alb_dns" {
  description = "Primary ALB DNS"
  type        = string
  default     = ""
}

variable "health_check_path" {
  description = "Health check path"
  type        = string
  default     = "/health"
}

# CloudWatch
variable "slack_webhook_url" {
  description = "Slack webhook URL"
  type        = string
  sensitive   = true
  default     = ""
}
