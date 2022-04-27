import boto3
import pytest
import sure  # noqa # pylint: disable=unused-import

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
    err["Code"].should.equal("InvalidParameterValue")
    err["Message"].should.equal(f"Value ({name}) for parameter DomainName is invalid. ")
    err.should.have.key("BoxUsage")


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
    all_domains.should.equal(["mydomain"])


@mock_sdb
def test_delete_domain():
    sdb = boto3.client("sdb", region_name="eu-west-1")
    sdb.create_domain(DomainName="mydomain")
    sdb.delete_domain(DomainName="mydomain")

    all_domains = sdb.list_domains()
    all_domains.shouldnt.have.key("DomainNames")


@mock_sdb
def test_delete_domain_unknown():
    sdb = boto3.client("sdb", region_name="eu-west-1")
    sdb.delete_domain(DomainName="unknown")

    all_domains = sdb.list_domains()
    all_domains.shouldnt.have.key("DomainNames")


@mock_sdb
def test_delete_domain_invalid():
    sdb = boto3.client("sdb", region_name="eu-west-1")
    with pytest.raises(ClientError) as exc:
        sdb.delete_domain(DomainName="a")
    err = exc.value.response["Error"]
    err["Code"].should.equal("InvalidParameterValue")
    err["Message"].should.equal("Value (a) for parameter DomainName is invalid. ")
    err.should.have.key("BoxUsage")
