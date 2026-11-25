variable "name" {
  description = "Globally unique account name (3-24 lowercase alphanumerics)."
  type        = string
}

variable "resource_group_name" {
  type = string
}

variable "location" {
  type = string
}
