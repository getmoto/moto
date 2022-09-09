import boto3
import sure  # noqa # pylint: disable=unused-import

from moto import mock_ssm
from moto.core import ACCOUNT_ID


@mock_ssm
def test_ssm_get_by_path():
    client = boto3.client("ssm", region_name="us-west-1")
    path = "/aws/service/global-infrastructure/regions"
    params = client.get_parameters_by_path(Path=path)["Parameters"]

    pacific = [p for p in params if p["Value"] == "af-south-1"][0]
    pacific["Name"].should.equal(
        "/aws/service/global-infrastructure/regions/af-south-1"
    )
    pacific["Type"].should.equal("String")
    pacific["Version"].should.equal(1)
    pacific["ARN"].should.equal(
        f"arn:aws:ssm:us-west-1:{ACCOUNT_ID}:parameter/aws/service/global-infrastructure/regions/af-south-1"
    )
    pacific.should.have.key("LastModifiedDate")


@mock_ssm
def test_ssm_region_query():
    client = boto3.client("ssm", region_name="us-west-1")
    param = client.get_parameter(
        Name="/aws/service/global-infrastructure/regions/us-west-1/longName"
    )

    value = param["Parameter"]["Value"]

    value.should.equal("US West (N. California)")
