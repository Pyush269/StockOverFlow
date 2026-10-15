locals {
  addon_names = toset(["vpc-cni", "coredns", "kube-proxy", "aws-ebs-csi-driver"])
  irsa_accounts = {
    cni = "system:serviceaccount:kube-system:aws-node"
    ebs = "system:serviceaccount:kube-system:ebs-csi-controller-sa"
    lbc = "system:serviceaccount:kube-system:aws-load-balancer-controller"
  }
  oidc_host = replace(aws_eks_cluster.main.identity[0].oidc[0].issuer, "https://", "")
}

data "tls_certificate" "oidc" {
  url = aws_eks_cluster.main.identity[0].oidc[0].issuer
}

resource "aws_iam_openid_connect_provider" "cluster" {
  url             = aws_eks_cluster.main.identity[0].oidc[0].issuer
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = [data.tls_certificate.oidc.certificates[length(data.tls_certificate.oidc.certificates) - 1].sha1_fingerprint]
}

resource "aws_iam_role" "irsa" {
  for_each = local.irsa_accounts
  name     = "${local.prefix}-${each.key}"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow", Action = "sts:AssumeRoleWithWebIdentity"
      Principal = { Federated = aws_iam_openid_connect_provider.cluster.arn }
      Condition = { StringEquals = {
        "${local.oidc_host}:sub" = each.value
        "${local.oidc_host}:aud" = "sts.amazonaws.com"
      } }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "cni" {
  role       = aws_iam_role.irsa["cni"].name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy"
}

resource "aws_iam_role_policy_attachment" "ebs" {
  role       = aws_iam_role.irsa["ebs"].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonEBSCSIDriverPolicyV2"
}

resource "aws_iam_policy" "load_balancer" {
  name        = "${local.prefix}-lbc"
  description = "Upstream AWS Load Balancer Controller v3.6.0 policy; exact SA trust on its role"
  policy      = file("${path.module}/policies/load-balancer-controller-v3.6.0.json")
}

resource "aws_iam_role_policy_attachment" "load_balancer" {
  role       = aws_iam_role.irsa["lbc"].name
  policy_arn = aws_iam_policy.load_balancer.arn
}

data "aws_eks_addon_version" "compatible" {
  for_each           = local.addon_names
  addon_name         = each.value
  kubernetes_version = var.kubernetes_version
  most_recent        = true
}

resource "aws_eks_addon" "cni" {
  cluster_name                = aws_eks_cluster.main.name
  addon_name                  = "vpc-cni"
  addon_version               = lookup(var.addon_versions, "vpc-cni", data.aws_eks_addon_version.compatible["vpc-cni"].version)
  service_account_role_arn    = aws_iam_role.irsa["cni"].arn
  resolve_conflicts_on_create = "OVERWRITE"
  resolve_conflicts_on_update = "PRESERVE"
  depends_on                  = [aws_iam_role_policy_attachment.cni]
}

resource "aws_eks_addon" "after_nodes" {
  for_each                    = setsubtract(local.addon_names, toset(["vpc-cni"]))
  cluster_name                = aws_eks_cluster.main.name
  addon_name                  = each.value
  addon_version               = lookup(var.addon_versions, each.value, data.aws_eks_addon_version.compatible[each.value].version)
  service_account_role_arn    = each.value == "aws-ebs-csi-driver" ? aws_iam_role.irsa["ebs"].arn : null
  resolve_conflicts_on_create = "OVERWRITE"
  resolve_conflicts_on_update = "PRESERVE"
  depends_on                  = [aws_eks_node_group.main, aws_iam_role_policy_attachment.ebs]
}
