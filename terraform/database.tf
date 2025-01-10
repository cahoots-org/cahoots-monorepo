# RDS Database Instance
resource "aws_db_instance" "main" {
  identifier        = "${var.project_name}-${var.environment}-db"  # Use a unique identifier for easy management and tracking.
  engine            = "postgres"  # Choose PostgreSQL for its reliability and feature set.
  engine_version    = "13.7"  # Specify the engine version for compatibility and stability.
  instance_class    = "db.t3.micro"  # Select an instance class that balances cost and performance for the workload.
  allocated_storage = 20  # Allocate sufficient storage for current needs with room for growth.

  db_name  = var.db_name  # Set the database name for easy identification and access.
  username = var.db_username  # Define a master username for database administration.
  password = var.db_password  # Set a secure password for database access.

  vpc_security_group_ids = [aws_security_group.rds.id]  # Attach security groups to control access and enhance security.
  db_subnet_group_name   = aws_db_subnet_group.main.name  # Use a subnet group to manage network placement and isolation.

  backup_retention_period = 7  # Retain backups for a week to ensure data recovery options.
  skip_final_snapshot    = true  # Skip final snapshot to speed up deletion in non-critical environments.

  tags = {
    Name        = "${var.project_name}-${var.environment}-db"  # Tag the database for resource tracking and management.
    Environment = var.environment  # Tag with environment for clarity and organization.
  }
}

# RDS Subnet Group
resource "aws_db_subnet_group" "main" {
  name       = "${var.project_name}-${var.environment}-db-subnet-group"  # Name the subnet group for easy identification.
  subnet_ids = var.private_subnet_ids  # Use private subnets to enhance security and restrict direct internet access.

  tags = {
    Name        = "${var.project_name}-${var.environment}-db-subnet-group"  # Tag the subnet group for resource tracking.
    Environment = var.environment  # Tag with environment for clarity and organization.
  }
}

# Security Group for RDS
resource "aws_security_group" "rds" {
  name        = "${var.project_name}-${var.environment}-rds-sg"  # Name the security group for easy identification.
  description = "Security group for RDS database"  # Describe the security group's purpose.
  vpc_id      = var.vpc_id  # Associate with the VPC for network connectivity.

  ingress {
    from_port       = 5432  # Allow traffic on port 5432 for PostgreSQL access.
    to_port         = 5432  # Allow traffic on port 5432 for PostgreSQL access.
    protocol        = "tcp"  # Use TCP protocol for database connections.
    security_groups = [var.app_security_group_id]  # Restrict access to specific security groups for enhanced security.
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-rds-sg"  # Tag the security group for resource tracking.
    Environment = var.environment  # Tag with environment for clarity and organization.
  }
}