import boto3

from moto import mock_ec2, mock_ssm


test_ami = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64"


@mock_ec2
@mock_ssm
def test_ssm_get_latest_ami_by_path():
    ssm = boto3.client("ssm", region_name="us-east-1")
    ami = ssm.get_parameter(Name=test_ami)["Parameter"]["Value"]

    ec2 = boto3.client("ec2", region_name="us-east-1")
    assert len(ec2.describe_images(ImageIds=[ami])["Images"]) == 1
