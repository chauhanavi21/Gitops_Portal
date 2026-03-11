###############################################################################
# IAM Module — Platform IAM roles & policies
###############################################################################

# ---------- EKS Cluster Role ----------
resource "aws_iam_role" "eks_cluster" {
  name = "${var.project}-${var.environment}-eks-cluster-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "eks.amazonaws.com"
      }
    }]
  })

  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "eks_cluster_policy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy"
  role       = aws_iam_role.eks_cluster.name
}

# ---------- Platform Admin Role ----------
resource "aws_iam_role" "platform_admin" {
  name = "${var.project}-${var.environment}-platform-admin"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        AWS = var.admin_principal_arns
      }
    }]
  })

  tags = merge(var.tags, {
    Role = "platform-admin"
  })
}

resource "aws_iam_policy" "platform_admin_policy" {
  name        = "${var.project}-${var.environment}-platform-admin-policy"
  description = "Platform admin policy for EKS and related services"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "EKSFullAccess"
        Effect = "Allow"
        Action = [
          "eks:*",
          "ec2:Describe*",
          "ecr:*",
          "logs:*",
          "cloudwatch:*",
          "iam:PassRole"
        ]
        Resource = "*"
      },
      {
        Sid    = "S3TerraformState"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ]
        Resource = [
          "arn:aws:s3:::${var.terraform_state_bucket}",
          "arn:aws:s3:::${var.terraform_state_bucket}/*"
        ]
      },
      {
        Sid    = "DynamoDBLocking"
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:DeleteItem"
        ]
        Resource = "arn:aws:dynamodb:*:*:table/${var.terraform_lock_table}"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "platform_admin_attach" {
  policy_arn = aws_iam_policy.platform_admin_policy.arn
  role       = aws_iam_role.platform_admin.name
}

# ---------- Team Developer Role ----------
resource "aws_iam_role" "team_developer" {
  name = "${var.project}-${var.environment}-team-developer"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        AWS = var.developer_principal_arns
      }
    }]
  })

  tags = merge(var.tags, {
    Role = "team-developer"
  })
}

resource "aws_iam_policy" "team_developer_policy" {
  name        = "${var.project}-${var.environment}-team-developer-policy"
  description = "Limited access for team developers"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "EKSReadAccess"
        Effect = "Allow"
        Action = [
          "eks:DescribeCluster",
          "eks:ListClusters",
          "eks:AccessKubernetesApi"
        ]
        Resource = "*"
      },
      {
        Sid    = "ECRPushPull"
        Effect = "Allow"
        Action = [
          "ecr:GetAuthorizationToken",
          "ecr:BatchGetImage",
          "ecr:GetDownloadUrlForLayer",
          "ecr:PutImage",
          "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart",
          "ecr:CompleteLayerUpload",
          "ecr:BatchCheckLayerAvailability"
        ]
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "team_developer_attach" {
  policy_arn = aws_iam_policy.team_developer_policy.arn
  role       = aws_iam_role.team_developer.name
}

# ---------- GitHub Actions OIDC Provider ----------
# NOTE: You need to configure GitHub OIDC provider for your AWS account
# See: https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/configuring-openid-connect-in-amazon-web-services
resource "aws_iam_openid_connect_provider" "github_actions" {
  count = var.create_github_oidc ? 1 : 0

  url = "https://token.actions.githubusercontent.com"

  client_id_list = ["sts.amazonaws.com"]

  # TODO: EXTERNAL DEPENDENCY — GitHub OIDC thumbprint
  # This thumbprint may change; verify at:
  # https://github.blog/changelog/2023-06-27-github-actions-update-on-oidc-integration-with-aws/
  thumbprint_list = ["6938fd4d98bab03faadb97b34396831e3780aea1"]

  tags = var.tags
}

resource "aws_iam_role" "github_actions" {
  count = var.create_github_oidc ? 1 : 0
  name  = "${var.project}-${var.environment}-github-actions"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRoleWithWebIdentity"
      Effect = "Allow"
      Principal = {
        Federated = aws_iam_openid_connect_provider.github_actions[0].arn
      }
      Condition = {
        StringLike = {
          "token.actions.githubusercontent.com:sub" = "repo:${var.github_org}/${var.github_repo}:*"
        }
      }
    }]
  })

  tags = var.tags
}
