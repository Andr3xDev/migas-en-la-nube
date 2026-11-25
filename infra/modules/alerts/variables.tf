variable "name" {
  description = "Name suffix shared by the alert resources."
  type        = string
}

variable "resource_group_name" {
  type = string
}

variable "location" {
  type = string
}

variable "app_insights_id" {
  description = "Application Insights resource the alerts and the availability test attach to."
  type        = string
}

variable "probe_url" {
  description = "Host and path probed by the availability test, without scheme."
  type        = string
}

variable "alert_email" {
  description = "Email address that receives every alert."
  type        = string
}
