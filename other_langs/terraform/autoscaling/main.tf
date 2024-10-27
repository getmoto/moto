resource "tls_private_key" "this" {
  algorithm = "RSA"
  rsa_bits  = 4096
}

resource "aws_key_pair" "this" {
  key_name   = var.app_name
  public_key = tls_private_key.this.public_key_openssh
}

resource "aws_launch_template" "this" {
  name                   = var.app_name
  image_id               = var.ami_id
  instance_type          = var.instance_type
  key_name               = aws_key_pair.this.key_name
  vpc_security_group_ids = [aws_security_group.this.id]
}

resource "aws_autoscaling_group" "this" {
  name                  = var.app_name
  desired_capacity      = 10
  min_size              = 1
  max_size              = 50
  health_check_type     = "EC2"
  vpc_zone_identifier   = [for subnet_id in data.aws_subnet.this : subnet_id.id]

  wait_for_capacity_timeout = 0

  launch_template {
    id      = aws_launch_template.this.id
    version = aws_launch_template.this.latest_version
  }
}
