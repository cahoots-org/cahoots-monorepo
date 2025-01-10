# AWS Configuration Variables
variable "aws_region" {
  description = "AWS region to deploy resources"
  type        = string
  default     = "us-west-2"  # Default region chosen for its balance of availability, cost, and proximity to users.
}

# VPC Variables
variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"  # Provides a large address space to accommodate future growth and additional subnets.
}

variable "availability_zones" {
  description = "List of availability zones"
  type        = list(string)
  default     = ["us-west-2a", "us-west-2b"]  # Use multiple AZs for high availability and fault tolerance.
}

# Load Balancer Variables
variable "alb_name" {
  description = "Name of the application load balancer"
  type        = string
  default     = "app-alb"  # Naming convention to easily identify the ALB in the infrastructure.
}

# Compute Variables
variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.micro"  # Cost-effective instance type for development and testing environments.
}

variable "min_size" {
  description = "Minimum size of the auto scaling group"
  type        = number
  default     = 2  # Ensure at least two instances for redundancy and load distribution.
}

variable "max_size" {
  description = "Maximum size of the auto scaling group"
  type        = number
  default     = 4  # Limit the maximum size to control costs while allowing for scaling.
}

# Database Variables
variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.micro"  # Economical choice for small to medium workloads.
}

variable "db_name" {
  description = "Name of the database"
  type        = string
  default     = "appdb"  # Standard naming for easy identification and management.
}

# Redis Variables
variable "redis_node_type" {
  description = "ElastiCache Redis node type"
  type        = string
  default     = "cache.t3.micro"  # Suitable for development and small-scale production use.
}

variable "redis_num_cache_nodes" {
  description = "Number of cache nodes in the cluster"
  type        = number
  default     = 1  # Single node for simplicity and cost-effectiveness in non-critical environments.
}

# Monitoring Variables
variable "enable_monitoring" {
  description = "Enable CloudWatch monitoring"
  type        = bool
  default     = true  # Default to true to ensure visibility into resource performance.
}

variable "alarm_email" {
  description = "Email address for CloudWatch alarms"
  type        = string
  default     = ""  # Placeholder for alert notifications, to be configured per environment.
}