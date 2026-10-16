terraform {
  required_version = ">= 1.16.0, < 2.0.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "6.69.0"
    }
  }
  # Single operator: local state. Back up securely; never commit state/plans.
  backend "local" {}
}

provider "aws" {
  region              = var.aws_region
  allowed_account_ids = [var.expected_account_id]
  default_tags {
    tags = {
      Project     = "StockFlow"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}
