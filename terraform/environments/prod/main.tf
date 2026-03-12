###############################################################################
# Prod Environment — Terraform Root Module (hardened)
###############################################################################

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.30"
    }
  }

  backend "s3" {
    bucket         = "platform-terraform-state"
    key            = "prod/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "platform-terraform-locks"
    encrypt        = true
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "platform-portal"
      Environment = "prod"
      ManagedBy   = "terraform"
      CostCenter  = "platform-engineering"
    }
  }
}

locals {
  environment  = "prod"
  project      = "platform"
  cluster_name = "${local.project}-${local.environment}-eks"
  tags = {
    Project     = local.project
    Environment = local.environment
    ManagedBy   = "terraform"
    CostCenter  = "platform-engineering"
  }
}

module "vpc" {
  source       = "../../modules/vpc"
  project      = local.project
  environment  = local.environment
  vpc_cidr     = "10.2.0.0/16"
  az_count     = 3
  cluster_name = local.cluster_name
  tags         = local.tags
}

module "eks" {
  source             = "../../modules/eks"
  cluster_name       = local.cluster_name
  cluster_version    = "1.28"
  environment        = local.environment
  vpc_id             = module.vpc.vpc_id
  private_subnet_ids = module.vpc.private_subnet_ids

  node_instance_types = ["m5.xlarge"]
  node_min_size       = 3
  node_max_size       = 10
  node_desired_size   = 5

  cluster_endpoint_public_access = false  # prod: private only

  aws_auth_roles = [
    {
      rolearn  = module.iam.platform_admin_role_arn
      username = "platform-admin"
      groups   = ["system:masters"]
    }
  ]
  tags = local.tags
}

module "iam" {
  source      = "../../modules/iam"
  project     = local.project
  environment = local.environment
  tags        = local.tags
}
