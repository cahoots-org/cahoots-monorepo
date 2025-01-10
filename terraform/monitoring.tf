# CloudWatch Log Groups
resource "aws_cloudwatch_log_group" "application" {
  name              = "/aws/application/${var.environment}"  # Organize logs by environment for easy access and management.
  retention_in_days = 30  # Retain logs for 30 days to balance storage costs and historical data needs.

  tags = {
    Environment = var.environment  # Tag with environment for clarity and organization.
  }
}

# CloudWatch Alarms for EC2 instances
resource "aws_cloudwatch_metric_alarm" "cpu_utilization" {
  alarm_name          = "${var.environment}-cpu-utilization"  # Name the alarm for easy identification and management.
  comparison_operator = "GreaterThanThreshold"  # Trigger alarm when CPU utilization exceeds the threshold.
  evaluation_periods  = "2"  # Require two evaluation periods to confirm the alarm condition.
  metric_name         = "CPUUtilization"  # Monitor CPU utilization to detect performance issues.
  namespace           = "AWS/EC2"  # Use the EC2 namespace for instance metrics.
  period              = "300"  # Evaluate the metric every 5 minutes.
  statistic           = "Average"  # Use average statistic to smooth out short-term fluctuations.
  threshold           = "80"  # Set threshold at 80% to alert on high CPU usage.
  alarm_description   = "This metric monitors EC2 CPU utilization"  # Describe the purpose of the alarm.
  alarm_actions       = [aws_sns_topic.alerts.arn]  # Notify via SNS when the alarm is triggered.
}

# RDS Monitoring
resource "aws_cloudwatch_metric_alarm" "database_connections" {
  alarm_name          = "${var.environment}-db-connections"  # Name the alarm for easy identification and management.
  comparison_operator = "GreaterThanThreshold"  # Trigger alarm when database connections exceed the threshold.
  evaluation_periods  = "2"  # Require two evaluation periods to confirm the alarm condition.
  metric_name         = "DatabaseConnections"  # Monitor database connections to detect potential bottlenecks.
  namespace           = "AWS/RDS"  # Use the RDS namespace for database metrics.
  period              = "300"  # Evaluate the metric every 5 minutes.
  statistic           = "Average"  # Use average statistic to smooth out short-term fluctuations.
  threshold           = "100"  # Set threshold at 100 connections to alert on high usage.
  alarm_description   = "This metric monitors RDS connections"  # Describe the purpose of the alarm.
  alarm_actions       = [aws_sns_topic.alerts.arn]  # Notify via SNS when the alarm is triggered.
}

# Redis Monitoring
resource "aws_cloudwatch_metric_alarm" "redis_cpu" {
  alarm_name          = "${var.environment}-redis-cpu"  # Name the alarm for easy identification and management.
  comparison_operator = "GreaterThanThreshold"  # Trigger alarm when Redis CPU utilization exceeds the threshold.
  evaluation_periods  = "2"  # Require two evaluation periods to confirm the alarm condition.
  metric_name         = "EngineCPUUtilization"  # Monitor Redis CPU utilization to detect performance issues.
  namespace           = "AWS/ElastiCache"  # Use the ElastiCache namespace for Redis metrics.
  period              = "300"  # Evaluate the metric every 5 minutes.
  statistic           = "Average"  # Use average statistic to smooth out short-term fluctuations.
  threshold           = "80"  # Set threshold at 80% to alert on high CPU usage.
  alarm_description   = "This metric monitors Redis CPU utilization"  # Describe the purpose of the alarm.
  alarm_actions       = [aws_sns_topic.alerts.arn]  # Notify via SNS when the alarm is triggered.
}

# SNS Topic for alerts
resource "aws_sns_topic" "alerts" {
  name = "${var.environment}-monitoring-alerts"  # Name the SNS topic for easy identification and management.
}