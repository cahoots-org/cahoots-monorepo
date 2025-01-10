# VPC Configuration
resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr  # Define a large CIDR block to allow for future expansion and subnetting.
  enable_dns_hostnames = true  # Enable DNS hostnames for easier resource identification and management.
  enable_dns_support   = true  # Enable DNS support to facilitate service discovery within the VPC.

  tags = {
    Name = "${var.environment}-vpc"  # Tag resources for easy identification and environment segregation.
  }
}

# Public Subnets
resource "aws_subnet" "public" {
  count             = length(var.public_subnets)  # Create multiple public subnets for high availability across AZs.
  vpc_id            = aws_vpc.main.id  # Associate subnets with the VPC for network connectivity.
  cidr_block        = var.public_subnets[count.index]  # Assign CIDR blocks to prevent overlap and ensure efficient IP usage.
  availability_zone = data.aws_availability_zones.available.names[count.index]  # Distribute subnets across AZs for fault tolerance.

  tags = {
    Name = "${var.environment}-public-subnet-${count.index + 1}"  # Tag subnets for easy management and identification.
  }
}

# Private Subnets
resource "aws_subnet" "private" {
  count             = length(var.private_subnets)  # Create private subnets to isolate sensitive resources from the internet.
  vpc_id            = aws_vpc.main.id  # Associate subnets with the VPC for network connectivity.
  cidr_block        = var.private_subnets[count.index]  # Assign CIDR blocks to prevent overlap and ensure efficient IP usage.
  availability_zone = data.aws_availability_zones.available.names[count.index]  # Distribute subnets across AZs for fault tolerance.

  tags = {
    Name = "${var.environment}-private-subnet-${count.index + 1}"  # Tag subnets for easy management and identification.
  }
}

# Internet Gateway
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id  # Attach the internet gateway to the VPC to enable internet access for public subnets.

  tags = {
    Name = "${var.environment}-igw"  # Tag the internet gateway for easy identification.
  }
}

# Route Tables
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id  # Create a route table for public subnets to manage internet-bound traffic.

  route {
    cidr_block = "0.0.0.0/0"  # Route all outbound traffic to the internet gateway.
    gateway_id = aws_internet_gateway.main.id  # Use the internet gateway for internet access.
  }

  tags = {
    Name = "${var.environment}-public-rt"  # Tag the route table for easy identification.
  }
}

resource "aws_route_table_association" "public" {
  count          = length(var.public_subnets)  # Associate each public subnet with the public route table.
  subnet_id      = aws_subnet.public[count.index].id  # Subnet ID for association.
  route_table_id = aws_route_table.public.id  # Route table ID for association.
}

# NAT Gateway
resource "aws_eip" "nat" {
  domain = "vpc"  # Allocate an Elastic IP for the NAT gateway to provide consistent outbound IP.
}

resource "aws_nat_gateway" "main" {
  allocation_id = aws_eip.nat.id  # Use the allocated Elastic IP for the NAT gateway.
  subnet_id     = aws_subnet.public[0].id  # Place the NAT gateway in a public subnet for internet access.

  tags = {
    Name = "${var.environment}-nat"  # Tag the NAT gateway for easy identification.
  }
}

# Private Route Table
resource "aws_route_table" "private" {
  vpc_id = aws_vpc.main.id  # Create a route table for private subnets to manage outbound traffic via NAT.

  route {
    cidr_block     = "0.0.0.0/0"  # Route all outbound traffic through the NAT gateway.
    nat_gateway_id = aws_nat_gateway.main.id  # Use the NAT gateway for internet access.
  }

  tags = {
    Name = "${var.environment}-private-rt"  # Tag the route table for easy identification.
  }
}

resource "aws_route_table_association" "private" {
  count          = length(var.private_subnets)  # Associate each private subnet with the private route table.
  subnet_id      = aws_subnet.private[count.index].id  # Subnet ID for association.
  route_table_id = aws_route_table.private.id  # Route table ID for association.
}