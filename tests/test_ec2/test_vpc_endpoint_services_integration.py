"""Unit tests specific to VPC endpoint services."""
import pytest

import boto3
from botocore.exceptions import ClientError

from moto import mock_ec2, settings
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
from unittest import SkipTest


@mock_ec2
def test_describe_vpc_endpoint_services_bad_args():
    if settings.TEST_SERVER_MODE:
        # Long-running operation - doesn't quite work in ServerMode, with parallel tests
        # Probably needs some locking to force the initialization to only occur once
        raise SkipTest("Can't run in ServerMode")
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


def fake_endpoint_services():
    """Return a dummy list of default VPC endpoint services."""
    return [
        {
            "AcceptanceRequired": False,
            "AvailabilityZones": ["us-west-1a", "us-west-1b"],
            "BaseEndpointDnsNames": ["access-analyzer.us-west-1.vpce.amazonaws.com"],
            "ManagesVpcEndpoints": False,
            "Owner": "amazon",
            "PrivateDnsName": "access-analyzer.us-west-1.amazonaws.com",
            "PrivateDnsNameVerificationState": "verified",
            "PrivateDnsNames": [
                {"PrivateDnsName": "access-analyzer.us-west-1.amazonaws.com"},
            ],
            "ServiceId": "vpce-svc-1",
            "ServiceName": "com.amazonaws.us-west-1.access-analyzer",
            "ServiceType": [{"ServiceType": "Interface"}],
            "Tags": [],
            "VpcEndpointPolicySupported": True,
        },
        {
            "AcceptanceRequired": False,
            "AvailabilityZones": ["us-west-1a", "us-west-1b"],
            "BaseEndpointDnsNames": ["config.us-west-1.vpce.amazonaws.com"],
            "ManagesVpcEndpoints": False,
            "Owner": "amazon",
            "PrivateDnsName": "config.us-west-1.amazonaws.com",
            "PrivateDnsNameVerificationState": "verified",
            "PrivateDnsNames": [{"PrivateDnsName": "config.us-west-1.amazonaws.com"}],
            "ServiceId": "vpce-svc-2",
            "ServiceName": "com.amazonaws.us-west-1.config",
            "ServiceType": [{"ServiceType": "Interface"}],
            "Tags": [],
            "VpcEndpointPolicySupported": True,
        },
        {
            "AcceptanceRequired": True,
            "AvailabilityZones": ["us-west-1a", "us-west-1b"],
            "BaseEndpointDnsNames": ["s3.us-west-1.amazonaws.com"],
            "ManagesVpcEndpoints": True,
            "Owner": "amazon",
            "ServiceId": "vpce-svc-3",
            "ServiceName": "com.amazonaws.us-west-1.s3",
            "ServiceType": [{"ServiceType": "Gateway"}],
            "Tags": [{"Key": "Name", "Value": "s3_gw"}],
            "VpcEndpointPolicySupported": False,
        },
        {
            "AcceptanceRequired": False,
            "AvailabilityZones": ["us-west-1a", "us-west-1b"],
            "BaseEndpointDnsNames": ["s3.us-west-1.vpce.amazonaws.com"],
            "ManagesVpcEndpoints": False,
            "Owner": "amazon",
            "ServiceId": "vpce-svc-4",
            "ServiceName": "com.amazonaws.us-west-1.s3",
            "ServiceType": [{"ServiceType": "Interface"}],
            "Tags": [
                {"Key": "Name", "Value": "s3_if"},
                {"Key": "Environ", "Value": "test"},
            ],
            "VpcEndpointPolicySupported": True,
        },
    ]


def validate_s3_service_endpoint_gateway(details):
    """Validate response contains appropriate s3 Gateway service details."""
    assert details["AcceptanceRequired"] is True
    assert details["AvailabilityZones"] == ["us-west-1a", "us-west-1b"]
    assert details["BaseEndpointDnsNames"] == ["s3.us-west-1.amazonaws.com"]
    assert details["ManagesVpcEndpoints"] is True
    assert details["Owner"] == "amazon"
    assert details["ServiceId"] == "vpce-svc-3"
    assert details["ServiceName"] == "com.amazonaws.us-west-1.s3"
    assert details["ServiceType"] == [{"ServiceType": "Gateway"}]
    assert details["VpcEndpointPolicySupported"] is False
    assert details["Tags"][0] == {"Key": "Name", "Value": "s3_gw"}


def validate_s3_service_endpoint_interface(details):
    """Validate response contains appropriate s3 Gateway service details."""
    assert details["AcceptanceRequired"] is False
    assert details["AvailabilityZones"] == ["us-west-1a", "us-west-1b"]
    assert details["BaseEndpointDnsNames"] == ["s3.us-west-1.vpce.amazonaws.com"]
    assert details["ManagesVpcEndpoints"] is False
    assert details["Owner"] == "amazon"
    assert details["ServiceId"] == "vpce-svc-4"
    assert details["ServiceName"] == "com.amazonaws.us-west-1.s3"
    assert details["ServiceType"] == [{"ServiceType": "Interface"}]
    assert details["VpcEndpointPolicySupported"] is True
    assert details["Tags"][0] == {"Key": "Name", "Value": "s3_if"}
    assert details["Tags"][1] == {"Key": "Environ", "Value": "test"}


@mock_ec2
def test_describe_vpc_endpoint_services_filters():
    """Verify that different type of filters return the expected results."""
    from moto.ec2.models import ec2_backends  # pylint: disable=import-outside-toplevel

    ec2_backend = ec2_backends[ACCOUNT_ID]["us-west-1"]
    test_data = fake_endpoint_services()

    # Allow access to _filter_endpoint_services as it provides the best
    # means of testing this logic.
    # pylint: disable=protected-access

    # Test a service name filter, using s3 as the service name.
    filtered_services = ec2_backend._filter_endpoint_services(
        ["com.amazonaws.us-west-1.s3"], [], test_data
    )
    assert len(filtered_services) == 2
    validate_s3_service_endpoint_gateway(filtered_services[0])
    validate_s3_service_endpoint_interface(filtered_services[1])

    # Test a service type filter.
    filtered_services = ec2_backend._filter_endpoint_services(
        [], [{"Name": "service-type", "Value": ["Gateway"]}], test_data
    )
    assert len(filtered_services) == 1
    validate_s3_service_endpoint_gateway(filtered_services[0])

    # Test a tag key/value filter.
    filtered_services = ec2_backend._filter_endpoint_services(
        [], [{"Name": "tag-key", "Value": ["Name"]}], test_data
    )
    assert len(filtered_services) == 2
    validate_s3_service_endpoint_gateway(filtered_services[0])
    validate_s3_service_endpoint_interface(filtered_services[1])

    # Test a tag key filter.
    filtered_services = ec2_backend._filter_endpoint_services(
        [], [{"Name": "tag:Environ", "Value": ["test"]}], test_data
    )
    assert len(filtered_services) == 1
    validate_s3_service_endpoint_interface(filtered_services[0])

    # Test when there are no filters.
    filtered_services = ec2_backend._filter_endpoint_services([], [], test_data)
    assert len(filtered_services) == 4

    # Test a combo of service name and multiple filters.
    filtered_services = ec2_backend._filter_endpoint_services(
        ["com.amazonaws.us-west-1.s3"],
        [{"Name": "tag:Environ", "Value": ["test"]}],
        test_data,
    )
    assert len(filtered_services) == 1
    validate_s3_service_endpoint_interface(filtered_services[0])


@mock_ec2
def test_describe_vpc_default_endpoint_services():
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
    assert partial_services["NextToken"] == (
        all_services["ServiceDetails"][2]["ServiceId"]
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
    assert details["PrivateDnsNames"] == [
        {"PrivateDnsName": "config.us-west-1.amazonaws.com"}
    ]
    assert details["PrivateDnsNameVerificationState"] == "verified"
    assert details["ServiceName"] == "com.amazonaws.us-west-1.config"
    assert details["ServiceType"] == [{"ServiceType": "Interface"}]
    assert details["VpcEndpointPolicySupported"] is True
