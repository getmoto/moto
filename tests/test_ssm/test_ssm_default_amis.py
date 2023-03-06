import boto3
import sure  # noqa # pylint: disable=unused-import

from moto import mock_ssm


test_ami = "/aws/service/ami-amazon-linux-latest/al2022-ami-kernel-default-x86_64"


@mock_ssm
def test_ssm_get_latest_ami_by_path():
    client = boto3.client("ssm", region_name="us-west-1")
    path = "/aws/service/ami-amazon-linux-latest"
    params = client.get_parameters_by_path(Path=path)["Parameters"]
    params.should.have.length_of(10)

    assert all(
        [p["Name"].startswith("/aws/service/ami-amazon-linux-latest") for p in params]
    )
    assert all([p["Type"] == "String" for p in params])
    assert all([p["DataType"] == "text" for p in params])
    assert all([p["ARN"].startswith("arn:aws:ssm:us-west-1") for p in params])


@mock_ssm
def test_ssm_latest_amis_are_different_in_regions():
    client = boto3.client("ssm", region_name="us-west-1")
    ami_uswest = client.get_parameter(Name=test_ami)["Parameter"]["Value"]

    client = boto3.client("ssm", region_name="eu-north-1")
    ami_eunorth = client.get_parameter(Name=test_ami)["Parameter"]["Value"]

    ami_uswest.shouldnt.equal(ami_eunorth)
