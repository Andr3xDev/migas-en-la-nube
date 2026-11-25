variable "prefix" {
  description = "Short prefix shared with the bootstrap resource groups."
  type        = string
  default     = "pdc"
}

variable "app_version" {
  description = "Value of PDC_VERSION exposed by the API."
  type        = string
  default     = "0.1.0"
}
