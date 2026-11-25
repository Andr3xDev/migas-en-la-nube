variable "location" {
  description = "Azure region for every resource group and the state storage account."
  type        = string
  default     = "centralus"
}

variable "repo" {
  description = "GitHub repository in owner/name form; used as the OIDC subject prefix."
  type        = string
}

variable "github_owner_id" {
  description = "Numeric GitHub owner id: gh api repos/<repo> --jq .owner.id"
  type        = number
}

variable "github_repo_id" {
  description = "Numeric GitHub repository id: gh api repos/<repo> --jq .id"
  type        = number
}

variable "prefix" {
  description = "Short prefix for resource names."
  type        = string
  default     = "pdc"
}

variable "budget_amount" {
  description = "Monthly subscription budget in the billing currency."
  type        = number
}

variable "budget_email" {
  description = "Address notified at 50, 80 and 100 percent of the budget."
  type        = string
}
