import boto3
import pytest

from moto import mock_aws


@pytest.fixture(name="client")
def client_fixture():
    with mock_aws():
        yield boto3.client("iot", region_name="eu-west-1")


def test_create_role_alias(client):
    role_alias_name = "test-role-alias"
    create_response = client.create_role_alias(
        roleAlias=role_alias_name,
        roleArn="arn:aws:iam::123456789012:role/my-role",
        credentialDurationSeconds=1234,
    )

    assert create_response["roleAlias"] == role_alias_name
    assert (
        create_response["roleAliasArn"]
        == f"arn:aws:iot:eu-west-1:123456789012:rolealias/{role_alias_name}"
    )

    assert len(client.list_role_aliases()["roleAliases"]) == 1


def test_create_role_alias_twice(client):
    role_alias_name = "test-role-alias"
    create_response = client.create_role_alias(
        roleAlias=role_alias_name,
        roleArn="arn:aws:iam::123456789012:role/my-role",
        credentialDurationSeconds=1234,
    )

    assert create_response["roleAlias"] == role_alias_name
    assert (
        create_response["roleAliasArn"]
        == f"arn:aws:iot:eu-west-1:123456789012:rolealias/{role_alias_name}"
    )

    with pytest.raises(client.exceptions.ResourceAlreadyExistsException):
        client.create_role_alias(
            roleAlias=role_alias_name,
            roleArn="arn:aws:iam::123456789012:role/my-role",
            credentialDurationSeconds=1234,
        )


def test_list_role_aliases(client):
    client.create_role_alias(
        roleAlias="test-role-alias", roleArn="arn:aws:iam::123456789012:role/my-role"
    )
    client.create_role_alias(
        roleAlias="another_role_alias",
        roleArn="arn:aws:iam::123456789012:role/my-role",
    )

    response = client.list_role_aliases()

    assert response["roleAliases"] == ["test-role-alias", "another_role_alias"]


def test_delete_role_alias(client):
    role_alias_name = "test-role-alias"

    client.create_role_alias(
        roleAlias=role_alias_name, roleArn="arn:aws:iam::123456789012:role/my-role"
    )
    assert len(client.list_role_aliases()["roleAliases"]) == 1

    client.delete_role_alias(roleAlias=role_alias_name)
    assert len(client.list_role_aliases()["roleAliases"]) == 0


def test_delete_nonexistent_role_alias(client):
    with pytest.raises(client.exceptions.ResourceNotFoundException):
        client.delete_role_alias(roleAlias="test_role_alias")


def test_describe_role_alias(client):
    role_alias_name = "test-role-alias"
    client.create_role_alias(
        roleAlias=role_alias_name, roleArn="arn:aws:iam::123456789012:role/my-role"
    )

    response = client.describe_role_alias(roleAlias=role_alias_name)
    assert response["roleAliasDescription"]["roleAlias"] == role_alias_name
    assert (
        response["roleAliasDescription"]["roleAliasArn"]
        == f"arn:aws:iot:eu-west-1:123456789012:rolealias/{role_alias_name}"
    )
    assert (
        response["roleAliasDescription"]["roleArn"]
        == "arn:aws:iam::123456789012:role/my-role"
    )
    assert response["roleAliasDescription"]["credentialDurationSeconds"] == 3600
    assert "owner" in response["roleAliasDescription"]
    assert "creationDate" in response["roleAliasDescription"]
    assert "lastModifiedDate" in response["roleAliasDescription"]


def test_update_role_alias(client):
    role_alias_name = "test-role-alias"
    client.create_role_alias(
        roleAlias=role_alias_name,
        roleArn="arn:aws:iam::123456789012:role/my-role",
        credentialDurationSeconds=1234,
    )
    client.update_role_alias(
        roleAlias=role_alias_name,
        roleArn="arn:aws:iam::123456789012:role/other-role",
        credentialDurationSeconds=2345,
    )
    response = client.describe_role_alias(roleAlias=role_alias_name)

    assert response["roleAliasDescription"]["roleAlias"] == role_alias_name
    assert (
        response["roleAliasDescription"]["roleAliasArn"]
        == f"arn:aws:iot:eu-west-1:123456789012:rolealias/{role_alias_name}"
    )
    assert (
        response["roleAliasDescription"]["roleArn"]
        == "arn:aws:iam::123456789012:role/other-role"
    )
    assert response["roleAliasDescription"]["credentialDurationSeconds"] == 2345
