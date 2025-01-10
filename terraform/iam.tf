# ECS Task Execution Role
resource "aws_iam_role" "ecs_task_execution_role" {
  name = "${var.project_name}-ecs-task-execution-role"  # Name the IAM role for easy identification and management.

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"  # Allow ECS tasks to assume this role for necessary permissions.
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"  # Specify ECS tasks as the principal for role assumption.
        }
      }
    ]
  })
}

# Attach the AWS managed policy for ECS task execution
resource "aws_iam_role_policy_attachment" "ecs_task_execution_role_policy" {
  role       = aws_iam_role.ecs_task_execution_role.name  # Attach the policy to the ECS task execution role.
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"  # Use the managed policy to simplify permissions management.
}

# Application Role for ECS Tasks
resource "aws_iam_role" "app_role" {
  name = "${var.project_name}-app-role"  # Name the IAM role for easy identification and management.

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"  # Allow ECS tasks to assume this role for application-specific permissions.
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"  # Specify ECS tasks as the principal for role assumption.
        }
      }
    ]
  })
}

# Application-specific permissions policy
resource "aws_iam_role_policy" "app_policy" {
  name = "${var.project_name}-app-policy"  # Name the policy for easy identification and management.
  role = aws_iam_role.app_role.id  # Attach the policy to the application role.

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ]
        Resource = [
          "${var.s3_bucket_arn}",
          "${var.s3_bucket_arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = "*"
      }
    ]
  })
}