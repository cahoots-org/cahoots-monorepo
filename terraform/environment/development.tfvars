environment = "development"
project_name = "ai-dev-team"

# VPC Configuration
vpc_cidr = "10.0.0.0/16"
public_subnets  = ["10.0.1.0/24", "10.0.2.0/24"]
private_subnets = ["10.0.3.0/24", "10.0.4.0/24"]

# Compute Configuration
instance_type = "t3.micro"
min_size     = 1
max_size     = 2

# Database Configuration
db_instance_class = "db.t3.micro"
db_name          = "aidevteam"

# Redis Configuration
redis_node_type       = "cache.t3.micro"
redis_num_cache_nodes = 1

# Monitoring Configuration
enable_monitoring = true
alarm_email      = "dev-alerts@example.com" 