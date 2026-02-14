# DR Route 53 Failover Configuration

data "aws_route53_zone" "main" {
  count        = var.domain_name != "" ? 1 : 0
  name         = var.domain_name
  private_zone = false
}

# Primary Health Check
resource "aws_route53_health_check" "primary" {
  count = var.domain_name != "" && var.primary_alb_dns != "" ? 1 : 0

  fqdn              = var.primary_alb_dns
  port              = 80
  type              = "HTTP"
  resource_path     = var.health_check_path
  failure_threshold = 3
  request_interval  = 30

  tags = { Name = "${var.project_name}-primary-health-check" }
}
