import boto3

from moto import mock_ssm
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID


@mock_ssm
def test_ssm_get_by_path():
    client = boto3.client("ssm", region_name="us-west-1")
    path = "/aws/service/global-infrastructure/regions"
    params = client.get_parameters_by_path(Path=path)["Parameters"]

    pacific = [p for p in params if p["Value"] == "af-south-1"][0]
    assert pacific["Name"] == "/aws/service/global-infrastructure/regions/af-south-1"
    assert pacific["Type"] == "String"
    assert pacific["Version"] == 1
    assert pacific["ARN"] == (
        f"arn:aws:ssm:us-west-1:{ACCOUNT_ID}:parameter/aws/service"
        "/global-infrastructure/regions/af-south-1"
    )
    assert "LastModifiedDate" in pacific


@mock_ssm
def test_global_infrastructure_services():
    client = boto3.client("ssm", region_name="us-west-1")
    path = "/aws/service/global-infrastructure/services"
    params = client.get_parameters_by_path(Path=path)["Parameters"]
    assert params[0]["Name"] == (
        "/aws/service/global-infrastructure/services/accessanalyzer"
    )


@mock_ssm
def test_ssm_region_query():
    client = boto3.client("ssm", region_name="us-west-1")
    param = client.get_parameter(
        Name="/aws/service/global-infrastructure/regions/us-west-1/longName"
    )

    value = param["Parameter"]["Value"]
    assert value == "US West (N. California)"
