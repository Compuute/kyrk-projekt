variable "project_id" { type = string }
variable "region" { type = string }
variable "service_name" { type = string }
variable "service_account" { type = string }
variable "image_placeholder" { type = string }
variable "environment" { type = string }

variable "min_instances" {
  type    = number
  default = 0
}

variable "max_instances" {
  type    = number
  default = 3
}
