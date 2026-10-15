data "aws_partition" "current" {}
data "aws_caller_identity" "current" {}
data "aws_ec2_instance_type" "worker" {
  instance_type = var.node_instance_type
}

resource "aws_iam_role" "cluster" {
  name = "${local.prefix}-cluster"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Principal = { Service = "eks.amazonaws.com" }, Action = "sts:AssumeRole" }]
  })
}

resource "aws_iam_role_policy_attachment" "cluster" {
  role       = aws_iam_role.cluster.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy"
}

resource "aws_kms_key" "cluster" {
  description             = "StockFlow EKS secrets and infrastructure logs"
  enable_key_rotation     = true
  deletion_window_in_days = 7
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      { Sid = "AccountAdministration", Effect = "Allow", Principal = { AWS = "arn:aws:iam::${var.expected_account_id}:root" }, Action = "kms:*", Resource = "*" },
      {
        Sid    = "RegionalCloudWatchLogs", Effect = "Allow", Principal = { Service = "logs.${var.aws_region}.amazonaws.com" }
        Action = ["kms:Encrypt", "kms:Decrypt", "kms:ReEncrypt*", "kms:GenerateDataKey*", "kms:DescribeKey"], Resource = "*"
        Condition = { ArnEquals = { "kms:EncryptionContext:aws:logs:arn" = [
          "arn:aws:logs:${var.aws_region}:${var.expected_account_id}:log-group:/aws/eks/${var.cluster_name}/cluster",
          "arn:aws:logs:${var.aws_region}:${var.expected_account_id}:log-group:/stockflow/${local.prefix}/vpc-flow"
        ] } }
      }
    ]
  })
}

resource "aws_kms_alias" "cluster" {
  name          = "alias/${local.prefix}"
  target_key_id = aws_kms_key.cluster.key_id
}

resource "aws_cloudwatch_log_group" "cluster" {
  name              = "/aws/eks/${var.cluster_name}/cluster"
  retention_in_days = 7
  kms_key_id        = aws_kms_key.cluster.arn
}

resource "aws_eks_cluster" "main" {
  name                          = var.cluster_name
  role_arn                      = aws_iam_role.cluster.arn
  version                       = var.kubernetes_version
  bootstrap_self_managed_addons = false
  deletion_protection           = var.deletion_protection
  enabled_cluster_log_types     = ["api", "audit", "authenticator", "controllerManager", "scheduler"]
  access_config {
    authentication_mode                         = "API"
    bootstrap_cluster_creator_admin_permissions = false
  }
  upgrade_policy {
    support_type = "STANDARD"
  }
  encryption_config {
    resources = ["secrets"]
    provider {
      key_arn = aws_kms_key.cluster.arn
    }
  }
  vpc_config {
    subnet_ids              = aws_subnet.private[*].id
    endpoint_private_access = true
    endpoint_public_access  = true
    public_access_cidrs     = var.operator_cidrs
  }
  lifecycle {
    precondition {
      condition     = data.aws_partition.current.partition == "aws"
      error_message = "The vendored load balancer policy supports commercial AWS partitions only."
    }
  }
  depends_on = [aws_iam_role_policy_attachment.cluster, aws_cloudwatch_log_group.cluster, aws_route.private_egress]
}

resource "aws_eks_access_entry" "operator" {
  cluster_name  = aws_eks_cluster.main.name
  principal_arn = var.operator_principal_arn
  type          = "STANDARD"
}

resource "aws_eks_access_policy_association" "operator" {
  cluster_name  = aws_eks_cluster.main.name
  principal_arn = aws_eks_access_entry.operator.principal_arn
  policy_arn    = "arn:aws:eks::aws:cluster-access-policy/AmazonEKSClusterAdminPolicy"
  access_scope {
    type = "cluster"
  }
}

resource "aws_iam_role" "nodes" {
  name = "${local.prefix}-nodes"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Principal = { Service = "ec2.amazonaws.com" }, Action = "sts:AssumeRole" }]
  })
}

resource "aws_iam_role_policy_attachment" "nodes" {
  for_each   = toset(["AmazonEKSWorkerNodePolicy", "AmazonEC2ContainerRegistryPullOnly"])
  role       = aws_iam_role.nodes.name
  policy_arn = "arn:aws:iam::aws:policy/${each.value}"
}

resource "aws_security_group" "nodes" {
  name_prefix = "${local.prefix}-nodes-"
  description = "Private EKS nodes; no SSH or public inbound access"
  vpc_id      = aws_vpc.main.id
  tags = {
    Name                                        = "${local.prefix}-nodes"
    "kubernetes.io/cluster/${var.cluster_name}" = "owned"
  }
}

resource "aws_vpc_security_group_ingress_rule" "node_internal" {
  security_group_id            = aws_security_group.nodes.id
  referenced_security_group_id = aws_security_group.nodes.id
  ip_protocol                  = "-1"
  description                  = "Pod and node communication within the worker security group"
}

resource "aws_vpc_security_group_ingress_rule" "control_plane_to_nodes" {
  for_each                     = toset(["443", "10250", "9443"])
  security_group_id            = aws_security_group.nodes.id
  referenced_security_group_id = aws_eks_cluster.main.vpc_config[0].cluster_security_group_id
  ip_protocol                  = "tcp"
  from_port                    = tonumber(each.value)
  to_port                      = tonumber(each.value)
  description                  = "Control plane to node HTTPS, kubelet, or controller webhook"
}

resource "aws_vpc_security_group_ingress_rule" "nodes_to_api" {
  security_group_id            = aws_eks_cluster.main.vpc_config[0].cluster_security_group_id
  referenced_security_group_id = aws_security_group.nodes.id
  ip_protocol                  = "tcp"
  from_port                    = 443
  to_port                      = 443
  description                  = "Private workers to the Kubernetes API"
}

resource "aws_vpc_security_group_egress_rule" "nodes" {
  security_group_id = aws_security_group.nodes.id
  ip_protocol       = "tcp"
  from_port         = 443
  to_port           = 443
  cidr_ipv4         = "0.0.0.0/0"
  description       = "HTTPS to AWS APIs and image registries through private routes"
}

resource "aws_vpc_security_group_egress_rule" "node_internal" {
  security_group_id            = aws_security_group.nodes.id
  referenced_security_group_id = aws_security_group.nodes.id
  ip_protocol                  = "-1"
  description                  = "Pod and node traffic within the worker security group"
}

resource "aws_vpc_security_group_egress_rule" "dns" {
  for_each          = toset(["tcp", "udp"])
  security_group_id = aws_security_group.nodes.id
  ip_protocol       = each.value
  from_port         = 53
  to_port           = 53
  cidr_ipv4         = "${cidrhost(var.vpc_cidr, 2)}/32"
  description       = "DNS to the VPC resolver"
}

resource "aws_launch_template" "nodes" {
  name_prefix            = "${local.prefix}-"
  update_default_version = true
  vpc_security_group_ids = [aws_security_group.nodes.id]
  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"
    http_put_response_hop_limit = 1
    instance_metadata_tags      = "disabled"
  }
  block_device_mappings {
    device_name = "/dev/xvda"
    ebs {
      volume_size           = var.node_disk_gib
      volume_type           = "gp3"
      encrypted             = true
      delete_on_termination = true
    }
  }
  tag_specifications {
    resource_type = "instance"
    tags          = { Name = "${local.prefix}-worker", Project = "StockFlow", Environment = var.environment }
  }
}

resource "aws_eks_node_group" "main" {
  cluster_name    = aws_eks_cluster.main.name
  node_group_name = "${local.prefix}-workers"
  node_role_arn   = aws_iam_role.nodes.arn
  subnet_ids      = aws_subnet.private[*].id
  version         = var.kubernetes_version
  ami_type        = "AL2023_x86_64_STANDARD"
  capacity_type   = "ON_DEMAND"
  instance_types  = [var.node_instance_type]
  launch_template {
    id      = aws_launch_template.nodes.id
    version = aws_launch_template.nodes.latest_version
  }
  scaling_config {
    min_size     = var.node_scaling.min
    desired_size = var.node_scaling.desired
    max_size     = var.node_scaling.max
  }
  update_config {
    max_unavailable = 1
    # The current project has a 5-vCPU quota. Avoid the default surge, which
    # temporarily launches extra nodes; one worker is unavailable during updates.
    update_strategy = "MINIMAL"
  }
  lifecycle {
    precondition {
      condition = contains(data.aws_ec2_instance_type.worker.supported_architectures, "x86_64") && (
        data.aws_ec2_instance_type.worker.default_vcpus >= 2 && data.aws_ec2_instance_type.worker.memory_size >= 4096
      )
      error_message = "Choose an x86_64 worker with at least 2 vCPUs and 4 GiB RAM."
    }
  }
  depends_on = [
    aws_iam_role_policy_attachment.nodes, aws_eks_addon.cni,
    aws_vpc_security_group_ingress_rule.control_plane_to_nodes,
    aws_vpc_security_group_ingress_rule.nodes_to_api,
    aws_vpc_security_group_ingress_rule.node_internal,
    aws_vpc_security_group_egress_rule.nodes,
    aws_vpc_security_group_egress_rule.node_internal,
    aws_vpc_security_group_egress_rule.dns
  ]
}
