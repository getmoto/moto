data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "all" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

resource "aws_lb" "this" {
  name                       = "nlb-test"
  internal                   = true
  load_balancer_type         = "application"
  subnets                    = data.aws_subnets.all.ids
  enable_deletion_protection = false
}