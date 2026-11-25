variable "location" {
  description = "Azure region for every resource group and the state storage account."
  type        = string
  default     = "centralus"
}

variable "repo" {
  description = "GitHub repository in owner/name form; used as the OIDC subject prefix."
  type        = string
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
