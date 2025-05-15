from datetime import datetime, timedelta, timezone
from typing import Dict, List

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
def test_register_domain(domain_parameters: Dict):
    route53domains_client = boto3.client("route53domains", region_name="global")
    res = route53domains_client.register_domain(**domain_parameters)

    operation_id = res["OperationId"]

    operations = route53domains_client.list_operations(Type=["REGISTER_DOMAIN"])[
        "Operations"
    ]
    for operation in operations:
        if operation["OperationId"] == operation_id:
            return

    assert (
        operation_id in [operation["OperationId"] for operation in operations]
    ), "Could not find expected operation id returned from `register_domain` in operation list"


@mock_aws
def test_register_domain_creates_hosted_zone(
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
def test_register_domain_fails_on_invalid_input(
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
def test_register_domain_fails_on_invalid_tld(domain_parameters: Dict):
    route53domains_client = boto3.client("route53domains", region_name="global")
    route53_client = boto3.client("route53", region_name="global")

    params = domain_parameters.copy()
    params["DomainName"] = "test.non-existing-tld"
    with pytest.raises(ClientError) as exc:
        route53domains_client.register_domain(**params)

    err = exc.value.response["Error"]
    assert err["Code"] == "UnsupportedTLD"

    res = route53_client.list_hosted_zones()
    assert len(res["HostedZones"]) == 0


@mock_aws
def test_list_operations(domain_parameters: Dict):
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
def test_get_operation_detail(domain_parameters: Dict):
    route53domains_client = boto3.client("route53domains", region_name="global")
    res = route53domains_client.register_domain(**domain_parameters)
    expected_operation_id = res["OperationId"]
    operation = route53domains_client.get_operation_detail(
        OperationId=expected_operation_id
    )
    assert operation["OperationId"] == expected_operation_id
    assert operation["Status"] == "SUCCESSFUL"
    assert operation["Type"] == "REGISTER_DOMAIN"


@mock_aws
def test_get_nonexistent_operation_detail():
    route53domains_client = boto3.client("route53domains", region_name="global")
    with pytest.raises(ClientError) as exc:
        route53domains_client.get_operation_detail(
            OperationId="non-exiting-operation-id"
        )

    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidInput"


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
    res = route53domains_client.get_domain_detail(
        DomainName=domain_parameters["DomainName"]
    )
    assert res["DomainName"] == domain_parameters["DomainName"]


@mock_aws
def test_get_invalid_domain_detail(domain_parameters):
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


@mock_aws
def test_list_domains(domain_parameters: Dict):
    route53domains_client = boto3.client("route53domains", region_name="global")
    route53domains_client.register_domain(**domain_parameters)
    res = route53domains_client.list_domains()

    assert len(res["Domains"]) == 1
    params = domain_parameters.copy()
    params["DomainName"] = "new-domain.com"
    route53domains_client.register_domain(**params)
    res = route53domains_client.list_domains()
    assert len(res["Domains"]) == 2


@mock_aws
@pytest.mark.parametrize(
    "filters,expected_domains_len",
    [
        (
            [
                {
                    "Name": "DomainName",
                    "Operator": "BEGINS_WITH",
                    "Values": ["some-non-registered-domain.com"],
                }
            ],
            0,  # expected_domains_len
        ),
        (
            [
                {
                    "Name": "DomainName",
                    "Operator": "BEGINS_WITH",
                    "Values": ["domain.com"],
                }
            ],
            1,  # expected_domains_len
        ),
        (
            [
                {
                    "Name": "Expiry",
                    "Operator": "GE",
                    "Values": [
                        str(
                            datetime.fromisocalendar(
                                year=2012, week=20, day=3
                            ).timestamp()
                        )
                    ],
                }
            ],
            1,  # expected_domains_len
        ),
        (
            [
                {
                    "Name": "Expiry",
                    "Operator": "GE",
                    "Values": [
                        str(
                            datetime.fromisocalendar(
                                year=2050, week=20, day=3
                            ).timestamp()
                        )
                    ],
                }
            ],
            0,  # expected_domains_len
        ),
    ],
)
def test_list_domains_filters(
    domain_parameters: Dict, filters: List[Dict], expected_domains_len: int
):
    route53domains_client = boto3.client("route53domains", region_name="global")
    route53domains_client.register_domain(**domain_parameters)
    res = route53domains_client.list_domains(FilterConditions=filters)
    assert len(res["Domains"]) == expected_domains_len


@mock_aws
def test_list_domains_sort_condition(domain_parameters: Dict):
    route53domains_client = boto3.client("route53domains", region_name="global")
    params = domain_parameters.copy()
    params["DomainName"] = "adomain.com"
    route53domains_client.register_domain(**params)
    params["DomainName"] = "bdomain.com"
    route53domains_client.register_domain(**params)
    sort = {"Name": "DomainName", "SortOrder": "DES"}
    res = route53domains_client.list_domains(SortCondition=sort)
    domains = res["Domains"]
    assert domains[0]["DomainName"] == "bdomain.com"
    assert domains[1]["DomainName"] == "adomain.com"

    sort = {"Name": "Expiry", "SortOrder": "ASC"}
    res = route53domains_client.list_domains(SortCondition=sort)
    domains = res["Domains"]
    assert domains[0]["DomainName"] == "adomain.com"
    assert domains[1]["DomainName"] == "bdomain.com"


@mock_aws
def test_list_domains_invalid_filter(domain_parameters: Dict):
    route53domains_client = boto3.client("route53domains", region_name="global")
    route53domains_client.register_domain(**domain_parameters)
    filters = [
        {
            "Name": "InvalidField",
            "Operator": "InvalidOperator",
            "Values": ["value-1", "value-2"],  # multiple values isn't supported
        }
    ]

    with pytest.raises(ClientError) as exc:
        route53domains_client.list_domains(FilterConditions=filters)

    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidInput"


@mock_aws
def test_list_domains_invalid_sort_condition(domain_parameters: Dict):
    route53domains_client = boto3.client("route53domains", region_name="global")
    route53domains_client.register_domain(**domain_parameters)
    sort = {
        "Name": "InvalidField",
        "SortOrder": "InvalidOrder",
    }

    with pytest.raises(ClientError) as exc:
        route53domains_client.list_domains(SortCondition=sort)

    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidInput"


@mock_aws
def test_list_domains_sort_condition_not_the_same_as_filter_condition(
    domain_parameters: Dict,
):
    route53domains_client = boto3.client("route53domains", region_name="global")
    route53domains_client.register_domain(**domain_parameters)
    sort = {
        "Name": "Expiry",
        "SortOrder": "ASC",
    }
    filters = [
        {
            "Name": "DomainName",
            "Operator": "BEGINS_WITH",
            "Values": ["domain.com"],
        }
    ]

    with pytest.raises(ClientError) as exc:
        route53domains_client.list_domains(FilterConditions=filters, SortCondition=sort)

    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidInput"


@mock_aws
def test_delete_domain(domain_parameters: Dict):
    route53domains_client = boto3.client("route53domains", region_name="global")
    route53domains_client.register_domain(**domain_parameters)
    domains = route53domains_client.list_domains()["Domains"]
    assert len(domains) == 1
    route53domains_client.delete_domain(DomainName=domain_parameters["DomainName"])
    domains = route53domains_client.list_domains()["Domains"]
    assert len(domains) == 0
    operations = route53domains_client.list_operations(Type=["DELETE_DOMAIN"])[
        "Operations"
    ]
    assert len(operations) == 1


@mock_aws
def test_delete_invalid_domain(domain_parameters: Dict):
    route53domains_client = boto3.client("route53domains", region_name="global")
    domains = route53domains_client.list_domains()["Domains"]
    assert len(domains) == 0
    with pytest.raises(ClientError) as exc:
        route53domains_client.delete_domain(DomainName=domain_parameters["DomainName"])

    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidInput"


@mock_aws
@pytest.mark.parametrize(
    "nameservers",
    [
        [{"Name": "1-nameserver.net"}, {"Name": "2-nameserver.net"}],
        [
            {"Name": "3-nameserver.net", "GlueIps": ["1.1.1.2"]},
            {"Name": "4-nameserver.net", "GlueIps": ["1.1.1.1"]},
        ],
    ],
)
def test_update_domain_nameservers(domain_parameters: Dict, nameservers: List[Dict]):
    route53domains_client = boto3.client("route53domains", region_name="global")
    route53domains_client.register_domain(**domain_parameters)
    operation_id = route53domains_client.update_domain_nameservers(
        DomainName=domain_parameters["DomainName"], Nameservers=nameservers
    )["OperationId"]
    domain = route53domains_client.get_domain_detail(
        DomainName=domain_parameters["DomainName"]
    )
    assert domain["Nameservers"] == nameservers
    operation = route53domains_client.get_operation_detail(OperationId=operation_id)
    assert operation["Type"] == "UPDATE_NAMESERVER"
    assert operation["Status"] == "SUCCESSFUL"


@mock_aws
@pytest.mark.parametrize(
    "nameservers",
    [
        [{"Name": "1-nameserver.net", "GlueIps": ["1.1.1.1", "1.1.1.2"]}],
        [
            {
                "Name": "1-nameserver.net",
                "GlueIps": [
                    "2001:0db8:85a3:0000:0000:8a2e:0370:7334",
                    "2001:0db8:85a3:0000:0000:8a2e:0370:7334",
                ],
            }
        ],
        [
            {
                "Name": "1-nameserver.net",
                "GlueIps": [
                    "2001:0db8:85a3:0000:0000:8a2e:0370:7334",
                    "2001:0db8:85a3:0000:0000:8a2e:0370:7334",
                    "1.1.1.1",
                ],
            }
        ],
        [
            {
                "Name": "1-nameserver.net",
                "GlueIps": [
                    "2001:0db8:85a3:0000:0000:8a2e:0370:7334",
                    "2001:0db8:85a3:0000:0000:8a2e:0370:7334",
                    "1.1.1.1",
                    "1.1.1.2",
                ],
            }
        ],
        [
            {
                "Name": "1-nameserver.net",
                "GlueIps": [
                    "2001:0db8:85a3:0000:0000:8a2e:0370:7334",
                    "1.1.1.1",
                    "not-an-ip-address",
                ],
            }
        ],
    ],
)
def test_update_domain_nameservers_with_multiple_glue_ips(
    domain_parameters: Dict, nameservers: List[Dict]
):
    route53domains_client = boto3.client("route53domains", region_name="global")
    route53domains_client.register_domain(**domain_parameters)
    with pytest.raises(ClientError) as exc:
        route53domains_client.update_domain_nameservers(
            DomainName=domain_parameters["DomainName"], Nameservers=nameservers
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidInput"


@mock_aws
def test_update_domain_nameservers_requires_glue_ips(domain_parameters: Dict):
    route53domains_client = boto3.client("route53domains", region_name="global")
    route53domains_client.register_domain(**domain_parameters)
    domain_name = domain_parameters["DomainName"]
    nameservers = [{"Name": f"subdomain.{domain_name}"}]
    with pytest.raises(ClientError) as exc:
        route53domains_client.update_domain_nameservers(
            DomainName=domain_parameters["DomainName"], Nameservers=nameservers
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidInput"


@mock_aws
def test_update_domain_nameservers_for_nonexistent_domain():
    route53domains_client = boto3.client("route53domains", region_name="global")
    nameservers = [{"Name": "1-nameserver.net"}, {"Name": "2-nameserver.net"}]

    with pytest.raises(ClientError) as exc:
        route53domains_client.update_domain_nameservers(
            DomainName="non-existent-domain.com", Nameservers=nameservers
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidInput"
