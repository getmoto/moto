"""Unit tests specific to VPC endpoint services."""
# boto3 tests are defined in `tests/test_core/test_ec2_vpc_endpoint_services`

from moto import mock_ec2
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID


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
