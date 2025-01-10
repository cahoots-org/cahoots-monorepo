# Application Load Balancer
resource "aws_lb" "main" {
  name               = "${var.project_name}-alb"  # Name the ALB for easy identification and management.
  internal           = false  # Set to false to make the ALB internet-facing, allowing external access.
  load_balancer_type = "application"  # Use an ALB for HTTP/HTTPS traffic, providing advanced routing features.
  security_groups    = [aws_security_group.alb.id]  # Attach security groups to control inbound and outbound traffic.
  subnets            = aws_subnet.public[*].id  # Deploy the ALB in public subnets to handle internet traffic.

  tags = {
    Name        = "${var.project_name}-alb"  # Tag the ALB for resource tracking and management.
    Environment = var.environment  # Tag with environment for clarity and organization.
  }
}

# ALB Target Group
resource "aws_lb_target_group" "app" {
  name        = "${var.project_name}-tg"  # Name the target group for easy identification.
  port        = 80  # Use port 80 for HTTP traffic, simplifying client connections.
  protocol    = "HTTP"  # Use HTTP protocol for standard web traffic.
  vpc_id      = aws_vpc.main.id  # Associate with the VPC for network connectivity.
  target_type = "ip"  # Use IP target type for flexibility in routing traffic to instances.

  health_check {
    path                = "/health"  # Define a health check path to monitor instance health.
    healthy_threshold   = 2  # Require two successful checks before considering an instance healthy.
    unhealthy_threshold = 10  # Allow ten failed checks before marking an instance unhealthy.
  }
}

# ALB Listener
resource "aws_lb_listener" "front_end" {
  load_balancer_arn = aws_lb.main.arn  # Attach the listener to the ALB to handle incoming requests.
  port              = "443"  # Use port 443 for HTTPS traffic, ensuring secure connections.
  protocol          = "HTTPS"  # Use HTTPS protocol for encrypted communication.
  ssl_policy        = "ELBSecurityPolicy-2016-08"  # Apply a secure SSL policy for encryption.
  certificate_arn   = var.certificate_arn  # Use an SSL certificate for secure connections.

  default_action {
    type             = "forward"  # Forward requests to the target group for processing.
    target_group_arn = aws_lb_target_group.app.arn  # Specify the target group for request routing.
  }
}

# ALB Security Group
resource "aws_security_group" "alb" {
  name        = "${var.project_name}-alb-sg"  # Name the security group for easy identification.
  description = "ALB Security Group"  # Describe the security group's purpose.
  vpc_id      = aws_vpc.main.id  # Associate with the VPC for network connectivity.

  ingress {
    protocol    = "tcp"  # Allow TCP traffic for secure connections.
    from_port   = 443  # Allow traffic on port 443 for HTTPS.
    to_port     = 443  # Allow traffic on port 443 for HTTPS.
    cidr_blocks = ["0.0.0.0/0"]  # Allow traffic from any IP address for public access.
  }

  egress {
    protocol    = "-1"  # Allow all outbound traffic for flexibility.
    from_port   = 0  # Allow all ports for outbound traffic.
    to_port     = 0  # Allow all ports for outbound traffic.
    cidr_blocks = ["0.0.0.0/0"]  # Allow outbound traffic to any IP address.
  }

  tags = {
    Name        = "${var.project_name}-alb-sg"  # Tag the security group for resource tracking.
    Environment = var.environment  # Tag with environment for clarity and organization.
  }
}