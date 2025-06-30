import json
import re
import time
from datetime import datetime

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
from moto.ram.utils import AWS_MANAGED_PERMISSIONS, RAM_RESOURCE_TYPES


@mock_aws
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


@mock_aws
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


@mock_aws
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


@mock_aws
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


@mock_aws
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


@mock_aws
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


@mock_aws
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


@mock_aws
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


@mock_aws
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


@mock_aws
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


@mock_aws
def test_enable_sharing_with_aws_organization():
    # given
    client = boto3.client("organizations", region_name="us-east-1")
    client.create_organization(FeatureSet="ALL")
    client = boto3.client("ram", region_name="us-east-1")

    # when
    response = client.enable_sharing_with_aws_organization()

    # then
    assert response["returnValue"] is True


@mock_aws
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


@mock_aws
def test_get_resource_share_associations_with_principals():
    # given
    client = boto3.client("ram", region_name="us-east-1")
    response = client.create_resource_share(
        name="test",
        principals=["123456789012"],
        resourceArns=[
            f"arn:aws:ec2:us-east-1:{ACCOUNT_ID}:transit-gateway/tgw-123456789"
        ],
    )
    resource_share_arn = response["resourceShare"]["resourceShareArn"]

    # when
    response = client.get_resource_share_associations(
        associationType="PRINCIPAL", resourceShareArns=[resource_share_arn]
    )

    # then
    assert len(response["resourceShareAssociations"]) == 1
    association = response["resourceShareAssociations"][0]
    assert association["resourceShareArn"] == resource_share_arn
    assert association["resourceShareName"] == "test"
    assert association["associatedEntity"] == "123456789012"
    assert association["associationType"] == "PRINCIPAL"
    assert association["status"] == "ASSOCIATED"
    assert isinstance(association["creationTime"], datetime)
    assert isinstance(association["lastUpdatedTime"], datetime)
    assert association["external"] is False


@mock_aws
def test_get_resource_share_associations_with_resources():
    # given
    client = boto3.client("ram", region_name="us-east-1")
    resource_arn = f"arn:aws:ec2:us-east-1:{ACCOUNT_ID}:transit-gateway/tgw-123456789"
    response = client.create_resource_share(
        name="test",
        principals=["123456789012"],
        resourceArns=[resource_arn],
    )
    resource_share_arn = response["resourceShare"]["resourceShareArn"]

    # when
    response = client.get_resource_share_associations(
        associationType="RESOURCE", resourceShareArns=[resource_share_arn]
    )

    # then
    assert len(response["resourceShareAssociations"]) == 1
    association = response["resourceShareAssociations"][0]
    assert association["resourceShareArn"] == resource_share_arn
    assert association["resourceShareName"] == "test"
    assert association["associatedEntity"] == resource_arn
    assert association["associationType"] == "RESOURCE"
    assert association["status"] == "ASSOCIATED"
    assert isinstance(association["creationTime"], datetime)
    assert isinstance(association["lastUpdatedTime"], datetime)
    assert association["external"] is False


@mock_aws
def test_get_resource_share_associations_with_filters():
    # given
    client = boto3.client("ram", region_name="us-east-1")
    resource_arn = f"arn:aws:ec2:us-east-1:{ACCOUNT_ID}:transit-gateway/tgw-123456789"
    response = client.create_resource_share(
        name="test",
        principals=["123456789012"],
        resourceArns=[resource_arn],
    )

    # when filtering by principal
    response = client.get_resource_share_associations(
        associationType="PRINCIPAL", principal="123456789012"
    )

    # then
    assert len(response["resourceShareAssociations"]) == 1
    assert (
        response["resourceShareAssociations"][0]["associatedEntity"] == "123456789012"
    )

    # when filtering by resource
    response = client.get_resource_share_associations(
        associationType="RESOURCE", resourceArn=resource_arn
    )

    # then
    assert len(response["resourceShareAssociations"]) == 1
    assert response["resourceShareAssociations"][0]["associatedEntity"] == resource_arn


@mock_aws
def test_get_resource_share_associations_errors():
    # given
    client = boto3.client("ram", region_name="us-east-1")
    resource_arn = f"arn:aws:ec2:us-east-1:{ACCOUNT_ID}:transit-gateway/tgw-123456789"
    client.create_resource_share(
        name="test",
        principals=["123456789012"],
        resourceArns=[resource_arn],
    )

    # when invalid association type
    with pytest.raises(ClientError) as e:
        client.get_resource_share_associations(associationType="INVALID")
    ex = e.value
    assert ex.operation_name == "GetResourceShareAssociations"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "InvalidParameterException" in ex.response["Error"]["Code"]
    assert "is not a valid association type" in ex.response["Error"]["Message"]

    # when invalid association status
    with pytest.raises(ClientError) as e:
        client.get_resource_share_associations(
            associationType="PRINCIPAL", associationStatus="INVALID"
        )
    ex = e.value
    assert ex.operation_name == "GetResourceShareAssociations"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "InvalidParameterException" in ex.response["Error"]["Code"]
    assert "is not a valid association status" in ex.response["Error"]["Message"]

    # when resource ARN with PRINCIPAL type
    with pytest.raises(ClientError) as e:
        client.get_resource_share_associations(
            associationType="PRINCIPAL", resourceArn=resource_arn
        )
    ex = e.value
    assert ex.operation_name == "GetResourceShareAssociations"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "InvalidParameterException" in ex.response["Error"]["Code"]
    assert (
        "You cannot specify a resource ARN when the association type is PRINCIPAL"
        in ex.response["Error"]["Message"]
    )

    # when principal with RESOURCE type
    with pytest.raises(ClientError) as e:
        client.get_resource_share_associations(
            associationType="RESOURCE", principal="123456789012"
        )
    ex = e.value
    assert ex.operation_name == "GetResourceShareAssociations"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "InvalidParameterException" in ex.response["Error"]["Code"]
    assert (
        "You cannot specify a principal when the association type is RESOURCE"
        in ex.response["Error"]["Message"]
    )


@mock_aws
@pytest.mark.parametrize(
    "resource_region_scope, expect_error, error_message",
    [
        ({}, False, None),  # default value is "ALL"
        ({"resourceRegionScope": "ALL"}, False, None),
        ({"resourceRegionScope": "GLOBAL"}, False, None),
        ({"resourceRegionScope": "REGIONAL"}, False, None),
        (
            {"resourceRegionScope": "INVALID"},
            True,
            "INVALID is not a valid resource region scope value. Specify a valid value and try again.",
        ),
    ],
    ids=[
        "default_region_scope",
        "all_region_scope",
        "global_region_scope",
        "regional_region_scope",
        "invalid_region_scope",
    ],
)
def test_list_resource_types(resource_region_scope, expect_error, error_message):
    client = boto3.client("ram", region_name="us-east-1")
    region_scope = resource_region_scope.get("resourceRegionScope")

    if expect_error:
        with pytest.raises(ClientError) as e:
            client.list_resource_types(**resource_region_scope)
        ex = e.value
        assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
        assert "InvalidParameterException" in ex.response["Error"]["Code"]
        assert ex.response["Error"]["Message"] == error_message
    else:
        response = client.list_resource_types(**resource_region_scope)
        expected_types = RAM_RESOURCE_TYPES
        if region_scope == "GLOBAL":
            expected_types = [
                rt for rt in expected_types if rt["resourceRegionScope"] == "GLOBAL"
            ]
        elif region_scope == "REGIONAL":
            expected_types = [
                rt for rt in expected_types if rt["resourceRegionScope"] == "REGIONAL"
            ]

        assert "resourceTypes" in response
        assert response["resourceTypes"] == expected_types


@mock_aws
@pytest.mark.parametrize(
    "parameters, expect_error, error_message",
    [
        ({}, False, None),
        ({"resourceType": "glue:catalog"}, False, None),
        ({"permissionType": "ALL"}, False, None),
        ({"resourceType": "glue:catalog", "permissionType": "AWS"}, False, None),
        (
            {"resourceType": "gluE:catalog", "permissionType": "AWS"},
            True,
            "Invalid resource type: gluE:catalog",
        ),
        (
            {"resourceType": "glue:catalog", "permissionType": "INVALID"},
            True,
            "INVALID is not a valid scope. Must be one of: ALL, AWS, LOCAL.",
        ),
    ],
    ids=[
        "default_params",
        "valid_resource_type",
        "valid_permission_type",
        "valid_resource_type_and_permission_type",
        "invalid_resource_type",
        "invalid_permission_type",
    ],
)
def test_list_permissions(parameters, expect_error, error_message):
    client = boto3.client("ram", region_name="us-east-1")
    permission_types_relation = {
        "AWS": "AWS_MANAGED",
        "LOCAL": "CUSTOMER_MANAGED",
    }
    resource_type = parameters.get("resourceType")
    permission_type = parameters.get("permissionType")

    # when
    if expect_error:
        with pytest.raises(ClientError) as e:
            client.list_permissions(**parameters)
        ex = e.value
        assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
        assert "InvalidParameterException" in ex.response["Error"]["Code"]
        assert ex.response["Error"]["Message"] == error_message
    else:
        response = client.list_permissions(**parameters)

        # then
        expected_permissions = AWS_MANAGED_PERMISSIONS
        if resource_type:
            expected_permissions = [
                permission
                for permission in expected_permissions
                if permission["resourceType"].lower() == resource_type.lower()
            ]

        if permission_type and permission_type != "ALL":
            expected_permissions = [
                permission
                for permission in expected_permissions
                if permission_types_relation.get(permission_type)
                == permission["permissionType"]
            ]

        assert "permissions" in response
        assert json.dumps(response["permissions"], default=str) == json.dumps(
            expected_permissions, default=str
        )
