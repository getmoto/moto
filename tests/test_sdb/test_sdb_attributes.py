import boto3
import pytest
import sure  # noqa # pylint: disable=unused-import

from botocore.exceptions import ClientError
from moto import mock_sdb


@mock_sdb
def test_put_attributes_unknown_domain():
    sdb = boto3.client("sdb", region_name="eu-west-1")
    with pytest.raises(ClientError) as exc:
        sdb.put_attributes(
            DomainName="aaaa", ItemName="asdf", Attributes=[{"Name": "a", "Value": "b"}]
        )
    err = exc.value.response["Error"]
    err["Code"].should.equal("NoSuchDomain")
    err["Message"].should.equal("The specified domain does not exist.")
    err.should.have.key("BoxUsage")


@mock_sdb
def test_put_attributes_invalid_domain():
    sdb = boto3.client("sdb", region_name="eu-west-1")
    with pytest.raises(ClientError) as exc:
        sdb.put_attributes(
            DomainName="a", ItemName="asdf", Attributes=[{"Name": "a", "Value": "b"}]
        )
    err = exc.value.response["Error"]
    err["Code"].should.equal("InvalidParameterValue")
    err["Message"].should.equal("Value (a) for parameter DomainName is invalid. ")
    err.should.have.key("BoxUsage")


@mock_sdb
def test_get_attributes_unknown_domain():
    sdb = boto3.client("sdb", region_name="eu-west-1")
    with pytest.raises(ClientError) as exc:
        sdb.get_attributes(DomainName="aaaa", ItemName="asdf")
    err = exc.value.response["Error"]
    err["Code"].should.equal("NoSuchDomain")
    err["Message"].should.equal("The specified domain does not exist.")
    err.should.have.key("BoxUsage")


@mock_sdb
def test_get_attributes_invalid_domain():
    sdb = boto3.client("sdb", region_name="eu-west-1")
    with pytest.raises(ClientError) as exc:
        sdb.get_attributes(DomainName="a", ItemName="asdf")
    err = exc.value.response["Error"]
    err["Code"].should.equal("InvalidParameterValue")
    err["Message"].should.equal("Value (a) for parameter DomainName is invalid. ")
    err.should.have.key("BoxUsage")


@mock_sdb
def test_put_and_get_attributes():
    name = "mydomain"
    sdb = boto3.client("sdb", region_name="eu-west-1")
    sdb.create_domain(DomainName=name)

    sdb.put_attributes(
        DomainName=name, ItemName="asdf", Attributes=[{"Name": "a", "Value": "b"}]
    )

    attrs = sdb.get_attributes(DomainName=name, ItemName="asdf")["Attributes"]
    attrs.should.equal([{"Name": "a", "Value": "b"}])


@mock_sdb
def test_put_multiple_and_get_attributes():
    name = "mydomain"
    sdb = boto3.client("sdb", region_name="eu-west-1")
    sdb.create_domain(DomainName=name)

    sdb.put_attributes(
        DomainName=name, ItemName="asdf", Attributes=[{"Name": "a", "Value": "b"}]
    )
    sdb.put_attributes(
        DomainName=name, ItemName="jklp", Attributes=[{"Name": "a", "Value": "val"}]
    )
    sdb.put_attributes(
        DomainName=name, ItemName="asdf", Attributes=[{"Name": "a", "Value": "c"}]
    )
    sdb.put_attributes(
        DomainName=name, ItemName="asdf", Attributes=[{"Name": "d", "Value": "e"}]
    )

    attrs = sdb.get_attributes(DomainName=name, ItemName="asdf")["Attributes"]
    attrs.should.equal(
        [
            {"Name": "a", "Value": "b"},
            {"Name": "a", "Value": "c"},
            {"Name": "d", "Value": "e"},
        ]
    )

    attrs = sdb.get_attributes(DomainName=name, ItemName="jklp")["Attributes"]
    attrs.should.equal([{"Name": "a", "Value": "val"}])


@mock_sdb
def test_put_replace_and_get_attributes():
    name = "mydomain"
    sdb = boto3.client("sdb", region_name="eu-west-1")
    sdb.create_domain(DomainName=name)

    sdb.put_attributes(
        DomainName=name, ItemName="asdf", Attributes=[{"Name": "a", "Value": "b"}]
    )
    sdb.put_attributes(
        DomainName=name, ItemName="asdf", Attributes=[{"Name": "a", "Value": "c"}]
    )
    sdb.put_attributes(
        DomainName=name, ItemName="asdf", Attributes=[{"Name": "d", "Value": "e"}]
    )
    sdb.put_attributes(
        DomainName=name,
        ItemName="asdf",
        Attributes=[
            {"Name": "a", "Value": "f", "Replace": True},
            {"Name": "d", "Value": "g"},
        ],
    )

    attrs = sdb.get_attributes(DomainName=name, ItemName="asdf")["Attributes"]
    attrs.should.have.length_of(3)
    attrs.should.contain({"Name": "a", "Value": "f"})
    attrs.should.contain({"Name": "d", "Value": "e"})
    attrs.should.contain({"Name": "d", "Value": "g"})


@mock_sdb
def test_put_and_get_multiple_attributes():
    name = "mydomain"
    sdb = boto3.client("sdb", region_name="eu-west-1")
    sdb.create_domain(DomainName=name)

    sdb.put_attributes(
        DomainName=name,
        ItemName="asdf",
        Attributes=[{"Name": "a", "Value": "b"}, {"Name": "attr2", "Value": "myvalue"}],
    )

    attrs = sdb.get_attributes(DomainName=name, ItemName="asdf")["Attributes"]
    attrs.should.equal(
        [{"Name": "a", "Value": "b"}, {"Name": "attr2", "Value": "myvalue"}]
    )


@mock_sdb
def test_get_attributes_by_name():
    name = "mydomain"
    sdb = boto3.client("sdb", region_name="eu-west-1")
    sdb.create_domain(DomainName=name)

    sdb.put_attributes(
        DomainName=name,
        ItemName="asdf",
        Attributes=[{"Name": "a", "Value": "b"}, {"Name": "attr2", "Value": "myvalue"}],
    )

    attrs = sdb.get_attributes(
        DomainName=name, ItemName="asdf", AttributeNames=["attr2"]
    )["Attributes"]
    attrs.should.equal([{"Name": "attr2", "Value": "myvalue"}])
