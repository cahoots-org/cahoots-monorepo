environment = "staging"
project_name = "cahoots"

# VPC Configuration
vpc_cidr = "10.1.0.0/16"
public_subnets  = ["10.1.1.0/24", "10.1.2.0/24"]
private_subnets = ["10.1.3.0/24", "10.1.4.0/24"]

# Compute Configuration
instance_type = "t3.small"
min_size     = 2
max_size     = 4

# Database Configuration
db_instance_class = "db.t3.small"
db_name          = "aidevteam"

# Redis Configuration
redis_node_type       = "cache.t3.small"
redis_num_cache_nodes = 2

# Monitoring Configuration
enable_monitoring = true
alarm_email      = "staging-alerts@example.com" 