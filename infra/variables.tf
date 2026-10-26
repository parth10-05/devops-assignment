variable "aws_region" {
  description = "AWS Region for the academic deployment."
  type        = string
  default     = "ap-south-1"
}

variable "project_name" {
  description = "Lowercase project identifier used in names and tags."
  type        = string
  default     = "triageiq"

  validation {
    condition     = can(regex("^[a-z0-9-]+$", var.project_name))
    error_message = "project_name may contain only lowercase letters, numbers, and hyphens."
  }
}

variable "environment" {
  description = "Deployment environment name."
  type        = string
  default     = "prod"
}

variable "github_repository" {
  description = "GitHub repository in owner/repository form. Only this repository's main branch can deploy."
  type        = string
}

variable "deployment_branch" {
  description = "Branch permitted to assume the GitHub Actions deployment role."
  type        = string
  default     = "main"
}

variable "instance_type" {
  description = "Use a Free Tier eligible type shown by the target AWS account. t3.small gives the lean Compose profile the best chance of fitting."
  type        = string
  default     = "t3.small"
}

variable "root_volume_size" {
  description = "EC2 root EBS volume size in GiB. Keep within the account's Free Tier/credit budget."
  type        = number
  default     = 30
}

variable "budget_alert_email" {
  description = "Email address that receives the monthly AWS cost-budget alert."
  type        = string
}
