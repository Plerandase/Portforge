# DR Infrastructure Outputs

# VPC
output "vpc_id" {
  value = aws_vpc.dr_vpc.id
}

output "vpc_cidr" {
  value = aws_vpc.dr_vpc.cidr_block
}

output "public_subnet_ids" {
  value = [aws_subnet.dr_pub_sub1.id, aws_subnet.dr_pub_sub2.id]
}

output "private_subnet_ids" {
  value = [aws_subnet.dr_pri_sub1.id, aws_subnet.dr_pri_sub2.id]
}

output "db_subnet_ids" {
  value = [aws_subnet.dr_db_sub1.id, aws_subnet.dr_db_sub2.id]
}

# EKS
output "eks_cluster_name" {
  value = module.eks_dr.cluster_name
}

output "eks_cluster_endpoint" {
  value = module.eks_dr.cluster_endpoint
}

output "eks_oidc_provider_arn" {
  value = module.eks_dr.oidc_provider_arn
}

output "kubectl_config_command" {
  value = "aws eks update-kubeconfig --region ${var.dr_region} --name ${module.eks_dr.cluster_name}"
}

# IAM
output "iam_roles" {
  value = {
    lb_controller = module.lb_controller_irsa_role.iam_role_arn
    ebs_csi       = module.ebs_csi_irsa_role.iam_role_arn
    argocd        = aws_iam_role.argocd_role.arn
    ai_service    = aws_iam_role.ai_service_role.arn
  }
}

# CloudWatch
output "sns_topic_arn" {
  value = aws_sns_topic.dr_alerts.arn
}
