# All AWS calls are mocked. These plans never contact or create AWS resources.
mock_provider "aws" {
  mock_data "aws_availability_zones" {
    defaults = { names = ["ap-southeast-2a", "ap-southeast-2b", "ap-southeast-2c"] }
  }
  mock_data "aws_partition" {
    defaults = { partition = "aws" }
  }
  mock_data "aws_caller_identity" {
    defaults = { account_id = "111111111111", arn = "arn:aws:iam::111111111111:role/StockFlowOperator" }
  }
  mock_data "aws_ec2_instance_type" {
    defaults = { supported_architectures = ["x86_64"], default_vcpus = 2, memory_size = 4096 }
  }
  mock_data "aws_eks_addon_version" {
    defaults = { version = "v1.0.0-eksbuild.1" }
  }
  mock_resource "aws_iam_role" {
    defaults = { arn = "arn:aws:iam::111111111111:role/MockRole" }
  }
  mock_resource "aws_iam_policy" {
    defaults = { arn = "arn:aws:iam::111111111111:policy/MockPolicy" }
  }
  mock_resource "aws_launch_template" {
    defaults = { id = "lt-11111111111111111", latest_version = 1 }
  }
  mock_resource "aws_cloudwatch_log_group" {
    defaults = { arn = "arn:aws:logs:ap-southeast-2:111111111111:log-group:mock" }
  }
  mock_resource "aws_kms_key" {
    defaults = { arn = "arn:aws:kms:ap-southeast-2:111111111111:key/11111111-1111-1111-1111-111111111111" }
  }
  mock_resource "aws_eks_cluster" {
    defaults = {
      arn        = "arn:aws:eks:ap-southeast-2:111111111111:cluster/stockflow-eks"
      endpoint   = "https://EXAMPLE.eks.amazonaws.com"
      identity   = [{ oidc = [{ issuer = "https://oidc.eks.ap-southeast-2.amazonaws.com/id/EXAMPLE" }] }]
      vpc_config = { cluster_security_group_id = "sg-11111111111111111" }
    }
  }
}

variables {
  expected_account_id    = "111111111111"
  operator_principal_arn = "arn:aws:iam::111111111111:role/StockFlowOperator"
  operator_cidrs         = ["203.0.113.10/32"]
}

run "private_network_and_egress" {
  command = apply # Mock providers only; in-memory fake resources, no AWS calls.
  assert {
    condition     = length(aws_subnet.public) == 2 && length(aws_subnet.private) == 2 && length(toset(local.zones)) == 2
    error_message = "The design must span two AZs with two public and two private subnets."
  }
  assert {
    condition     = alltrue([for subnet in aws_subnet.private : !subnet.map_public_ip_on_launch]) && aws_eks_node_group.main.subnet_ids == toset(aws_subnet.private[*].id)
    error_message = "Workers must use private subnets without automatic public addresses."
  }
  assert {
    condition     = length(aws_nat_gateway.main) == 1 && alltrue([for route in aws_route.private_egress : route.nat_gateway_id == aws_nat_gateway.main[0].id])
    error_message = "Single-NAT mode must route both private AZs through the selected NAT."
  }
}

run "per_az_egress" {
  command = apply
  variables { nat_mode = "per_az" }
  assert {
    condition     = length(aws_nat_gateway.main) == 2 && alltrue([for index in range(2) : aws_route.private_egress[index].nat_gateway_id == aws_nat_gateway.main[index].id])
    error_message = "Per-AZ mode must route each private AZ through its own NAT."
  }
}

run "single_worker_demo" {
  command = apply
  assert {
    condition     = aws_eks_node_group.main.scaling_config[0].desired_size == 1 && aws_eks_node_group.main.scaling_config[0].max_size == 2 && length(aws_eks_node_group.main.subnet_ids) == 2
    error_message = "The demo uses one worker with room for manual expansion and retains both private subnets."
  }
}

run "reject_zero_workers" {
  command = plan
  variables { node_scaling = { min = 0, desired = 0, max = 2 } }
  expect_failures = [var.node_scaling]
}

run "endpoint_identity_and_worker_security" {
  command = apply
  assert {
    condition     = aws_eks_cluster.main.vpc_config[0].endpoint_private_access && aws_eks_cluster.main.vpc_config[0].public_access_cidrs == toset(var.operator_cidrs)
    error_message = "The cluster must use a private endpoint plus an explicitly restricted public operator endpoint."
  }
  assert {
    condition     = aws_eks_cluster.main.access_config[0].authentication_mode == "API" && !aws_eks_cluster.main.access_config[0].bootstrap_cluster_creator_admin_permissions && aws_eks_access_entry.operator.principal_arn == var.operator_principal_arn
    error_message = "Operator access must be explicit rather than implicitly granting the creator administrator access."
  }
  assert {
    condition     = aws_launch_template.nodes.metadata_options[0].http_tokens == "required" && aws_launch_template.nodes.metadata_options[0].http_put_response_hop_limit == 1 && aws_launch_template.nodes.block_device_mappings[0].ebs[0].encrypted
    error_message = "Workers need IMDSv2 with hop limit 1 and encrypted root disks."
  }
  assert {
    condition     = aws_eks_cluster.main.upgrade_policy[0].support_type == "STANDARD" && length(aws_eks_cluster.main.enabled_cluster_log_types) == 5 && aws_eks_node_group.main.ami_type == "AL2023_x86_64_STANDARD"
    error_message = "Use standard support, full control-plane audit logging, and AL2023 workers."
  }
  assert {
    condition     = aws_eks_node_group.main.update_config[0].update_strategy == "MINIMAL" && aws_eks_node_group.main.update_config[0].max_unavailable == 1
    error_message = "Updates must replace one worker at a time without surge capacity under the current quota."
  }
  assert {
    condition     = aws_vpc_security_group_egress_rule.nodes.ip_protocol == "tcp" && aws_vpc_security_group_egress_rule.nodes.from_port == 443 && aws_vpc_security_group_egress_rule.nodes.to_port == 443 && alltrue([for rule in aws_vpc_security_group_egress_rule.dns : rule.cidr_ipv4 == "${cidrhost(var.vpc_cidr, 2)}/32"])
    error_message = "External worker egress must be HTTPS, with DNS scoped to the VPC resolver."
  }
}

run "service_account_scoped_iam" {
  command = apply
  assert {
    condition = alltrue([for name, account in local.pod_accounts :
      jsondecode(aws_iam_role.pod[name].assume_role_policy).Statement[0].Principal.Service == "pods.eks.amazonaws.com" &&
      toset(jsondecode(aws_iam_role.pod[name].assume_role_policy).Statement[0].Action) == toset(["sts:AssumeRole", "sts:TagSession"]) &&
      jsondecode(aws_iam_role.pod[name].assume_role_policy).Statement[0].Condition.StringEquals["aws:RequestTag/eks-cluster-arn"] == aws_eks_cluster.main.arn &&
      jsondecode(aws_iam_role.pod[name].assume_role_policy).Statement[0].Condition.StringEquals["aws:RequestTag/kubernetes-namespace"] == "kube-system" &&
      jsondecode(aws_iam_role.pod[name].assume_role_policy).Statement[0].Condition.StringEquals["aws:RequestTag/kubernetes-service-account"] == account
    ])
    error_message = "Each Pod Identity trust must bind the EKS service, exact cluster, namespace, and service account."
  }
  assert {
    condition = !contains(keys(aws_iam_role_policy_attachment.nodes), "AmazonEKS_CNI_Policy") && (
      one(aws_eks_addon.cni.pod_identity_association).role_arn == aws_iam_role.pod["cni"].arn &&
      one(aws_eks_addon.cni.pod_identity_association).service_account == "aws-node" &&
      one(aws_eks_addon.after_nodes["aws-ebs-csi-driver"].pod_identity_association).role_arn == aws_iam_role.pod["ebs"].arn &&
      one(aws_eks_addon.after_nodes["aws-ebs-csi-driver"].pod_identity_association).service_account == "ebs-csi-controller-sa"
    )
    error_message = "CNI and EBS permissions must use separate pod roles, not the EC2 node role."
  }
  assert {
    condition = aws_eks_pod_identity_association.load_balancer.cluster_name == aws_eks_cluster.main.name && (
      aws_eks_pod_identity_association.load_balancer.namespace == "kube-system" &&
      aws_eks_pod_identity_association.load_balancer.service_account == "aws-load-balancer-controller" &&
      aws_eks_pod_identity_association.load_balancer.role_arn == aws_iam_role.pod["lbc"].arn &&
      !aws_eks_pod_identity_association.load_balancer.disable_session_tags &&
      aws_eks_addon.pod_identity_agent.addon_name == "eks-pod-identity-agent"
    )
    error_message = "Load balancer credentials require the exact Pod Identity association and enabled session tags."
  }
}

run "reject_world_open_api" {
  command = plan
  variables { operator_cidrs = ["0.0.0.0/0"] }
  expect_failures = [var.operator_cidrs]
}

run "reject_sts_session_operator" {
  command = plan
  variables { operator_principal_arn = "arn:aws:sts::111111111111:assumed-role/StockFlowOperator/session" }
  expect_failures = [var.operator_principal_arn]
}

run "reject_foreign_account_operator" {
  command = plan
  variables { operator_principal_arn = "arn:aws:iam::222222222222:role/OtherOperator" }
  expect_failures = [var.operator_principal_arn]
}

run "reject_invalid_worker_scaling" {
  command = plan
  variables { node_scaling = { min = 2, desired = 1, max = 3 } }
  expect_failures = [var.node_scaling]
}

run "reject_stale_kubernetes_version" {
  command = plan
  variables { kubernetes_version = "1.31" }
  expect_failures = [var.kubernetes_version]
}
