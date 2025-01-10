# Redis subnet group
resource "aws_elasticache_subnet_group" "redis_subnet_group" {
  name       = "${var.project_name}-redis-subnet-group"  # Name the subnet group for easy identification and management.
  subnet_ids = var.private_subnet_ids  # Use private subnets to enhance security and restrict direct internet access.
}

# Redis parameter group
resource "aws_elasticache_parameter_group" "redis_parameter_group" {
  family = "redis6.x"  # Specify the Redis family version for compatibility and feature support.
  name   = "${var.project_name}-redis-params"  # Name the parameter group for easy identification.

  parameter {
    name  = "maxmemory-policy"  # Set the memory management policy to optimize cache performance.
    value = "allkeys-lru"  # Use LRU policy to efficiently manage memory usage.
  }
}

# Redis cluster
resource "aws_elasticache_cluster" "redis" {
  cluster_id           = "${var.project_name}-redis"  # Use a unique cluster ID for easy management and tracking.
  engine              = "redis"  # Choose Redis for its performance and simplicity as an in-memory data store.
  node_type           = var.redis_node_type  # Select a node type that balances cost and performance for the workload.
  num_cache_nodes     = 1  # Start with a single node for simplicity and cost-effectiveness in non-critical environments.
  parameter_group_name = aws_elasticache_parameter_group.redis_parameter_group.name  # Use the parameter group for configuration consistency.
  port                = 6379  # Use the default Redis port for standard access.
  subnet_group_name   = aws_elasticache_subnet_group.redis_subnet_group.name  # Use the subnet group to manage network placement and isolation.
  security_group_ids  = [var.redis_security_group_id]  # Attach security groups to control access and enhance security.

  tags = {
    Name        = "${var.project_name}-redis"  # Tag the Redis cluster for resource tracking and management.
    Environment = var.environment  # Tag with environment for clarity and organization.
  }
}

# Output the Redis endpoint
output "redis_endpoint" {
  value = aws_elasticache_cluster.redis.cache_nodes[0].address  # Output the Redis endpoint address for application integration.
}