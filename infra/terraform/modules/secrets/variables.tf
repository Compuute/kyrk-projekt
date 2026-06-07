variable "project_id" { type = string }
variable "names" { type = list(string) }
variable "accessors" {
  type = list(object({
    secret = string
    member = string
  }))
  default = []
}
