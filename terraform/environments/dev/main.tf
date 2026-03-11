###############################################################################
# Dev Environment — Terraform Root Module
###############################################################################

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.30"
    }
  }

  # TODO: CONFIGURE — Replace with your actual S3 bucket and DynamoDB table
  # Create these manually or via a bootstrap script before running terraform init
  backend "s3" {
    bucket         = "platform-terraform-state"
    key            = "dev/terraform.tfstate"
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
      Environment = "dev"
      ManagedBy   = "terraform"
      CostCenter  = "platform-engineering"
    }
  }
}

locals {
  environment  = "dev"
  project      = "platform"
  cluster_name = "${local.project}-${local.environment}-eks"

  tags = {
    Project     = local.project
    Environment = local.environment
    ManagedBy   = "terraform"
    CostCenter  = "platform-engineering"
  }
}

# ---------- VPC ----------
module "vpc" {
  source = "../../modules/vpc"

  project      = local.project
  environment  = local.environment
  vpc_cidr     = "10.0.0.0/16"
  az_count     = 3
  cluster_name = local.cluster_name
  tags         = local.tags
}

# ---------- EKS ----------
module "eks" {
  source = "../../modules/eks"

  cluster_name       = local.cluster_name
  cluster_version    = "1.28"
  environment        = local.environment
  vpc_id             = module.vpc.vpc_id
  private_subnet_ids = module.vpc.private_subnet_ids

  node_instance_types = ["t3.medium"]
  node_min_size       = 2
  node_max_size       = 4
  node_desired_size   = 2

  spot_min_size     = 0
  spot_max_size     = 3
  spot_desired_size = 1

  cluster_endpoint_public_access = true

  aws_auth_roles = [
    {
      rolearn  = module.iam.platform_admin_role_arn
      username = "platform-admin"
      groups   = ["system:masters"]
    },
    {
      rolearn  = module.iam.team_developer_role_arn
      username = "team-developer"
      groups   = ["platform:developers"]
    }
  ]

  tags = local.tags
}

# ---------- IAM ----------
module "iam" {
  source = "../../modules/iam"

  project     = local.project
  environment = local.environment
  tags        = local.tags

  # TODO: CONFIGURE — Add your IAM principal ARNs
  admin_principal_arns     = [] # e.g., ["arn:aws:iam::123456789012:user/admin"]
  developer_principal_arns = [] # e.g., ["arn:aws:iam::123456789012:role/dev-team"]

  # TODO: CONFIGURE — Set to true and provide org/repo for GitHub Actions OIDC
  create_github_oidc = false
  github_org         = "YOUR_GITHUB_ORG"
  github_repo        = "portal-gitop"
}
