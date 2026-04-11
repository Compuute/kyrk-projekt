variable "project_id" { type = string }
variable "region" { type = string }
variable "name" { type = string }

variable "public_read" {
  type    = bool
  default = false
}

variable "retention_days" {
  type    = number
  default = null
}
