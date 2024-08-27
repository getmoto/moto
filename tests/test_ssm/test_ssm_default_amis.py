import boto3
import pytest

from moto import mock_aws

test_ami = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64"


@mock_aws
@pytest.mark.parametrize(
    "partition,region",
    [
        ("aws", "us-west-1"),
        ("aws-us-gov", "us-gov-east-1"),
        ("aws-us-gov", "us-gov-west-1"),
    ],
)
def test_ssm_get_latest_ami_by_path(partition, region):
    client = boto3.client("ssm", region_name=region)
    path = "/aws/service/ami-amazon-linux-latest"
    params = client.get_parameters_by_path(Path=path)["Parameters"]
    assert len(params) == 10

    assert all(
        {p["Name"].startswith("/aws/service/ami-amazon-linux-latest") for p in params}
    )
    assert all({p["Type"] == "String" for p in params})
    assert all({p["DataType"] == "text" for p in params})
    assert all({p["ARN"].startswith(f"arn:{partition}:ssm:{region}") for p in params})


@mock_aws
def test_ssm_latest_amis_are_different_in_regions():
    client = boto3.client("ssm", region_name="us-west-1")
    ami_uswest = client.get_parameter(Name=test_ami)["Parameter"]["Value"]

    client = boto3.client("ssm", region_name="eu-north-1")
    ami_eunorth = client.get_parameter(Name=test_ami)["Parameter"]["Value"]

    assert ami_uswest != ami_eunorth
