# Configure AWS Provider
provider "aws" {
  region = var.aws_region  # Specify the AWS region to ensure resources are deployed in the desired geographical location for latency and compliance.
}

# VPC Module
module "vpc" {
  source = "./modules/vpc"  # Use a module to encapsulate VPC setup, promoting reusability and consistency across environments.
  environment = var.environment  # Tag resources with the environment to differentiate between production, staging, etc.
  vpc_cidr    = var.vpc_cidr  # Define the CIDR block to control the IP address range for the VPC, ensuring no overlap with other networks.
}

# Load Balancer Module
module "alb" {
  source = "./modules/alb"  # Encapsulate ALB setup to manage traffic distribution and improve application availability.
  vpc_id = module.vpc.vpc_id  # Associate the ALB with the VPC to ensure it can route traffic to resources within the VPC.
  subnets = module.vpc.public_subnets  # Deploy the ALB in public subnets to allow internet-facing access.
}

# Compute Resources Module
module "ecs" {
  source = "./modules/ecs"  # Use ECS to manage containerized applications, simplifying deployment and scaling.
  vpc_id = module.vpc.vpc_id  # Ensure ECS resources are within the VPC for security and network control.
  alb_target_group_arn = module.alb.target_group_arn  # Connect ECS services to the ALB for load balancing and fault tolerance.
}

# Database Module
module "rds" {
  source = "./modules/rds"  # Use RDS for managed database services, reducing operational overhead and improving reliability.
  vpc_id = module.vpc.vpc_id  # Place RDS instances within the VPC for security and network isolation.
  subnet_ids = module.vpc.private_subnets  # Use private subnets to restrict direct internet access to the database.
}

# Redis Module
module "redis" {
  source = "./modules/redis"  # Deploy Redis for in-memory data storage, enhancing application performance with fast data access.
  vpc_id = module.vpc.vpc_id  # Ensure Redis is within the VPC for security and network control.
  subnet_ids = module.vpc.private_subnets  # Use private subnets to protect Redis from direct internet exposure.
}

# IAM Module
module "iam" {
  source = "./modules/iam"  # Manage IAM roles and policies to enforce security and access control across AWS resources.
}

# Monitoring Module
module "monitoring" {
  source = "./modules/monitoring"  # Implement monitoring to gain insights into resource performance and detect issues early.
  environment = var.environment  # Tag monitoring resources with the environment for clarity and organization.
}

# Variables
variable "aws_region" {
  description = "AWS region to deploy resources"
  default     = "us-west-2"  # Default to a specific region to standardize deployments and optimize latency.
}

variable "environment" {
  description = "Environment name"
  default     = "production"  # Default to production to ensure resources are tagged appropriately for the live environment.
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  default     = "10.0.0.0/16"  # Default CIDR block to provide a large address space for future scaling.
}