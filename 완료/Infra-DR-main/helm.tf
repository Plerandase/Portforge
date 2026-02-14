# DR Helm Charts

# AWS Load Balancer Controller
resource "helm_release" "aws_load_balancer_controller" {
  provider   = helm.dr
  name       = "aws-load-balancer-controller"
  repository = "https://aws.github.io/eks-charts"
  chart      = "aws-load-balancer-controller"
  namespace  = "kube-system"
  version    = "1.10.2"

  values = [yamlencode({
    clusterName = module.eks_dr.cluster_name
    region      = var.dr_region
    vpcId       = aws_vpc.dr_vpc.id
    serviceAccount = {
      create = true
      name   = "aws-load-balancer-controller"
      annotations = {
        "eks.amazonaws.com/role-arn" = module.lb_controller_irsa_role.iam_role_arn
      }
    }
  })]

  depends_on = [module.eks_dr, module.lb_controller_irsa_role]
}

# ArgoCD
resource "kubernetes_namespace" "argocd" {
  provider = kubernetes.dr

  metadata { name = "argocd" }

  depends_on = [module.eks_dr]
}

resource "helm_release" "argocd" {
  provider   = helm.dr
  name       = "argocd"
  repository = "https://argoproj.github.io/argo-helm"
  chart      = "argo-cd"
  namespace  = kubernetes_namespace.argocd.metadata[0].name
  version    = "7.7.12"

  values = [yamlencode({
    server = {
      service   = { type = "LoadBalancer" }
      extraArgs = ["--insecure"]
    }
    configs = {
      params = { "server.insecure" = true }
    }
  })]

  depends_on = [module.eks_dr, helm_release.aws_load_balancer_controller]
}

# EBS CSI Driver
resource "helm_release" "ebs_csi_driver" {
  provider   = helm.dr
  name       = "aws-ebs-csi-driver"
  repository = "https://kubernetes-sigs.github.io/aws-ebs-csi-driver"
  chart      = "aws-ebs-csi-driver"
  namespace  = "kube-system"
  version    = "2.37.0"

  values = [yamlencode({
    controller = {
      serviceAccount = {
        create = true
        name   = "ebs-csi-controller-sa"
        annotations = {
          "eks.amazonaws.com/role-arn" = module.ebs_csi_irsa_role.iam_role_arn
        }
      }
    }
  })]

  depends_on = [module.eks_dr, module.ebs_csi_irsa_role]
}

# External Secrets Operator
resource "kubernetes_namespace" "external_secrets" {
  provider = kubernetes.dr

  metadata { name = "external-secrets" }

  depends_on = [module.eks_dr]
}

resource "helm_release" "external_secrets" {
  provider   = helm.dr
  name       = "external-secrets"
  repository = "https://charts.external-secrets.io"
  chart      = "external-secrets"
  namespace  = kubernetes_namespace.external_secrets.metadata[0].name
  version    = "0.9.13"

  values = [yamlencode({
    installCRDs = true
    serviceAccount = {
      create = true
      name   = "external-secrets-sa"
      annotations = {
        "eks.amazonaws.com/role-arn" = module.external_secrets_irsa_role.iam_role_arn
      }
    }
  })]

  depends_on = [module.eks_dr, module.external_secrets_irsa_role]
}
