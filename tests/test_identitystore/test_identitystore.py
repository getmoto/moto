"""Unit tests for identitystore-supported APIs."""
import random
import string
from uuid import UUID, uuid4

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_identitystore
from moto.moto_api._internal import mock_random


# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


def get_identity_store_id() -> str:
    rand = "".join(random.choices(string.ascii_lowercase, k=10))
    return f"d-{rand}"


@mock_identitystore
def test_create_group():
    client = boto3.client("identitystore", region_name="us-east-2")
    identity_store_id = get_identity_store_id()
    create_resp = client.create_group(
        IdentityStoreId=identity_store_id,
        DisplayName="test_group",
        Description="description",
    )
    assert create_resp["IdentityStoreId"] == identity_store_id
    assert UUID(create_resp["GroupId"])


@mock_identitystore
def test_create_group_duplicate_name():
    client = boto3.client("identitystore", region_name="us-east-2")
    identity_store_id = get_identity_store_id()
    create_resp = client.create_group(
        IdentityStoreId=identity_store_id,
        DisplayName="test_group",
        Description="description",
    )
    assert create_resp["IdentityStoreId"] == identity_store_id
    assert UUID(create_resp["GroupId"])

    with pytest.raises(ClientError) as exc:
        client.create_group(
            IdentityStoreId=identity_store_id,
            DisplayName="test_group",
            Description="description",
        )
    err = exc.value
    assert "ConflictException" in str(type(err))
    assert (
        str(err)
        == "An error occurred (ConflictException) when calling the CreateGroup operation: Duplicate GroupDisplayName"
    )
    assert err.operation_name == "CreateGroup"
    assert err.response["Error"]["Code"] == "ConflictException"
    assert err.response["Error"]["Message"] == "Duplicate GroupDisplayName"
    assert err.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert err.response["Message"] == "Duplicate GroupDisplayName"
    assert err.response["Reason"] == "UNIQUENESS_CONSTRAINT_VIOLATION"


@mock_identitystore
def test_group_multiple_identity_stores():
    identity_store_id = get_identity_store_id()
    identity_store_id2 = get_identity_store_id()
    client = boto3.client("identitystore", region_name="us-east-2")
    group1 = __create_test_group(client, store_id=identity_store_id)
    group2 = __create_test_group(client, store_id=identity_store_id2)

    assert __group_exists(client, group1[0], store_id=identity_store_id)
    assert not __group_exists(client, group1[0], store_id=identity_store_id2)

    assert __group_exists(client, group2[0], store_id=identity_store_id2)
    assert not __group_exists(client, group2[0], store_id=identity_store_id)


@mock_identitystore
def test_create_group_membership():
    client = boto3.client("identitystore", region_name="us-east-2")
    identity_store_id = get_identity_store_id()

    group_id = client.create_group(
        IdentityStoreId=identity_store_id,
        DisplayName="test_group",
        Description="description",
    )["GroupId"]

    user_id = __create_and_verify_sparse_user(client, identity_store_id)["UserId"]

    create_response = client.create_group_membership(
        IdentityStoreId=identity_store_id,
        GroupId=group_id,
        MemberId={"UserId": user_id},
    )
    assert UUID(create_response["MembershipId"])
    assert create_response["IdentityStoreId"] == identity_store_id

    list_response = client.list_group_memberships(
        IdentityStoreId=identity_store_id, GroupId=group_id
    )
    assert len(list_response["GroupMemberships"]) == 1
    assert (
        list_response["GroupMemberships"][0]["MembershipId"]
        == create_response["MembershipId"]
    )
    assert list_response["GroupMemberships"][0]["MemberId"]["UserId"] == user_id


@mock_identitystore
def test_create_duplicate_username():
    client = boto3.client("identitystore", region_name="us-east-2")
    identity_store_id = get_identity_store_id()

    # This should succeed
    client.create_user(
        IdentityStoreId=identity_store_id,
        UserName="deleteme_username",
        DisplayName="deleteme_displayname",
        Name={"GivenName": "Givenname", "FamilyName": "Familyname"},
    )

    with pytest.raises(ClientError) as exc:
        # This should fail
        client.create_user(
            IdentityStoreId=identity_store_id,
            UserName="deleteme_username",
            DisplayName="deleteme_displayname",
            Name={"GivenName": "Givenname", "FamilyName": "Familyname"},
        )
    err = exc.value
    assert "ConflictException" in str(type(err))
    assert (
        str(err)
        == "An error occurred (ConflictException) when calling the CreateUser operation: Duplicate UserName"
    )
    assert err.operation_name == "CreateUser"
    assert err.response["Error"]["Code"] == "ConflictException"
    assert err.response["Error"]["Message"] == "Duplicate UserName"
    assert err.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert err.response["Message"] == "Duplicate UserName"
    assert err.response["Reason"] == "UNIQUENESS_CONSTRAINT_VIOLATION"


@mock_identitystore
def test_create_username_no_username():
    client = boto3.client("identitystore", region_name="us-east-2")
    identity_store_id = get_identity_store_id()

    with pytest.raises(ClientError) as exc:
        client.create_user(IdentityStoreId=identity_store_id)
    err = exc.value
    assert "ValidationException" in str(type(err))
    assert (
        str(err)
        == "An error occurred (ValidationException) when calling the CreateUser operation: userName is a required attribute"
    )
    assert err.operation_name == "CreateUser"
    assert err.response["Error"]["Code"] == "ValidationException"
    assert err.response["Error"]["Message"] == "userName is a required attribute"
    assert err.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert err.response["Message"] == "userName is a required attribute"


@mock_identitystore
def test_create_username_missing_required_attributes():
    client = boto3.client("identitystore", region_name="us-east-2")
    identity_store_id = get_identity_store_id()

    with pytest.raises(ClientError) as exc:
        client.create_user(
            IdentityStoreId=identity_store_id, UserName="username", Name={}
        )
    err = exc.value
    assert "ValidationException" in str(type(err))
    assert (
        str(err)
        == "An error occurred (ValidationException) when calling the CreateUser operation: displayname: The attribute displayname is required, name: The attribute name is required"
    )
    assert err.operation_name == "CreateUser"
    assert err.response["Error"]["Code"] == "ValidationException"
    assert (
        err.response["Error"]["Message"]
        == "displayname: The attribute displayname is required, name: The attribute name is required"
    )
    assert err.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert (
        err.response["Message"]
        == "displayname: The attribute displayname is required, name: The attribute name is required"
    )


@mock_identitystore
@pytest.mark.parametrize(
    "field, missing", [("GivenName", "familyname"), ("FamilyName", "givenname")]
)
def test_create_username_missing_required_name_field(field, missing):
    client = boto3.client("identitystore", region_name="us-east-2")
    identity_store_id = get_identity_store_id()

    with pytest.raises(ClientError) as exc:
        client.create_user(
            IdentityStoreId=identity_store_id,
            UserName="username",
            DisplayName="displayName",
            Name={field: field},
        )
    err = exc.value
    assert "ValidationException" in str(type(err))
    assert (
        str(err)
        == f"An error occurred (ValidationException) when calling the CreateUser operation: {missing}: The attribute {missing} is required"
    )
    assert err.operation_name == "CreateUser"
    assert err.response["Error"]["Code"] == "ValidationException"
    assert (
        err.response["Error"]["Message"]
        == f"{missing}: The attribute {missing} is required"
    )
    assert err.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert err.response["Message"] == f"{missing}: The attribute {missing} is required"


@mock_identitystore
def test_create_describe_sparse_user():
    client = boto3.client("identitystore", region_name="us-east-2")
    identity_store_id = get_identity_store_id()
    response = client.create_user(
        IdentityStoreId=identity_store_id,
        UserName="the_username",
        DisplayName="display_name",
        Name={"GivenName": "given_name", "FamilyName": "family_name"},
    )
    assert UUID(response["UserId"])

    user_resp = client.describe_user(
        IdentityStoreId=identity_store_id, UserId=response["UserId"]
    )

    assert user_resp["UserName"] == "the_username"
    assert user_resp["DisplayName"] == "display_name"
    assert "Name" in user_resp
    assert user_resp["Name"]["GivenName"] == "given_name"
    assert user_resp["Name"]["FamilyName"] == "family_name"


@mock_identitystore
def test_create_describe_full_user():
    client = boto3.client("identitystore", region_name="us-east-2")
    identity_store_id = get_identity_store_id()
    response = client.create_user(
        IdentityStoreId=identity_store_id,
        UserName="the_username",
        DisplayName="display_name",
        Name={
            "Formatted": "formatted_name",
            "GivenName": "given_name",
            "FamilyName": "family_name",
            "MiddleName": "middle_name",
            "HonorificPrefix": "The Honorable",
            "HonorificSuffix": "Wisest of us all",
        },
        NickName="nick_name",
        ProfileUrl="https://example.com",
        Emails=[
            {"Value": "email1@example.com", "Type": "Personal", "Primary": True},
            {"Value": "email2@example.com", "Type": "Work", "Primary": False},
        ],
        Addresses=[
            {
                "StreetAddress": "123 Address St.",
                "Locality": "locality",
                "Region": "region",
                "PostalCode": "123456",
                "Country": "USA",
                "Formatted": "123 Address St.\nlocality, region, 123456",
                "Type": "Home",
                "Primary": True,
            },
        ],
        PhoneNumbers=[
            {"Value": "555-456-7890", "Type": "Home", "Primary": True},
        ],
        UserType="user_type",
        Title="title",
        PreferredLanguage="preferred_language",
        Locale="locale",
        Timezone="timezone",
    )
    assert UUID(response["UserId"])

    user_resp = client.describe_user(
        IdentityStoreId=identity_store_id, UserId=response["UserId"]
    )

    assert user_resp["UserName"] == "the_username"
    assert user_resp["DisplayName"] == "display_name"
    assert "Name" in user_resp
    assert user_resp["Name"]["Formatted"] == "formatted_name"
    assert user_resp["Name"]["GivenName"] == "given_name"
    assert user_resp["Name"]["FamilyName"] == "family_name"
    assert user_resp["Name"]["MiddleName"] == "middle_name"
    assert user_resp["Name"]["HonorificPrefix"] == "The Honorable"
    assert user_resp["Name"]["HonorificSuffix"] == "Wisest of us all"
    assert user_resp["NickName"] == "nick_name"
    assert user_resp["ProfileUrl"] == "https://example.com"
    assert "Emails" in user_resp
    assert len(user_resp["Emails"]) == 2
    email1 = user_resp["Emails"][0]
    assert email1["Value"] == "email1@example.com"
    assert email1["Type"] == "Personal"
    assert email1["Primary"] is True
    email2 = user_resp["Emails"][1]
    assert email2["Value"] == "email2@example.com"
    assert email2["Type"] == "Work"
    assert email2["Primary"] is False
    assert "Addresses" in user_resp
    assert len(user_resp["Addresses"]) == 1
    assert user_resp["Addresses"][0]["StreetAddress"] == "123 Address St."
    assert user_resp["Addresses"][0]["Locality"] == "locality"
    assert user_resp["Addresses"][0]["Region"] == "region"
    assert user_resp["Addresses"][0]["PostalCode"] == "123456"
    assert user_resp["Addresses"][0]["Country"] == "USA"
    assert (
        user_resp["Addresses"][0]["Formatted"]
        == "123 Address St.\nlocality, region, 123456"
    )
    assert user_resp["Addresses"][0]["Type"] == "Home"
    assert user_resp["Addresses"][0]["Primary"] is True
    assert "PhoneNumbers" in user_resp
    assert len(user_resp["PhoneNumbers"]) == 1
    assert user_resp["PhoneNumbers"][0]["Value"] == "555-456-7890"
    assert user_resp["PhoneNumbers"][0]["Type"] == "Home"
    assert user_resp["PhoneNumbers"][0]["Primary"] is True
    assert user_resp["UserType"] == "user_type"
    assert user_resp["Title"] == "title"
    assert user_resp["PreferredLanguage"] == "preferred_language"
    assert user_resp["Locale"] == "locale"
    assert user_resp["Timezone"] == "timezone"


@mock_identitystore
def test_describe_user_doesnt_exist():
    client = boto3.client("identitystore", region_name="us-east-2")
    identity_store_id = get_identity_store_id()

    with pytest.raises(ClientError) as exc:
        client.describe_user(
            IdentityStoreId=identity_store_id, UserId=str(mock_random.uuid4())
        )

    err = exc.value
    assert err.response["Error"]["Code"] == "ResourceNotFoundException"
    assert err.response["Error"]["Message"] == "USER not found."
    assert err.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert err.response["ResourceType"] == "USER"
    assert err.response["Message"] == "USER not found."
    assert "RequestId" in err.response


@mock_identitystore
def test_get_group_id():
    client = boto3.client("identitystore", region_name="us-east-2")
    identity_store_id = get_identity_store_id()
    groups = {}

    # Create a bunch of groups
    for _ in range(1, 10):
        group = __create_test_group(client, identity_store_id)
        groups[group[0]] = group[2]

    # Make sure we can get their ID
    for name, group_id in groups.items():
        response = client.get_group_id(
            IdentityStoreId=identity_store_id,
            AlternateIdentifier={
                "UniqueAttribute": {
                    "AttributePath": "displayName",
                    "AttributeValue": name,
                }
            },
        )

        assert response["IdentityStoreId"] == identity_store_id
        assert response["GroupId"] == group_id


@mock_identitystore
def test_get_group_id_does_not_exist():
    client = boto3.client("identitystore", region_name="us-east-2")
    identity_store_id = get_identity_store_id()
    with pytest.raises(ClientError) as exc:
        client.get_group_id(
            IdentityStoreId=identity_store_id,
            AlternateIdentifier={
                "UniqueAttribute": {
                    "AttributePath": "displayName",
                    "AttributeValue": "does-not-exist",
                }
            },
        )
    err = exc.value
    assert err.response["Error"]["Code"] == "ResourceNotFoundException"
    assert err.response["Error"]["Message"] == "GROUP not found."
    assert err.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert err.response["ResourceType"] == "GROUP"
    assert err.response["Message"] == "GROUP not found."
    assert "RequestId" in err.response


@mock_identitystore
def test_list_groups():
    client = boto3.client("identitystore", region_name="us-east-2")
    identity_store_id = get_identity_store_id()

    start = 0
    end = 266
    batch_size = 100
    next_token = None

    expected_groups = list()
    for _ in range(end):
        display_name, description, group_id = __create_test_group(
            client=client, store_id=identity_store_id
        )
        expected_groups.append(
            {
                "GroupId": group_id,
                "DisplayName": display_name,
                "ExternalIds": [],
                "Description": description,
                "IdentityStoreId": identity_store_id,
            }
        )

    groups = list()
    for iteration in range(start, end, batch_size):
        last_iteration = end - iteration <= batch_size
        expected_size = batch_size if not last_iteration else end - iteration

        if next_token is not None:
            list_response = client.list_groups(
                IdentityStoreId=identity_store_id,
                MaxResults=batch_size,
                NextToken=next_token,
            )
        else:
            list_response = client.list_groups(
                IdentityStoreId=identity_store_id,
                MaxResults=batch_size,
            )

        assert len(list_response["Groups"]) == expected_size
        groups.extend(list_response["Groups"])
        if last_iteration:
            assert "NextToken" not in list_response
        else:
            assert "NextToken" in list_response
            next_token = list_response["NextToken"]

    assert groups == expected_groups


@mock_identitystore
def test_list_groups_filter():
    client = boto3.client("identitystore", region_name="us-east-2")
    identity_store_id = get_identity_store_id()

    display_name, description, group_id = __create_test_group(
        client=client, store_id=identity_store_id
    )
    expected_group = {
        "GroupId": group_id,
        "DisplayName": display_name,
        "ExternalIds": [],
        "Description": description,
        "IdentityStoreId": identity_store_id,
    }

    # Create a second test group to see if it is not returned
    __create_test_group(client=client, store_id=identity_store_id)

    groups = client.list_groups(
        IdentityStoreId=identity_store_id,
        Filters=[
            {"AttributePath": "DisplayName", "AttributeValue": display_name},
        ],
    )["Groups"]

    assert len(groups) == 1
    assert groups[0] == expected_group

    no_groups = client.list_groups(
        IdentityStoreId=identity_store_id,
        Filters=[
            {"AttributePath": "DisplayName", "AttributeValue": "non_existant_group"},
        ],
    )["Groups"]

    assert len(no_groups) == 0


@mock_identitystore
def test_list_group_memberships():
    client = boto3.client("identitystore", region_name="us-east-2")
    identity_store_id = get_identity_store_id()

    start = 0
    end = 5000
    batch_size = 321
    next_token = None
    membership_ids = []

    group_id = client.create_group(
        IdentityStoreId=identity_store_id,
        DisplayName="test_group",
        Description="description",
    )["GroupId"]

    for _ in range(end):
        user_id = __create_and_verify_sparse_user(client, identity_store_id)["UserId"]
        create_response = client.create_group_membership(
            IdentityStoreId=identity_store_id,
            GroupId=group_id,
            MemberId={"UserId": user_id},
        )
        membership_ids.append((create_response["MembershipId"], user_id))

    for iteration in range(start, end, batch_size):
        last_iteration = end - iteration <= batch_size
        expected_size = batch_size if not last_iteration else end - iteration
        end_index = iteration + expected_size

        if next_token is not None:
            list_response = client.list_group_memberships(
                IdentityStoreId=identity_store_id,
                GroupId=group_id,
                MaxResults=batch_size,
                NextToken=next_token,
            )
        else:
            list_response = client.list_group_memberships(
                IdentityStoreId=identity_store_id,
                GroupId=group_id,
                MaxResults=batch_size,
            )

        assert len(list_response["GroupMemberships"]) == expected_size
        __check_membership_list_values(
            list_response["GroupMemberships"], membership_ids[iteration:end_index]
        )
        if last_iteration:
            assert "NextToken" not in list_response
        else:
            assert "NextToken" in list_response
            next_token = list_response["NextToken"]


def __check_membership_list_values(members, expected):
    assert len(members) == len(expected)
    for i in range(len(expected)):
        assert members[i]["MembershipId"] == expected[i][0]
        assert members[i]["MemberId"]["UserId"] == expected[i][1]


@mock_identitystore
def test_list_users():
    client = boto3.client("identitystore", region_name="us-east-2")
    identity_store_id = get_identity_store_id()

    start = 0
    end = 240
    batch_size = 100
    next_token = None

    expected_users = list()
    for _ in range(end):
        dummy_user = __create_and_verify_sparse_user(client, identity_store_id)
        expected_users.append(dummy_user)

    users = list()
    for iteration in range(start, end, batch_size):
        last_iteration = end - iteration <= batch_size
        expected_size = batch_size if not last_iteration else end - iteration

        if next_token is not None:
            list_response = client.list_users(
                IdentityStoreId=identity_store_id,
                MaxResults=batch_size,
                NextToken=next_token,
            )
        else:
            list_response = client.list_users(
                IdentityStoreId=identity_store_id,
                MaxResults=batch_size,
            )

        assert len(list_response["Users"]) == expected_size
        users.extend(list_response["Users"])
        if last_iteration:
            assert "NextToken" not in list_response
        else:
            assert "NextToken" in list_response
            next_token = list_response["NextToken"]

    assert users == expected_users


@mock_identitystore
def test_list_users_filter():
    client = boto3.client("identitystore", region_name="us-east-2")
    identity_store_id = get_identity_store_id()

    client.create_user(
        IdentityStoreId=identity_store_id,
        UserName="test_username_1",
        DisplayName="test_display_name_1",
        Name={"GivenName": "given_name", "FamilyName": "family_name"},
    )

    # Create a second user to see if it is not returned
    client.create_user(
        IdentityStoreId=identity_store_id,
        UserName="test_username_2",
        DisplayName="test_display_name_2",
        Name={"GivenName": "given_name", "FamilyName": "family_name"},
    )

    users = client.list_users(
        IdentityStoreId=identity_store_id,
        Filters=[
            {"AttributePath": "UserName", "AttributeValue": "test_username_1"},
        ],
    )["Users"]

    assert len(users) == 1
    assert users[0]["UserName"] == "test_username_1"

    no_users = client.list_users(
        IdentityStoreId=identity_store_id,
        Filters=[
            {"AttributePath": "UserName", "AttributeValue": "non_existant_user"},
        ],
    )["Users"]

    assert len(no_users) == 0


@mock_identitystore
def test_delete_group():
    client = boto3.client("identitystore", region_name="us-east-2")
    identity_store_id = get_identity_store_id()

    test_group = __create_test_group(client, identity_store_id)
    assert __group_exists(client, test_group[0], identity_store_id)

    resp = client.delete_group(IdentityStoreId=identity_store_id, GroupId=test_group[2])
    assert "ResponseMetadata" in resp
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

    assert not __group_exists(client, test_group[0], identity_store_id)


@mock_identitystore
def test_delete_group_doesnt_exist():
    client = boto3.client("identitystore", region_name="us-east-2")
    identity_store_id = get_identity_store_id()

    bogus_id = str(uuid4())

    resp = client.delete_group(IdentityStoreId=identity_store_id, GroupId=bogus_id)
    assert "ResponseMetadata" in resp
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

    assert not __group_exists(client, bogus_id, identity_store_id)


@mock_identitystore
def test_delete_group_membership():
    client = boto3.client("identitystore", region_name="eu-west-1")
    identity_store_id = get_identity_store_id()
    user_id = __create_and_verify_sparse_user(client, identity_store_id)["UserId"]
    _, _, group_id = __create_test_group(client, identity_store_id)

    membership = client.create_group_membership(
        IdentityStoreId=identity_store_id,
        GroupId=group_id,
        MemberId={"UserId": user_id},
    )

    # Verify the group membership
    response = client.list_group_memberships(
        IdentityStoreId=identity_store_id, GroupId=group_id
    )
    assert response["GroupMemberships"][0]["MemberId"]["UserId"] == user_id

    client.delete_group_membership(
        IdentityStoreId=identity_store_id, MembershipId=membership["MembershipId"]
    )

    # Verify the group membership has been removed
    response = client.list_group_memberships(
        IdentityStoreId=identity_store_id, GroupId=group_id
    )
    assert len(response["GroupMemberships"]) == 0


@mock_identitystore
def test_delete_user():
    client = boto3.client("identitystore", region_name="us-east-2")
    identity_store_id = get_identity_store_id()
    user_id = __create_and_verify_sparse_user(client, identity_store_id)["UserId"]

    client.delete_user(IdentityStoreId=identity_store_id, UserId=user_id)

    with pytest.raises(ClientError) as exc:
        client.describe_user(IdentityStoreId=identity_store_id, UserId=user_id)
    err = exc.value
    assert err.response["Error"]["Code"] == "ResourceNotFoundException"


@mock_identitystore
def test_delete_user_doesnt_exist():
    client = boto3.client("identitystore", region_name="us-east-2")
    identity_store_id = get_identity_store_id()

    # This test ensures that the delete_user call does not raise an error if the user ID does not exist
    client.delete_user(
        IdentityStoreId=identity_store_id, UserId=str(mock_random.uuid4())
    )


@mock_identitystore
def test_create_describe_group() -> None:
    client = boto3.client("identitystore", region_name="us-east-2")
    identity_store_id = get_identity_store_id()
    group_name, group_descriprion, group_id = __create_test_group(
        client, identity_store_id
    )

    client_response = client.describe_group(
        IdentityStoreId=identity_store_id, GroupId=group_id
    )
    assert client_response["GroupId"] == group_id
    assert client_response["DisplayName"] == group_name
    assert client_response["Description"] == group_descriprion
    assert client_response["IdentityStoreId"] == identity_store_id


@mock_identitystore
def test_describe_group_doesnt_exist() -> None:
    client = boto3.client("identitystore", region_name="us-east-2")
    identity_store_id = get_identity_store_id()

    with pytest.raises(ClientError) as exc:
        client.describe_group(IdentityStoreId=identity_store_id, GroupId=str(uuid4()))

    err = exc.value
    assert err.response["Error"]["Code"] == "ResourceNotFoundException"
    assert err.response["Error"]["Message"] == "GROUP not found."
    assert err.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert err.response["ResourceType"] == "GROUP"
    assert err.response["Message"] == "GROUP not found."
    assert "RequestId" in err.response


def __create_test_group(client, store_id: str):
    rand = "".join(random.choices(string.ascii_lowercase, k=8))
    group_name = f"test_group_{rand}"
    description = f"random_description_{rand}"

    create_resp = client.create_group(
        IdentityStoreId=store_id,
        DisplayName=group_name,
        Description=description,
    )

    return group_name, description, create_resp["GroupId"]


def __group_exists(client, group_name: str, store_id: str) -> bool:
    try:
        client.get_group_id(
            IdentityStoreId=store_id,
            AlternateIdentifier={
                "UniqueAttribute": {
                    "AttributePath": "displayName",
                    "AttributeValue": group_name,
                }
            },
        )
        return True
    except ClientError as e:
        if "ResourceNotFoundException" in str(type(e)):
            return False
        raise e


def __create_and_verify_sparse_user(client, store_id: str):
    """Creates a user, verifies it is unique and returns the response of describe_user"""
    rand = "".join(random.choices(string.ascii_lowercase, k=8))
    username = f"the_username_{rand}"
    response = client.create_user(
        IdentityStoreId=store_id,
        UserName=username,
        DisplayName=f"display_name_{rand}",
        Name={"GivenName": f"given_name_{rand}", "FamilyName": f"family_name_{rand}"},
    )
    assert UUID(response["UserId"])

    user_resp = client.describe_user(
        IdentityStoreId=store_id, UserId=response["UserId"]
    )

    assert user_resp["UserName"] == username
    del user_resp[
        "ResponseMetadata"
    ]  # strip response metadata and just return user info
    return user_resp
