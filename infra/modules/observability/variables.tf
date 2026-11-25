variable "name" {
  description = "Name suffix shared by the workspace and Application Insights."
  type        = string
}

variable "resource_group_name" {
  type = string
}

variable "location" {
  type = string
}

variable "retention_in_days" {
  type    = number
  default = 30
}
