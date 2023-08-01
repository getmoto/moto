import boto3
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from unittest import mock

from moto import mock_kms
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID


grantee_principal = (
    f"arn:aws:iam::{ACCOUNT_ID}:role/service-role/tf-acc-test-7071877926602081451"
)


@mock_kms
def test_create_grant():
    client = boto3.client("kms", region_name="us-east-1")
    key_id = create_key(client)

    resp = client.create_grant(
        KeyId=key_id,
        GranteePrincipal=grantee_principal,
        Operations=["DECRYPT"],
        Name="testgrant",
    )
    assert "GrantId" in resp
    assert "GrantToken" in resp


@mock_kms
def test_list_grants():
    client = boto3.client("kms", region_name="us-east-1")
    key_id = create_key(client)

    assert client.list_grants(KeyId=key_id)["Grants"] == []

    grant_id1 = client.create_grant(
        KeyId=key_id,
        GranteePrincipal=grantee_principal,
        Operations=["DECRYPT"],
        Name="testgrant",
    )["GrantId"]

    grant_id2 = client.create_grant(
        KeyId=key_id,
        GranteePrincipal=grantee_principal,
        Operations=["DECRYPT", "ENCRYPT"],
        Constraints={"EncryptionContextSubset": {"baz": "kaz", "foo": "bar"}},
    )["GrantId"]

    # List all
    grants = client.list_grants(KeyId=key_id)["Grants"]
    assert len(grants) == 2
    grant_1 = [grant for grant in grants if grant["GrantId"] == grant_id1][0]
    grant_2 = [grant for grant in grants if grant["GrantId"] == grant_id2][0]

    assert grant_1["KeyId"] == key_id
    assert grant_1["GrantId"] == grant_id1
    assert grant_1["Name"] == "testgrant"
    assert grant_1["GranteePrincipal"] == grantee_principal
    assert grant_1["Operations"] == ["DECRYPT"]

    assert grant_2["KeyId"] == key_id
    assert grant_2["GrantId"] == grant_id2
    assert "Name" not in grant_2
    assert grant_2["GranteePrincipal"] == grantee_principal
    assert grant_2["Operations"] == ["DECRYPT", "ENCRYPT"]
    assert grant_2["Constraints"] == {
        "EncryptionContextSubset": {"baz": "kaz", "foo": "bar"}
    }

    # List by grant_id
    grants = client.list_grants(KeyId=key_id, GrantId=grant_id2)["Grants"]
    assert len(grants) == 1
    assert grants[0]["GrantId"] == grant_id2

    # List by unknown grant_id
    grants = client.list_grants(KeyId=key_id, GrantId="unknown")["Grants"]
    assert len(grants) == 0


@mock_kms
def test_list_retirable_grants():
    client = boto3.client("kms", region_name="us-east-1")
    key_id1 = create_key(client)
    key_id2 = create_key(client)

    client.create_grant(
        KeyId=key_id1,
        GranteePrincipal=grantee_principal,
        Operations=["DECRYPT"],
    )

    client.create_grant(
        KeyId=key_id1,
        GranteePrincipal=grantee_principal,
        RetiringPrincipal="sth else",
        Operations=["DECRYPT"],
    )

    client.create_grant(
        KeyId=key_id2,
        GranteePrincipal=grantee_principal,
        Operations=["DECRYPT"],
    )

    grant2_key2 = client.create_grant(
        KeyId=key_id2,
        GranteePrincipal=grantee_principal,
        RetiringPrincipal="principal",
        Operations=["DECRYPT"],
    )["GrantId"]

    # List only the grants from the retiring principal
    grants = client.list_retirable_grants(RetiringPrincipal="principal")["Grants"]
    assert len(grants) == 1
    assert grants[0]["KeyId"] == key_id2
    assert grants[0]["GrantId"] == grant2_key2


@mock_kms
def test_revoke_grant():

    client = boto3.client("kms", region_name="us-east-1")
    key_id = create_key(client)

    assert client.list_grants(KeyId=key_id)["Grants"] == []

    grant_id = client.create_grant(
        KeyId=key_id,
        GranteePrincipal=grantee_principal,
        Operations=["DECRYPT"],
        Name="testgrant",
    )["GrantId"]

    client.revoke_grant(KeyId=key_id, GrantId=grant_id)

    assert len(client.list_grants(KeyId=key_id)["Grants"]) == 0


@mock_kms
def test_revoke_grant_raises_when_grant_does_not_exist():
    client = boto3.client("kms", region_name="us-east-1")
    key_id = create_key(client)
    not_existent_grant_id = "aabbccdd"

    with pytest.raises(client.exceptions.NotFoundException) as ex:
        client.revoke_grant(KeyId=key_id, GrantId=not_existent_grant_id)

    assert ex.value.response["Error"]["Code"] == "NotFoundException"
    assert (
        ex.value.response["Error"]["Message"]
        == f"Grant ID {not_existent_grant_id} not found"
    )


@mock_kms
def test_retire_grant_by_token():

    client = boto3.client("kms", region_name="us-east-1")
    key_id = create_key(client)

    for idx in range(0, 3):
        grant_token = client.create_grant(
            KeyId=key_id,
            GranteePrincipal=grantee_principal,
            Operations=["DECRYPT"],
            Name=f"testgrant{idx}",
        )["GrantToken"]

    client.retire_grant(GrantToken=grant_token)

    assert len(client.list_grants(KeyId=key_id)["Grants"]) == 2


@mock_kms
def test_retire_grant_by_grant_id():

    client = boto3.client("kms", region_name="us-east-1")
    key_id = create_key(client)

    for idx in range(0, 3):
        grant_id = client.create_grant(
            KeyId=key_id,
            GranteePrincipal=grantee_principal,
            Operations=["DECRYPT"],
            Name=f"testgrant{idx}",
        )["GrantId"]

    client.retire_grant(KeyId=key_id, GrantId=grant_id)

    assert len(client.list_grants(KeyId=key_id)["Grants"]) == 2


def create_key(client):
    with mock.patch.object(rsa, "generate_private_key", return_value=""):
        return client.create_key(Policy="my policy")["KeyMetadata"]["KeyId"]
