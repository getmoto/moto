# These tests are called from EC2, but collect data from all services
# Because it essentially loads all services in the background, these are long-running tests (10 secs)
#
# There are some issues with running these tests in parallel
# Running them as part of 'moto/core' avoids that problem
import sys

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws
from moto.utilities.distutils_version import LooseVersion

boto3_version = sys.modules["botocore"].__version__


@mock_aws
def test_describe_vpc_endpoint_services_bad_args() -> None:
    """Verify exceptions are raised for bad arguments."""
    ec2 = boto3.client("ec2", region_name="us-west-1")

    # Bad service name -- a default service would typically be of the format:
    # 'com.amazonaws.<region>.<service_name>'.
    with pytest.raises(ClientError) as exc:
        ec2.describe_vpc_endpoint_services(ServiceNames=["s3"])
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidServiceName"
    assert "The Vpc Endpoint Service 's3' does not exist" in err["Message"]

    # Bad filter specification -- the filter name should be "service-type"
    # not "ServiceType".
    with pytest.raises(ClientError) as exc:
        ec2.describe_vpc_endpoint_services(
            ServiceNames=["com.amazonaws.us-west-1.s3"],
            Filters=[{"Name": "ServiceType", "Values": ["Gateway"]}],
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidFilter"
    assert "The filter 'ServiceType' is invalid" in err["Message"]

    # Bad token -- a token of "foo" has no correlation with this data.
    with pytest.raises(ClientError) as exc:
        ec2.describe_vpc_endpoint_services(
            ServiceNames=["com.amazonaws.us-west-1.s3"],
            Filters=[{"Name": "service-type", "Values": ["Gateway"]}],
            NextToken="foo",
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidNextToken"
    assert "The token 'foo' is invalid" in err["Message"]


@mock_aws
def test_describe_vpc_endpoint_services_unimplemented_service() -> None:
    """Verify exceptions are raised for bad arguments."""
    ec2 = boto3.client("ec2", region_name="us-east-1")

    service_name = "com.amazonaws.us-east-1.bedrock-agent-runtime"
    resp = ec2.describe_vpc_endpoint_services(ServiceNames=[service_name])
    assert resp["ServiceNames"] == [service_name]


@mock_aws
def test_describe_vpc_default_endpoint_services() -> None:
    """Test successfull calls as well as the next_token arg."""
    ec2 = boto3.client("ec2", region_name="us-west-1")

    # Verify the major components of the response. The unit test for filters
    # verifies the contents of some of the ServicesDetails entries, so the
    # focus of this unit test will be the larger components of the response.
    all_services = ec2.describe_vpc_endpoint_services()
    assert set(all_services.keys()) == set(
        ["ServiceNames", "ServiceDetails", "ResponseMetadata"]
    )
    assert len(all_services["ServiceDetails"]) == len(all_services["ServiceNames"])
    all_names = [x["ServiceName"] for x in all_services["ServiceDetails"]]
    assert set(all_names) == set(all_services["ServiceNames"])

    # Verify the handling of the next token.
    partial_services = ec2.describe_vpc_endpoint_services(MaxResults=2)
    assert len(partial_services["ServiceDetails"]) == 2
    assert len(partial_services["ServiceNames"]) == 2
    assert all_names[0] == partial_services["ServiceNames"][0]
    assert all_names[1] == partial_services["ServiceNames"][1]
    assert all_names[0] == partial_services["ServiceDetails"][0]["ServiceName"]
    assert all_names[1] == partial_services["ServiceDetails"][1]["ServiceName"]
    assert (
        partial_services["NextToken"]
        == (all_services["ServiceDetails"][2]["ServiceId"])
    )

    # Use the next token to receive another service.
    more_services = ec2.describe_vpc_endpoint_services(
        MaxResults=1, NextToken=partial_services["NextToken"]
    )
    assert len(more_services["ServiceDetails"]) == 1
    assert len(more_services["ServiceNames"]) == 1
    assert all_names[2] == more_services["ServiceNames"][0]
    assert all_names[2] == more_services["ServiceDetails"][0]["ServiceName"]
    assert more_services["NextToken"] == all_services["ServiceDetails"][3]["ServiceId"]

    # Use the next token to receive the remaining services.
    remaining_services = ec2.describe_vpc_endpoint_services(
        NextToken=more_services["NextToken"]
    )
    assert len(remaining_services["ServiceDetails"]) == len(all_names) - 3
    assert "NextToken" not in remaining_services

    # Extract one service and verify all the fields.  This time the data is
    # extracted from the actual response.
    config_service = ec2.describe_vpc_endpoint_services(
        ServiceNames=["com.amazonaws.us-west-1.config"]
    )
    details = config_service["ServiceDetails"][0]
    assert details["AcceptanceRequired"] is False
    assert details["AvailabilityZones"] == ["us-west-1a", "us-west-1b"]
    assert details["BaseEndpointDnsNames"] == ["config.us-west-1.vpce.amazonaws.com"]
    assert details["ManagesVpcEndpoints"] is False
    assert details["Owner"] == "amazon"
    assert details["PrivateDnsName"] == "config.us-west-1.amazonaws.com"
    if LooseVersion(boto3_version) > LooseVersion("1.29.0"):
        # Attribute wasn't available in older botocore versions
        assert details["PrivateDnsNames"] == [
            {"PrivateDnsName": "config.us-west-1.amazonaws.com"}
        ]
    assert details["PrivateDnsNameVerificationState"] == "verified"
    assert details["ServiceName"] == "com.amazonaws.us-west-1.config"
    assert details["ServiceType"] == [{"ServiceType": "Interface"}]
    assert details["VpcEndpointPolicySupported"] is True
