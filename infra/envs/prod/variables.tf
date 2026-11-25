variable "prefix" {
  description = "Short prefix shared with the bootstrap resource groups."
  type        = string
  default     = "pdc"
}

variable "alert_email" {
  description = "Email address that receives prod alerts."
  type        = string

  validation {
    condition     = can(regex("@", var.alert_email))
    error_message = "alert_email must be an email address; set the ALERT_EMAIL variable in the prod GitHub environment."
  }
}

variable "app_version" {
  description = "Value of PDC_VERSION exposed by the API."
  type        = string
  default     = "0.1.0"
}
