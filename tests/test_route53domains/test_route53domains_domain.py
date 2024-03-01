from datetime import datetime, timedelta, timezone
from typing import Dict

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws


@pytest.fixture(name="domain_parameters")
def generate_domain_parameters() -> Dict:
    return {
        "DomainName": "domain.com",
        "DurationInYears": 3,
        "AutoRenew": True,
        "AdminContact": {
            "FirstName": "First",
            "LastName": "Last",
            "ContactType": "PERSON",
            "AddressLine1": "address 1",
            "AddressLine2": "address 2",
            "City": "New York City",
            "CountryCode": "US",
            "ZipCode": "123123123",
            "Email": "email@gmail.com",
            "Fax": "+1.1234567890",
        },
        "RegistrantContact": {
            "FirstName": "First",
            "LastName": "Last",
            "ContactType": "PERSON",
            "AddressLine1": "address 1",
            "AddressLine2": "address 2",
            "City": "New York City",
            "CountryCode": "US",
            "ZipCode": "123123123",
            "Email": "email@gmail.com",
            "Fax": "+1.1234567890",
        },
        "TechContact": {
            "FirstName": "First",
            "LastName": "Last",
            "ContactType": "PERSON",
            "AddressLine1": "address 1",
            "AddressLine2": "address 2",
            "City": "New York City",
            "CountryCode": "US",
            "ZipCode": "123123123",
            "Email": "email@gmail.com",
            "Fax": "+1.1234567890",
        },
        "PrivacyProtectAdminContact": True,
        "PrivacyProtectRegistrantContact": True,
        "PrivacyProtectTechContact": True,
    }


@pytest.fixture(name="invalid_domain_parameters")
def generate_invalid_domain_parameters(domain_parameters: Dict) -> Dict:
    domain_parameters["DomainName"] = "a"
    domain_parameters["DurationInYears"] = 500
    return domain_parameters


@mock_aws
def test_route53domains_register_domain(domain_parameters: Dict):
    route53domains_client = boto3.client("route53domains", region_name="global")
    res = route53domains_client.register_domain(**domain_parameters)

    operation_id = res["OperationId"]

    operations = route53domains_client.list_operations()["Operations"]
    for operation in operations:
        if operation["OperationId"] == operation_id:
            return

    assert operation_id in [
        operation["OperationId"] for operation in operations
    ], "Could not find expected operation id returned from `register_domain` in operation list"


@mock_aws
def test_route53domains_register_domain_creates_hosted_zone(
    domain_parameters: Dict,
):
    """Test good register domain API calls."""
    route53domains_client = boto3.client("route53domains", region_name="global")
    route53_client = boto3.client("route53", region_name="global")
    route53domains_client.register_domain(**domain_parameters)

    res = route53_client.list_hosted_zones()
    assert "domain.com" in [
        zone["Name"] for zone in res["HostedZones"]
    ], "`register_domain` did not create a new hosted zone with the same name"


@mock_aws
def test_route53domains_register_domain_fails_on_invalid_input(
    invalid_domain_parameters: Dict,
):
    route53domains_client = boto3.client("route53domains", region_name="global")
    route53_client = boto3.client("route53", region_name="global")
    with pytest.raises(ClientError) as exc:
        route53domains_client.register_domain(**invalid_domain_parameters)

    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidInput"

    res = route53_client.list_hosted_zones()
    assert len(res["HostedZones"]) == 0


@mock_aws
def test_route53domains_register_domain_fails_on_invalid_tld(domain_parameters: Dict):
    route53domains_client = boto3.client("route53domains", region_name="global")
    route53_client = boto3.client("route53", region_name="global")

    domain_parameters["DomainName"] = "test.non-existing-tld"
    with pytest.raises(ClientError) as exc:
        route53domains_client.register_domain(**domain_parameters)

    err = exc.value.response["Error"]
    assert err["Code"] == "UnsupportedTLD"

    res = route53_client.list_hosted_zones()
    assert len(res["HostedZones"]) == 0


@mock_aws
def test_route53domains_list_operations(domain_parameters: Dict):
    route53domains_client = boto3.client("route53domains", region_name="global")
    route53domains_client.register_domain(**domain_parameters)

    operations = route53domains_client.list_operations()["Operations"]
    assert len(operations) == 1

    future_time = datetime.now(timezone.utc) + timedelta(minutes=1)
    operations = route53domains_client.list_operations(
        SubmittedSince=future_time.timestamp()
    )["Operations"]
    assert len(operations) == 0

    operations = route53domains_client.list_operations(Status=["SUCCESSFUL"])[
        "Operations"
    ]
    assert len(operations) == 1

    operations = route53domains_client.list_operations(Status=["IN_PROGRESS"])[
        "Operations"
    ]
    assert len(operations) == 0

    operations = route53domains_client.list_operations(Type=["REGISTER_DOMAIN"])[
        "Operations"
    ]
    assert len(operations) == 1

    operations = route53domains_client.list_operations(Type=["DELETE_DOMAIN"])[
        "Operations"
    ]
    assert len(operations) == 0


@mock_aws
def test_list_operations_invalid_input():
    route53domains_client = boto3.client("route53domains", region_name="global")
    with pytest.raises(ClientError) as exc:
        _ = route53domains_client.list_operations(Type=["INVALID_TYPE"])["Operations"]

    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidInput"

    with pytest.raises(ClientError) as exc:
        _ = route53domains_client.list_operations(Status=["INVALID_STATUS"])[
            "Operations"
        ]
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidInput"


@mock_aws
def test_list_operations_marker(domain_parameters: Dict):
    route53domains_client = boto3.client("route53domains", region_name="global")
    domain_params = domain_parameters.copy()
    route53domains_client.register_domain(**domain_params)
    domain_params["DomainName"] = "seconddomain.com"
    route53domains_client.register_domain(**domain_params)
    domain_params["DomainName"] = "thirddomain.com"
    route53domains_client.register_domain(**domain_params)
    operations_res = route53domains_client.list_operations()
    assert len(operations_res["Operations"]) == 3
    operations_res = route53domains_client.list_operations(Marker="0", MaxItems=1)
    assert len(operations_res["Operations"]) == 1
    operations_res = route53domains_client.list_operations(
        Marker=operations_res["NextPageMarker"]
    )
    assert len(operations_res["Operations"]) == 2


@mock_aws
def test_duplicate_requests(domain_parameters: Dict):
    route53domains_client = boto3.client("route53domains", region_name="global")
    route53domains_client.register_domain(**domain_parameters)
    with pytest.raises(ClientError) as exc:
        route53domains_client.register_domain(**domain_parameters)
    err = exc.value.response["Error"]
    assert err["Code"] == "DuplicateRequest"


@mock_aws
def test_domain_limit(domain_parameters: Dict):
    route53domains_client = boto3.client("route53domains", region_name="global")
    params = domain_parameters.copy()
    for i in range(20):
        params["DomainName"] = f"domain-{i}.com"
        route53domains_client.register_domain(**params)

    params["DomainName"] = "domain-20.com"
    with pytest.raises(ClientError) as exc:
        route53domains_client.register_domain(**params)

    err = exc.value.response["Error"]
    assert err["Code"] == "DomainLimitExceeded"


@mock_aws
def test_get_domain_detail(domain_parameters: Dict):
    route53domains_client = boto3.client("route53domains", region_name="global")
    route53domains_client.register_domain(**domain_parameters)
    res = route53domains_client.get_domain_detail(DomainName=domain_parameters["DomainName"])
    assert res["DomainName"] == domain_parameters["DomainName"]


@mock_aws
def test_get_invalid_domain_detail(domain_parameters: Dict):
    route53domains_client = boto3.client("route53domains", region_name="global")
    route53domains_client.register_domain(**domain_parameters)
    with pytest.raises(ClientError) as exc:
        route53domains_client.get_domain_detail(DomainName="not-a-domain")

    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidInput"

    with pytest.raises(ClientError) as exc:
        route53domains_client.get_domain_detail(DomainName="test.non-existing-tld")

    err = exc.value.response["Error"]
    assert err["Code"] == "UnsupportedTLD"
