# EC2 Launch Template
resource "aws_launch_template" "app_template" {
  name_prefix   = "app-template"  # Use a prefix for easy identification and versioning of launch templates.
  image_id      = var.ami_id  # Specify the AMI ID to ensure consistent instance configuration.
  instance_type = var.instance_type  # Choose an instance type that balances cost and performance for the workload.

  network_interfaces {
    associate_public_ip_address = true  # Enable public IP for direct internet access if needed.
    security_groups            = [aws_security_group.app_sg.id]  # Attach security groups to control access.
  }

  user_data = base64encode(templatefile("${path.module}/user-data.sh", {
    environment = var.environment  # Pass environment variables to configure instances on launch.
  }))

  iam_instance_profile {
    name = aws_iam_instance_profile.app_profile.name  # Attach an IAM profile to grant necessary permissions.
  }

  tags = {
    Name        = "app-template"  # Tag the launch template for resource tracking.
    Environment = var.environment  # Tag with environment for clarity and organization.
  }
}

# Auto Scaling Group
resource "aws_autoscaling_group" "app_asg" {
  name                = "app-asg"  # Name the ASG for easy identification and management.
  desired_capacity    = var.asg_desired_capacity  # Set desired capacity to balance load and cost.
  max_size           = var.asg_max_size  # Define maximum size to control scaling and costs.
  min_size           = var.asg_min_size  # Define minimum size to ensure availability and redundancy.
  target_group_arns  = [aws_lb_target_group.app_tg.arn]  # Attach to target groups for load balancing.
  vpc_zone_identifier = var.private_subnet_ids  # Deploy instances in private subnets for security.

  launch_template {
    id      = aws_launch_template.app_template.id  # Use the launch template for consistent instance configuration.
    version = "$Latest"  # Always use the latest version for updates and improvements.
  }

  tag {
    key                 = "Name"  # Tag key for resource identification.
    value              = "app-instance"  # Tag value for resource identification.
    propagate_at_launch = true  # Ensure tags are applied to instances at launch.
  }
}

# Auto Scaling Policies
resource "aws_autoscaling_policy" "scale_up" {
  name                   = "scale-up"  # Name the policy for easy identification.
  scaling_adjustment     = 1  # Increase capacity by one instance to handle increased load.
  adjustment_type        = "ChangeInCapacity"  # Use capacity change for straightforward scaling.
  cooldown              = 300  # Set cooldown to prevent rapid scaling and instability.
  autoscaling_group_name = aws_autoscaling_group.app_asg.name  # Associate with the ASG for scaling actions.
}

resource "aws_autoscaling_policy" "scale_down" {
  name                   = "scale-down"  # Name the policy for easy identification.
  scaling_adjustment     = -1  # Decrease capacity by one instance to reduce costs during low load.
  adjustment_type        = "ChangeInCapacity"  # Use capacity change for straightforward scaling.
  cooldown              = 300  # Set cooldown to prevent rapid scaling and instability.
  autoscaling_group_name = aws_autoscaling_group.app_asg.name  # Associate with the ASG for scaling actions.
}