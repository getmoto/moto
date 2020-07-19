from datetime import datetime

import boto3
import sure  # noqa
from botocore.exceptions import ClientError
from nose.tools import assert_raises

from moto import mock_ram, mock_organizations


@mock_ram
def test_create_resource_share():
    # given
    client = boto3.client("ram", region_name="us-east-1")

    # when
    response = client.create_resource_share(name="test")

    # then
    resource = response["resourceShare"]
    resource["allowExternalPrincipals"].should.be.ok
    resource["creationTime"].should.be.a(datetime)
    resource["lastUpdatedTime"].should.be.a(datetime)
    resource["name"].should.equal("test")
    resource["owningAccountId"].should.equal("123456789012")
    resource["resourceShareArn"].should.match(
        r"arn:aws:ram:us-east-1:123456789012:resource-share/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
    )
    resource["status"].should.equal("ACTIVE")
    resource.should_not.have.key("featureSet")

    # creating a resource share with the name should result in a second one
    # not overwrite/update the old one
    # when
    response = client.create_resource_share(
        name="test",
        allowExternalPrincipals=False,
        resourceArns=[
            "arn:aws:ec2:us-east-1:123456789012:transit-gateway/tgw-123456789"
        ],
    )

    # then
    resource = response["resourceShare"]
    resource["allowExternalPrincipals"].should_not.be.ok
    resource["creationTime"].should.be.a(datetime)
    resource["lastUpdatedTime"].should.be.a(datetime)
    resource["name"].should.equal("test")
    resource["owningAccountId"].should.equal("123456789012")
    resource["resourceShareArn"].should.match(
        r"arn:aws:ram:us-east-1:123456789012:resource-share/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
    )
    resource["status"].should.equal("ACTIVE")

    response = client.get_resource_shares(resourceOwner="SELF")
    response["resourceShares"].should.have.length_of(2)


@mock_ram
def test_create_resource_share_errors():
    # given
    client = boto3.client("ram", region_name="us-east-1")

    # invalid ARN
    # when
    with assert_raises(ClientError) as e:
        client.create_resource_share(name="test", resourceArns=["inalid-arn"])
    ex = e.exception
    ex.operation_name.should.equal("CreateResourceShare")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("MalformedArnException")
    ex.response["Error"]["Message"].should.equal(
        "The specified resource ARN inalid-arn is not valid. "
        "Verify the ARN and try again."
    )

    # valid ARN, but not shareable resource type
    # when
    with assert_raises(ClientError) as e:
        client.create_resource_share(
            name="test", resourceArns=["arn:aws:iam::123456789012:role/test"]
        )
    ex = e.exception
    ex.operation_name.should.equal("CreateResourceShare")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("MalformedArnException")
    ex.response["Error"]["Message"].should.equal(
        "You cannot share the selected resource type."
    )

    # invalid principal ID
    # when
    with assert_raises(ClientError) as e:
        client.create_resource_share(
            name="test",
            principals=["invalid"],
            resourceArns=[
                "arn:aws:ec2:us-east-1:123456789012:transit-gateway/tgw-123456789"
            ],
        )
    ex = e.exception
    ex.operation_name.should.equal("CreateResourceShare")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("InvalidParameterException")
    ex.response["Error"]["Message"].should.equal(
        "Principal ID invalid is malformed. Verify the ID and try again."
    )


@mock_ram
@mock_organizations
def test_create_resource_share_with_organization():
    # given
    client = boto3.client("organizations", region_name="us-east-1")
    org_arn = client.create_organization(FeatureSet="ALL")["Organization"]["Arn"]
    root_id = client.list_roots()["Roots"][0]["Id"]
    ou_arn = client.create_organizational_unit(ParentId=root_id, Name="test")[
        "OrganizationalUnit"
    ]["Arn"]
    client = boto3.client("ram", region_name="us-east-1")

    # share in whole Organization
    # when
    response = client.create_resource_share(
        name="test",
        principals=[org_arn],
        resourceArns=[
            "arn:aws:ec2:us-east-1:123456789012:transit-gateway/tgw-123456789"
        ],
    )

    # then
    response["resourceShare"]["name"].should.equal("test")

    # share in an OU
    # when
    response = client.create_resource_share(
        name="test",
        principals=[ou_arn],
        resourceArns=[
            "arn:aws:ec2:us-east-1:123456789012:transit-gateway/tgw-123456789"
        ],
    )

    # then
    response["resourceShare"]["name"].should.equal("test")


@mock_ram
@mock_organizations
def test_create_resource_share_with_organization_errors():
    # given
    client = boto3.client("organizations", region_name="us-east-1")
    client.create_organization(FeatureSet="ALL")
    root_id = client.list_roots()["Roots"][0]["Id"]
    client.create_organizational_unit(ParentId=root_id, Name="test")
    client = boto3.client("ram", region_name="us-east-1")

    # unknown Organization
    # when
    with assert_raises(ClientError) as e:
        client.create_resource_share(
            name="test",
            principals=["arn:aws:organizations::123456789012:organization/o-unknown"],
            resourceArns=[
                "arn:aws:ec2:us-east-1:123456789012:transit-gateway/tgw-123456789"
            ],
        )
    ex = e.exception
    ex.operation_name.should.equal("CreateResourceShare")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("UnknownResourceException")
    ex.response["Error"]["Message"].should.equal(
        "Organization o-unknown could not be found."
    )

    # unknown OU
    # when
    with assert_raises(ClientError) as e:
        client.create_resource_share(
            name="test",
            principals=["arn:aws:organizations::123456789012:ou/o-unknown/ou-unknown"],
            resourceArns=[
                "arn:aws:ec2:us-east-1:123456789012:transit-gateway/tgw-123456789"
            ],
        )
    ex = e.exception
    ex.operation_name.should.equal("CreateResourceShare")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("UnknownResourceException")
    ex.response["Error"]["Message"].should.equal(
        "OrganizationalUnit ou-unknown in unknown organization could not be found."
    )


@mock_ram
def test_get_resource_shares():
    # given
    client = boto3.client("ram", region_name="us-east-1")
    client.create_resource_share(name="test")

    # when
    response = client.get_resource_shares(resourceOwner="SELF")

    # then
    response["resourceShares"].should.have.length_of(1)
    resource = response["resourceShares"][0]
    resource["allowExternalPrincipals"].should.be.ok
    resource["creationTime"].should.be.a(datetime)
    resource["featureSet"].should.equal("STANDARD")
    resource["lastUpdatedTime"].should.be.a(datetime)
    resource["name"].should.equal("test")
    resource["owningAccountId"].should.equal("123456789012")
    resource["resourceShareArn"].should.match(
        r"arn:aws:ram:us-east-1:123456789012:resource-share/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
    )
    resource["status"].should.equal("ACTIVE")


@mock_ram
def test_get_resource_shares_errors():
    # given
    client = boto3.client("ram", region_name="us-east-1")

    # invalid resource owner
    # when
    with assert_raises(ClientError) as e:
        client.get_resource_shares(resourceOwner="invalid")
    ex = e.exception
    ex.operation_name.should.equal("GetResourceShares")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("InvalidParameterException")
    ex.response["Error"]["Message"].should.equal(
        "invalid is not a valid resource owner. "
        "Specify either SELF or OTHER-ACCOUNTS and try again."
    )
