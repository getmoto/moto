data "aws_ssm_parameter" "amazon_linux_2023_x86_64" {
  name = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64"
}

data "aws_ssm_parameter" "amazon_linux_2023_arm64" {
  name = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-arm64"
}

resource "aws_instance" "example_arm64" {
  ami = data.aws_ssm_parameter.amazon_linux_2023_arm64.value

  # Use burstable instance type to trigger ec2:DescribeInstanceCreditSpecifications API call
  instance_type = "t4g.small"
}

resource "aws_instance" "example_x86" {
  ami = data.aws_ssm_parameter.amazon_linux_2023_x86_64.value

  # Use burstable instance type to trigger ec2:DescribeInstanceCreditSpecifications API call
  instance_type = "t2.micro"

}
