# DR EKS Cluster
# Warm Standby: 2 nodes (min), 4 nodes (max)

module "eks_dr" {
  source  = "terraform-aws-modules/eks/aws"
  version = "20.36.0"

  providers = {
    aws = aws.dr
  }

  cluster_name    = var.cluster_name
  cluster_version = var.cluster_version
  vpc_id          = aws_vpc.dr_vpc.id

  subnet_ids = [
    aws_subnet.dr_pri_sub1.id,
    aws_subnet.dr_pri_sub2.id
  ]

  enable_cluster_creator_admin_permissions = false

  access_entries = {
    for idx, arn in var.admin_principal_arns :
    format("admin_%02d", idx + 1) => {
      principal_arn = arn
      policy_associations = {
        admin = {
          policy_arn = "arn:aws:eks::aws:cluster-access-policy/AmazonEKSClusterAdminPolicy"
          access_scope = { type = "cluster" }
        }
      }
    }
  }

  eks_managed_node_groups = {
    dr_node_group = {
      min_size       = var.node_group_min_size
      max_size       = var.node_group_max_size
      desired_size   = var.node_group_desired_size
      instance_types = var.node_group_instance_types

      labels = {
        Environment = "DR"
        Region      = var.dr_region
      }
    }
  }

  cluster_endpoint_public_access = true
  enable_irsa                    = true

  tags = { Name = var.cluster_name }
}
