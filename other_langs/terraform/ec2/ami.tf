data "aws_ami" "ubuntu" {
  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-xenial-16.04-amd64-server-20170721"]
  }

  filter {
    name   = "state"
    values = ["available"]
  }

  most_recent = true

  # Canonical's account ID
  owners = ["099720109477"]
}