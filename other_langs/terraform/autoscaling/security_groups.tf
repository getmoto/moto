resource "aws_security_group" "this" {
  name        = var.app_name
  vpc_id      = data.aws_vpc.this.id

  ingress {
    description = "SSH ingress"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [for cidr in data.aws_subnet.this : cidr.cidr_block]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = var.app_name
  }

}
