variable "project" {
  description = "Project name used for resource naming"
  type        = string
  default     = "platform"
}

variable "environment" {
  description = "Environment name (dev, stage, prod)"
  type        = string
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "az_count" {
  description = "Number of availability zones to use"
  type        = number
  default     = 3
}

variable "cluster_name" {
  description = "EKS cluster name for subnet tagging"
  type        = string
}

variable "tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default     = {}
}
