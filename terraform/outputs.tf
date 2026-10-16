output "region" { value = var.aws_region }
output "cluster_name" { value = aws_eks_cluster.main.name }
output "cluster_endpoint" { value = aws_eks_cluster.main.endpoint }
output "vpc_id" { value = aws_vpc.main.id }
output "public_subnet_ids" { value = aws_subnet.public[*].id }
output "private_subnet_ids" { value = aws_subnet.private[*].id }
output "node_security_group_id" { value = aws_security_group.nodes.id }
output "load_balancer_controller_role_arn" { value = aws_iam_role.pod["lbc"].arn }
output "ebs_csi_role_arn" { value = aws_iam_role.pod["ebs"].arn }
output "addon_versions" {
  value = merge({ "vpc-cni" = aws_eks_addon.cni.addon_version, "eks-pod-identity-agent" = aws_eks_addon.pod_identity_agent.addon_version }, { for name, addon in aws_eks_addon.after_nodes : name => addon.addon_version })
}
output "update_kubeconfig_command" {
  value = "aws eks update-kubeconfig --region ${var.aws_region} --name ${aws_eks_cluster.main.name}"
}
output "design_summary" {
  value = {
    availability_zones = local.zones
    nat_gateways       = local.nat_count
    worker_type        = var.node_instance_type
    workers            = var.node_scaling
    node_disk_gib      = var.node_disk_gib
    public_api_cidrs   = var.operator_cidrs
    controller_policy  = "v3.6.0"
  }
}
