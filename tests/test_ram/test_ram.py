import re
import time
from datetime import datetime

import boto3
from botocore.exceptions import ClientError
import pytest

from moto import mock_ram, mock_organizations
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID


@mock_ram
def test_create_resource_share():
    # given
    client = boto3.client("ram", region_name="us-east-1")

    # when
    response = client.create_resource_share(name="test")

    # then
    resource = response["resourceShare"]
    assert resource["allowExternalPrincipals"] is True
    assert isinstance(resource["creationTime"], datetime)
    assert isinstance(resource["lastUpdatedTime"], datetime)
    assert resource["name"] == "test"
    assert resource["owningAccountId"] == ACCOUNT_ID
    assert re.match(
        (
            r"arn:aws:ram:us-east-1:\d{12}:resource-share"
            r"/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
        ),
        resource["resourceShareArn"],
    )
    assert resource["status"] == "ACTIVE"
    assert "featureSet" not in resource

    # creating a resource share with the name should result in a second one
    # not overwrite/update the old one
    # when
    response = client.create_resource_share(
        name="test",
        allowExternalPrincipals=False,
        resourceArns=[
            f"arn:aws:ec2:us-east-1:{ACCOUNT_ID}:transit-gateway/tgw-123456789"
        ],
    )

    # then
    resource = response["resourceShare"]
    assert resource["allowExternalPrincipals"] is False
    assert isinstance(resource["creationTime"], datetime)
    assert isinstance(resource["lastUpdatedTime"], datetime)
    assert resource["name"] == "test"
    assert resource["owningAccountId"] == ACCOUNT_ID
    assert re.match(
        (
            r"arn:aws:ram:us-east-1:\d{12}:resource-share"
            r"/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
        ),
        resource["resourceShareArn"],
    )
    assert resource["status"] == "ACTIVE"

    response = client.get_resource_shares(resourceOwner="SELF")
    assert len(response["resourceShares"]) == 2


@mock_ram
def test_create_resource_share_errors():
    # given
    client = boto3.client("ram", region_name="us-east-1")

    # invalid ARN
    # when
    with pytest.raises(ClientError) as e:
        client.create_resource_share(name="test", resourceArns=["inalid-arn"])
    ex = e.value
    assert ex.operation_name == "CreateResourceShare"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "MalformedArnException" in ex.response["Error"]["Code"]
    assert ex.response["Error"]["Message"] == (
        "The specified resource ARN inalid-arn is not valid. "
        "Verify the ARN and try again."
    )

    # valid ARN, but not shareable resource type
    # when
    with pytest.raises(ClientError) as e:
        client.create_resource_share(
            name="test", resourceArns=[f"arn:aws:iam::{ACCOUNT_ID}:role/test"]
        )
    ex = e.value
    assert ex.operation_name == "CreateResourceShare"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "MalformedArnException" in ex.response["Error"]["Code"]
    assert (
        ex.response["Error"]["Message"]
        == "You cannot share the selected resource type."
    )

    # invalid principal ID
    # when
    with pytest.raises(ClientError) as e:
        client.create_resource_share(
            name="test",
            principals=["invalid"],
            resourceArns=[
                f"arn:aws:ec2:us-east-1:{ACCOUNT_ID}:transit-gateway/tgw-123456789"
            ],
        )
    ex = e.value
    assert ex.operation_name == "CreateResourceShare"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "InvalidParameterException" in ex.response["Error"]["Code"]
    assert ex.response["Error"]["Message"] == (
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
            f"arn:aws:ec2:us-east-1:{ACCOUNT_ID}:transit-gateway/tgw-123456789"
        ],
    )

    # then
    assert response["resourceShare"]["name"] == "test"

    # share in an OU
    # when
    response = client.create_resource_share(
        name="test",
        principals=[ou_arn],
        resourceArns=[
            f"arn:aws:ec2:us-east-1:{ACCOUNT_ID}:transit-gateway/tgw-123456789"
        ],
    )

    # then
    assert response["resourceShare"]["name"] == "test"


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
    with pytest.raises(ClientError) as e:
        client.create_resource_share(
            name="test",
            principals=[f"arn:aws:organizations::{ACCOUNT_ID}:organization/o-unknown"],
            resourceArns=[
                f"arn:aws:ec2:us-east-1:{ACCOUNT_ID}:transit-gateway/tgw-123456789"
            ],
        )
    ex = e.value
    assert ex.operation_name == "CreateResourceShare"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "UnknownResourceException" in ex.response["Error"]["Code"]
    assert ex.response["Error"]["Message"] == (
        "Organization o-unknown could not be found."
    )

    # unknown OU
    # when
    with pytest.raises(ClientError) as e:
        client.create_resource_share(
            name="test",
            principals=[f"arn:aws:organizations::{ACCOUNT_ID}:ou/o-unknown/ou-unknown"],
            resourceArns=[
                f"arn:aws:ec2:us-east-1:{ACCOUNT_ID}:transit-gateway/tgw-123456789"
            ],
        )
    ex = e.value
    assert ex.operation_name == "CreateResourceShare"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "UnknownResourceException" in ex.response["Error"]["Code"]
    assert ex.response["Error"]["Message"] == (
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
    assert len(response["resourceShares"]) == 1
    resource = response["resourceShares"][0]
    assert resource["allowExternalPrincipals"] is True
    assert isinstance(resource["creationTime"], datetime)
    assert resource["featureSet"] == "STANDARD"
    assert isinstance(resource["lastUpdatedTime"], datetime)
    assert resource["name"] == "test"
    assert resource["owningAccountId"] == ACCOUNT_ID
    assert re.match(
        (
            r"arn:aws:ram:us-east-1:\d{12}:resource-share"
            r"/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
        ),
        resource["resourceShareArn"],
    )
    assert resource["status"] == "ACTIVE"


@mock_ram
def test_get_resource_shares_errors():
    # given
    client = boto3.client("ram", region_name="us-east-1")

    # invalid resource owner
    # when
    with pytest.raises(ClientError) as e:
        client.get_resource_shares(resourceOwner="invalid")
    ex = e.value
    assert ex.operation_name == "GetResourceShares"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "InvalidParameterException" in ex.response["Error"]["Code"]
    assert ex.response["Error"]["Message"] == (
        "invalid is not a valid resource owner. "
        "Specify either SELF or OTHER-ACCOUNTS and try again."
    )


@mock_ram
def test_update_resource_share():
    # given
    client = boto3.client("ram", region_name="us-east-1")
    arn = client.create_resource_share(name="test")["resourceShare"]["resourceShareArn"]

    # when
    time.sleep(0.1)
    response = client.update_resource_share(resourceShareArn=arn, name="test-update")

    # then
    resource = response["resourceShare"]
    assert resource["allowExternalPrincipals"] is True
    assert resource["name"] == "test-update"
    assert resource["owningAccountId"] == ACCOUNT_ID
    assert re.match(
        (
            r"arn:aws:ram:us-east-1:\d{12}:resource-share"
            r"/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
        ),
        resource["resourceShareArn"],
    )
    assert resource["status"] == "ACTIVE"
    assert "featureSet" not in resource
    creation_time = resource["creationTime"]
    assert resource["lastUpdatedTime"] > creation_time

    response = client.get_resource_shares(resourceOwner="SELF")
    assert len(response["resourceShares"]) == 1


@mock_ram
def test_update_resource_share_errors():
    # given
    client = boto3.client("ram", region_name="us-east-1")

    # invalid resource owner
    # when
    with pytest.raises(ClientError) as e:
        client.update_resource_share(
            resourceShareArn=f"arn:aws:ram:us-east-1:{ACCOUNT_ID}:resource-share/not-existing",
            name="test-update",
        )
    ex = e.value
    assert ex.operation_name == "UpdateResourceShare"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "UnknownResourceException" in ex.response["Error"]["Code"]
    assert ex.response["Error"]["Message"] == (
        f"ResourceShare arn:aws:ram:us-east-1:{ACCOUNT_ID}"
        ":resource-share/not-existing could not be found."
    )


@mock_ram
def test_delete_resource_share():
    # given
    client = boto3.client("ram", region_name="us-east-1")
    arn = client.create_resource_share(name="test")["resourceShare"]["resourceShareArn"]

    # when
    time.sleep(0.1)
    response = client.delete_resource_share(resourceShareArn=arn)

    # then
    assert response["returnValue"] is True

    response = client.get_resource_shares(resourceOwner="SELF")
    assert len(response["resourceShares"]) == 1
    resource = response["resourceShares"][0]
    assert resource["status"] == "DELETED"
    creation_time = resource["creationTime"]
    assert resource["lastUpdatedTime"] > creation_time


@mock_ram
def test_delete_resource_share_errors():
    # given
    client = boto3.client("ram", region_name="us-east-1")

    # invalid resource owner
    # when
    with pytest.raises(ClientError) as e:
        client.delete_resource_share(
            resourceShareArn=f"arn:aws:ram:us-east-1:{ACCOUNT_ID}:resource-share/not-existing"
        )
    ex = e.value
    assert ex.operation_name == "DeleteResourceShare"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "UnknownResourceException" in ex.response["Error"]["Code"]
    assert ex.response["Error"]["Message"] == (
        f"ResourceShare arn:aws:ram:us-east-1:{ACCOUNT_ID}"
        ":resource-share/not-existing could not be found."
    )


@mock_ram
@mock_organizations
def test_enable_sharing_with_aws_organization():
    # given
    client = boto3.client("organizations", region_name="us-east-1")
    client.create_organization(FeatureSet="ALL")
    client = boto3.client("ram", region_name="us-east-1")

    # when
    response = client.enable_sharing_with_aws_organization()

    # then
    assert response["returnValue"] is True


@mock_ram
@mock_organizations
def test_enable_sharing_with_aws_organization_errors():
    # given
    client = boto3.client("ram", region_name="us-east-1")

    # no Organization defined
    # when
    with pytest.raises(ClientError) as e:
        client.enable_sharing_with_aws_organization()
    ex = e.value
    assert ex.operation_name == "EnableSharingWithAwsOrganization"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "OperationNotPermittedException" in ex.response["Error"]["Code"]
    assert ex.response["Error"]["Message"] == (
        "Unable to enable sharing with AWS Organizations. "
        "Received AccessDeniedException from AWSOrganizations with the "
        "following error message: "
        "You don't have permissions to access this resource."
    )
