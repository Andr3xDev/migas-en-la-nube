output "swa_url" {
  value = "https://${module.static_web_app.default_host_name}"
}

output "api_key" {
  value     = module.static_web_app.api_key
  sensitive = true
}
