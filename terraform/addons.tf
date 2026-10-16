locals {
  addon_names = toset(["vpc-cni", "coredns", "kube-proxy", "aws-ebs-csi-driver", "eks-pod-identity-agent"])
  pod_accounts = {
    cni = "aws-node"
    ebs = "ebs-csi-controller-sa"
    lbc = "aws-load-balancer-controller"
  }
}

resource "aws_iam_role" "pod" {
  for_each = local.pod_accounts
  name     = "${local.prefix}-${each.key}"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow", Action = ["sts:AssumeRole", "sts:TagSession"]
      Principal = { Service = "pods.eks.amazonaws.com" }
      Condition = { StringEquals = {
        "aws:RequestTag/eks-cluster-arn"            = aws_eks_cluster.main.arn
        "aws:RequestTag/kubernetes-namespace"       = "kube-system"
        "aws:RequestTag/kubernetes-service-account" = each.value
      } }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "cni" {
  role       = aws_iam_role.pod["cni"].name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy"
}

resource "aws_iam_role_policy_attachment" "ebs" {
  role       = aws_iam_role.pod["ebs"].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonEBSCSIDriverPolicyV2"
}

resource "aws_iam_policy" "load_balancer" {
  name        = "${local.prefix}-lbc"
  description = "Upstream AWS Load Balancer Controller v3.6.0 policy; exact SA trust on its role"
  policy      = file("${path.module}/policies/load-balancer-controller-v3.6.0.json")
}

resource "aws_iam_role_policy_attachment" "load_balancer" {
  role       = aws_iam_role.pod["lbc"].name
  policy_arn = aws_iam_policy.load_balancer.arn
}

data "aws_eks_addon_version" "compatible" {
  for_each           = local.addon_names
  addon_name         = each.value
  kubernetes_version = var.kubernetes_version
  most_recent        = true
}

resource "aws_eks_addon" "pod_identity_agent" {
  cluster_name                = aws_eks_cluster.main.name
  addon_name                  = "eks-pod-identity-agent"
  addon_version               = lookup(var.addon_versions, "eks-pod-identity-agent", data.aws_eks_addon_version.compatible["eks-pod-identity-agent"].version)
  resolve_conflicts_on_create = "OVERWRITE"
  resolve_conflicts_on_update = "PRESERVE"
}

resource "aws_eks_pod_identity_association" "load_balancer" {
  cluster_name         = aws_eks_cluster.main.name
  namespace            = "kube-system"
  service_account      = local.pod_accounts.lbc
  role_arn             = aws_iam_role.pod["lbc"].arn
  disable_session_tags = false
  depends_on           = [aws_eks_addon.pod_identity_agent, aws_iam_role_policy_attachment.load_balancer]
}

resource "aws_eks_addon" "cni" {
  cluster_name                = aws_eks_cluster.main.name
  addon_name                  = "vpc-cni"
  addon_version               = lookup(var.addon_versions, "vpc-cni", data.aws_eks_addon_version.compatible["vpc-cni"].version)
  resolve_conflicts_on_create = "OVERWRITE"
  resolve_conflicts_on_update = "PRESERVE"
  pod_identity_association {
    role_arn        = aws_iam_role.pod["cni"].arn
    service_account = local.pod_accounts.cni
  }
  depends_on = [aws_iam_role_policy_attachment.cni, aws_eks_addon.pod_identity_agent]
}

resource "aws_eks_addon" "after_nodes" {
  for_each                    = setsubtract(local.addon_names, toset(["vpc-cni", "eks-pod-identity-agent"]))
  cluster_name                = aws_eks_cluster.main.name
  addon_name                  = each.value
  addon_version               = lookup(var.addon_versions, each.value, data.aws_eks_addon_version.compatible[each.value].version)
  resolve_conflicts_on_create = "OVERWRITE"
  resolve_conflicts_on_update = "PRESERVE"
  dynamic "pod_identity_association" {
    for_each = each.value == "aws-ebs-csi-driver" ? [local.pod_accounts.ebs] : []
    content {
      role_arn        = aws_iam_role.pod["ebs"].arn
      service_account = pod_identity_association.value
    }
  }
  depends_on = [aws_eks_node_group.main, aws_iam_role_policy_attachment.ebs]
}
