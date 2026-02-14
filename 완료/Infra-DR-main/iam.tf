# DR IAM Roles

# Load Balancer Controller
module "lb_controller_irsa_role" {
  source  = "terraform-aws-modules/iam/aws//modules/iam-role-for-service-accounts-eks"
  version = "~> 5.0"

  providers = { aws = aws.dr }

  role_name                              = "${var.project_name}-lb-controller-role"
  attach_load_balancer_controller_policy = true

  oidc_providers = {
    main = {
      provider_arn               = module.eks_dr.oidc_provider_arn
      namespace_service_accounts = ["kube-system:aws-load-balancer-controller"]
    }
  }
}

# EBS CSI Driver
module "ebs_csi_irsa_role" {
  source  = "terraform-aws-modules/iam/aws//modules/iam-role-for-service-accounts-eks"
  version = "~> 5.0"

  providers = { aws = aws.dr }

  role_name             = "${var.project_name}-ebs-csi-driver-role"
  attach_ebs_csi_policy = true

  oidc_providers = {
    main = {
      provider_arn               = module.eks_dr.oidc_provider_arn
      namespace_service_accounts = ["kube-system:ebs-csi-controller-sa"]
    }
  }
}

# ArgoCD Role
resource "aws_iam_role" "argocd_role" {
  provider = aws.dr
  name     = "${var.project_name}-argocd-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Federated = module.eks_dr.oidc_provider_arn
      }
      Action = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "${replace(module.eks_dr.cluster_oidc_issuer_url, "https://", "")}:sub" = "system:serviceaccount:argocd:argocd-server"
        }
      }
    }]
  })
}

resource "aws_iam_role_policy" "argocd_policy" {
  provider = aws.dr
  name     = "${var.project_name}-argocd-policy"
  role     = aws_iam_role.argocd_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["ecr:GetAuthorizationToken", "ecr:BatchCheckLayerAvailability", "ecr:GetDownloadUrlForLayer", "ecr:BatchGetImage"]
        Resource = "*"
      }
    ]
  })
}

# AI Service Role (Bedrock, DynamoDB)
resource "aws_iam_role" "ai_service_role" {
  provider = aws.dr
  name     = "${var.project_name}-ai-service-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Federated = module.eks_dr.oidc_provider_arn
      }
      Action = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "${replace(module.eks_dr.cluster_oidc_issuer_url, "https://", "")}:sub" = "system:serviceaccount:default:ai-service-sa"
        }
      }
    }]
  })
}

resource "aws_iam_role_policy" "ai_service_policy" {
  provider = aws.dr
  name     = "${var.project_name}-ai-service-policy"
  role     = aws_iam_role.ai_service_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"]
        Resource = "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-*"
      },
      {
        Effect   = "Allow"
        Action   = ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:Query", "dynamodb:Scan", "dynamodb:UpdateItem", "dynamodb:DeleteItem"]
        Resource = ["arn:aws:dynamodb:${var.dr_region}:*:table/${var.team_chats_table_name}", "arn:aws:dynamodb:${var.dr_region}:*:table/${var.chat_rooms_table_name}"]
      }
    ]
  })
}

# External Secrets Operator
module "external_secrets_irsa_role" {
  source  = "terraform-aws-modules/iam/aws//modules/iam-role-for-service-accounts-eks"
  version = "~> 5.0"

  providers = { aws = aws.dr }

  role_name = "${var.project_name}-external-secrets-role"

  oidc_providers = {
    main = {
      provider_arn               = module.eks_dr.oidc_provider_arn
      namespace_service_accounts = ["external-secrets:external-secrets-sa"]
    }
  }
}

resource "aws_iam_role_policy" "external_secrets_policy" {
  provider = aws.dr
  name     = "${var.project_name}-external-secrets-policy"
  role     = module.external_secrets_irsa_role.iam_role_name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["secretsmanager:GetSecretValue", "secretsmanager:DescribeSecret"]
        Resource = "arn:aws:secretsmanager:${var.dr_region}:*:secret:portforge/*"
      }
    ]
  })
}
