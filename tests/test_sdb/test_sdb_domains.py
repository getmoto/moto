import boto3
import pytest

from botocore.exceptions import ClientError
from moto import mock_sdb


@mock_sdb
@pytest.mark.parametrize("name", ["", "a", "a#", "aaa#", "as@asdff", "asf'qwer"])
def test_create_domain_invalid(name):
    # Error handling is always the same
    sdb = boto3.client("sdb", region_name="eu-west-1")
    with pytest.raises(ClientError) as exc:
        sdb.create_domain(DomainName=name)
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParameterValue"
    assert err["Message"] == f"Value ({name}) for parameter DomainName is invalid. "
    assert "BoxUsage" in err


@mock_sdb
@pytest.mark.parametrize(
    "name", ["abc", "ABc", "a00", "as-df", "jk_kl", "qw.rt", "asfljaejadslfsl"]
)
def test_create_domain_valid(name):
    # a-z, A-Z, 0-9, '_', '-', and '.'
    sdb = boto3.client("sdb", region_name="eu-west-1")
    sdb.create_domain(DomainName=name)


@mock_sdb
def test_create_domain_and_list():
    sdb = boto3.client("sdb", region_name="eu-west-1")
    sdb.create_domain(DomainName="mydomain")

    all_domains = sdb.list_domains()["DomainNames"]
    assert all_domains == ["mydomain"]


@mock_sdb
def test_delete_domain():
    sdb = boto3.client("sdb", region_name="eu-west-1")
    sdb.create_domain(DomainName="mydomain")
    sdb.delete_domain(DomainName="mydomain")

    all_domains = sdb.list_domains()
    assert "DomainNames" not in all_domains


@mock_sdb
def test_delete_domain_unknown():
    sdb = boto3.client("sdb", region_name="eu-west-1")
    sdb.delete_domain(DomainName="unknown")

    all_domains = sdb.list_domains()
    assert "DomainNames" not in all_domains


@mock_sdb
def test_delete_domain_invalid():
    sdb = boto3.client("sdb", region_name="eu-west-1")
    with pytest.raises(ClientError) as exc:
        sdb.delete_domain(DomainName="a")
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParameterValue"
    assert err["Message"] == "Value (a) for parameter DomainName is invalid. "
    assert "BoxUsage" in err
