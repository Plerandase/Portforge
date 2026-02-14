# DR CloudWatch Alarms

# SNS Topic for Alerts
resource "aws_sns_topic" "dr_alerts" {
  provider = aws.dr
  name     = "${var.project_name}-alerts"
}

# EKS Node CPU Alarm
resource "aws_cloudwatch_metric_alarm" "eks_node_cpu" {
  provider            = aws.dr
  alarm_name          = "${var.project_name}-eks-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "node_cpu_utilization"
  namespace           = "ContainerInsights"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "[DR-Tokyo] EKS Node CPU > 80%"

  dimensions = { ClusterName = var.cluster_name }

  alarm_actions = [aws_sns_topic.dr_alerts.arn]
  ok_actions    = [aws_sns_topic.dr_alerts.arn]
}

# EKS Node Memory Alarm
resource "aws_cloudwatch_metric_alarm" "eks_node_memory" {
  provider            = aws.dr
  alarm_name          = "${var.project_name}-eks-memory-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "node_memory_utilization"
  namespace           = "ContainerInsights"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "[DR-Tokyo] EKS Node Memory > 80%"

  dimensions = { ClusterName = var.cluster_name }

  alarm_actions = [aws_sns_topic.dr_alerts.arn]
  ok_actions    = [aws_sns_topic.dr_alerts.arn]
}

# RDS Alarms
resource "aws_cloudwatch_metric_alarm" "rds_cpu" {
  provider            = aws.dr
  alarm_name          = "${var.project_name}-rds-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/RDS"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "[DR-Tokyo] RDS CPU > 80%"
  dimensions          = { DBInstanceIdentifier = "portforge-dr-rds-replica" }
  alarm_actions       = [aws_sns_topic.dr_alerts.arn]
  ok_actions          = [aws_sns_topic.dr_alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "rds_replica_lag" {
  provider            = aws.dr
  alarm_name          = "${var.project_name}-rds-replica-lag"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "ReplicaLag"
  namespace           = "AWS/RDS"
  period              = 60
  statistic           = "Average"
  threshold           = 60
  alarm_description   = "[DR-Tokyo] RDS Replica Lag > 60s"
  dimensions          = { DBInstanceIdentifier = "portforge-dr-rds-replica" }
  alarm_actions       = [aws_sns_topic.dr_alerts.arn]
}

# Route 53 Health Check Alarm (Primary 장애 감지)
resource "aws_cloudwatch_metric_alarm" "primary_health_check" {
  count    = var.domain_name != "" && var.primary_alb_dns != "" ? 1 : 0
  provider = aws.dr

  alarm_name          = "${var.project_name}-primary-health-check"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 2
  metric_name         = "HealthCheckStatus"
  namespace           = "AWS/Route53"
  period              = 60
  statistic           = "Minimum"
  threshold           = 1
  alarm_description   = "[DR-Tokyo] Primary Region Health Check Failed"
  treat_missing_data  = "breaching"

  dimensions = { HealthCheckId = aws_route53_health_check.primary[0].id }

  alarm_actions = [aws_sns_topic.dr_alerts.arn]
}
