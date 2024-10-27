data "aws_caller_identity" "this" {}

data "aws_vpc" "this" {
  default = true
}

data "aws_subnets" "this" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.this.id]
  }
}

data "aws_subnet" "this" {
  for_each = toset(data.aws_subnets.this.ids)
  id       = each.value
}
