import boto3

from moto import mock_ec2, mock_ssm


@mock_ec2
@mock_ssm
def test_ssm_get_latest_ami_by_path():
    ssm = boto3.client("ssm", region_name="us-east-1")
    path = "/aws/service/ecs/optimized-ami"
    params = ssm.get_parameters_by_path(Path=path, Recursive=True)["Parameters"]
    assert len(params) == 10

    ec2 = boto3.client("ec2", region_name="us-east-1")
    for param in params:
        if "Value" in param and isinstance(param["Value"], dict):
            ami = param["Value"]["image_id"]
            assert len(ec2.describe_images(ImageIds=[ami])["Images"]) == 1
