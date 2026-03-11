variable "project" {
  type    = string
  default = "platform"
}

variable "environment" {
  type = string
}

variable "admin_principal_arns" {
  description = "ARNs of IAM users/roles that can assume platform-admin"
  type        = list(string)
  default     = []
}

variable "developer_principal_arns" {
  description = "ARNs of IAM users/roles that can assume team-developer"
  type        = list(string)
  default     = []
}

variable "terraform_state_bucket" {
  description = "S3 bucket for Terraform state"
  type        = string
  default     = "platform-terraform-state"
}

variable "terraform_lock_table" {
  description = "DynamoDB table for Terraform locking"
  type        = string
  default     = "platform-terraform-locks"
}

variable "create_github_oidc" {
  description = "Create GitHub Actions OIDC provider"
  type        = bool
  default     = false
}

variable "github_org" {
  description = "GitHub organization name"
  type        = string
  default     = ""
}

variable "github_repo" {
  description = "GitHub repository name"
  type        = string
  default     = ""
}

variable "tags" {
  type    = map(string)
  default = {}
}
