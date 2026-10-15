variable "aws_region" {
  description = "Commercial AWS region; confirm EKS/add-on availability before planning."
  type        = string
  default     = "ap-southeast-2"
}

variable "expected_account_id" {
  description = "Explicit target AWS account; the provider rejects any other account."
  type        = string
  validation {
    condition     = can(regex("^[0-9]{12}$", var.expected_account_id))
    error_message = "Use the target 12-digit AWS account ID."
  }
}

variable "operator_principal_arn" {
  description = "Existing IAM role/user ARN for the operator, never an STS session or root ARN."
  type        = string
  validation {
    condition     = can(regex("^arn:aws:iam::${var.expected_account_id}:(role|user)/.+$", var.operator_principal_arn))
    error_message = "Use an existing IAM role/user ARN in expected_account_id; do not use root or an assumed-role session ARN."
  }
}

variable "operator_cidrs" {
  description = "Current trusted public IPv4 CIDRs for kubectl; no unrestricted API endpoint."
  type        = list(string)
  validation {
    condition = length(var.operator_cidrs) > 0 && alltrue([
      for cidr in var.operator_cidrs : try(can(cidrnetmask(cidr)) && tonumber(split("/", cidr)[1]) >= 24, false)
    ])
    error_message = "Supply at least one valid IPv4 CIDR of /24 or narrower (prefer your public IP/32); 0.0.0.0/0 is forbidden."
  }
}

variable "cluster_name" {
  type    = string
  default = "stockflow-eks"
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{2,35}$", var.cluster_name))
    error_message = "Use 3–36 lowercase letters/digits/hyphens, starting with a letter."
  }
}

variable "environment" {
  type    = string
  default = "capstone"
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{1,11}$", var.environment))
    error_message = "Use 2–12 lowercase letters/digits/hyphens."
  }
}

variable "kubernetes_version" {
  description = "Default 1.36 matches installed kubectl; recheck regional standard support before the real plan."
  type        = string
  default     = "1.36"
  validation {
    condition     = contains(["1.35", "1.36", "1.37"], var.kubernetes_version)
    error_message = "Use 1.35–1.37 with kubectl 1.36, after verifying regional EKS standard support."
  }
}

variable "vpc_cidr" {
  type    = string
  default = "10.42.0.0/16"
  validation {
    condition = try(can(cidrnetmask(var.vpc_cidr)) && split("/", var.vpc_cidr)[1] == "16" && can(regex(
      "^(10\\.|192\\.168\\.|172\\.(1[6-9]|2[0-9]|3[01])\\.)", var.vpc_cidr
    )), false)
    error_message = "Use an RFC1918 IPv4 /16, avoiding existing networks you need to connect."
  }
}

variable "nat_mode" {
  description = "single saves capstone cost but has one-AZ egress dependency; per_az uses two NAT gateways."
  type        = string
  default     = "single"
  validation {
    condition     = contains(["single", "per_az"], var.nat_mode)
    error_message = "nat_mode must be single or per_az."
  }
}

variable "node_instance_type" {
  description = "x86_64 instance with at least 2 vCPUs/4 GiB; m7i-flex.large is free-plan eligible with 8 GiB in Sydney. Verify project eligibility before changing."
  type        = string
  default     = "m7i-flex.large"
}

variable "node_scaling" {
  description = "Two workers; increase max only after checking the regional vCPU quota. No cluster autoscaler is installed."
  type        = object({ min = number, desired = number, max = number })
  default     = { min = 2, desired = 2, max = 2 }
  validation {
    condition = alltrue([for count in values(var.node_scaling) : count == floor(count)]) && (
      var.node_scaling.min >= 2 && var.node_scaling.min <= var.node_scaling.desired &&
      var.node_scaling.desired <= var.node_scaling.max && var.node_scaling.max <= 6
    )
    error_message = "Use integer counts: 2 <= min <= desired <= max <= 6."
  }
}

variable "node_disk_gib" {
  type    = number
  default = 30
  validation {
    condition     = var.node_disk_gib >= 20 && var.node_disk_gib <= 100 && floor(var.node_disk_gib) == var.node_disk_gib
    error_message = "Use an integer root disk size between 20 and 100 GiB."
  }
}

variable "addon_versions" {
  description = "Optional exact EKS add-on versions; otherwise AWS resolves the latest compatible version into the saved plan."
  type        = map(string)
  default     = {}
  validation {
    condition     = alltrue([for name in keys(var.addon_versions) : contains(["vpc-cni", "coredns", "kube-proxy", "aws-ebs-csi-driver"], name)])
    error_message = "Only vpc-cni, coredns, kube-proxy, and aws-ebs-csi-driver are managed here."
  }
}

variable "deletion_protection" {
  description = "Enable for longer-lived environments; disable explicitly before approved cleanup."
  type        = bool
  default     = false
}
