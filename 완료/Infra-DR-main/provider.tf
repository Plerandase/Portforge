# DR Infrastructure - Provider Configuration
# Region: Tokyo (ap-northeast-1)

terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.12"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.25"
    }
  }
}

# DR Region (Tokyo)
provider "aws" {
  alias  = "dr"
  region = var.dr_region

  default_tags {
    tags = {
      Environment = "DR"
      Project     = var.project_name
      ManagedBy   = "Terraform"
    }
  }
}

# Primary Region (Seoul) - RDS Read Replica 소스 참조용
provider "aws" {
  alias  = "primary"
  region = var.primary_region

  default_tags {
    tags = {
      Environment = "Primary"
      Project     = var.project_name
      ManagedBy   = "Terraform"
    }
  }
}

# EKS Cluster Auth Data
data "aws_eks_cluster_auth" "dr" {
  provider = aws.dr
  name     = module.eks_dr.cluster_name
}

# Kubernetes Provider
provider "kubernetes" {
  alias = "dr"

  host                   = module.eks_dr.cluster_endpoint
  cluster_ca_certificate = base64decode(module.eks_dr.cluster_certificate_authority_data)
  token                  = data.aws_eks_cluster_auth.dr.token
}

# Helm Provider
# Note: VS Code Terraform 확장에서 에러 표시되지만, terraform apply 시 정상 동작
provider "helm" {
  alias = "dr"

  kubernetes {
    host                   = module.eks_dr.cluster_endpoint
    cluster_ca_certificate = base64decode(module.eks_dr.cluster_certificate_authority_data)
    token                  = data.aws_eks_cluster_auth.dr.token
  }
}
