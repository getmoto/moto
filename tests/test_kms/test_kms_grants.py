import boto3
import sure  # noqa # pylint: disable=unused-import
import pytest

from moto import mock_kms
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID


grantee_principal = (
    f"arn:aws:iam::{ACCOUNT_ID}:role/service-role/tf-acc-test-7071877926602081451"
)


@mock_kms
def test_create_grant():
    client = boto3.client("kms", region_name="us-east-1")
    key_id = client.create_key(Policy="my policy")["KeyMetadata"]["KeyId"]

    resp = client.create_grant(
        KeyId=key_id,
        GranteePrincipal=grantee_principal,
        Operations=["DECRYPT"],
        Name="testgrant",
    )
    resp.should.have.key("GrantId")
    resp.should.have.key("GrantToken")


@mock_kms
def test_list_grants():
    client = boto3.client("kms", region_name="us-east-1")
    key_id = client.create_key(Policy="my policy")["KeyMetadata"]["KeyId"]

    client.list_grants(KeyId=key_id).should.have.key("Grants").equals([])

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
    grants.should.have.length_of(2)
    grant_1 = [grant for grant in grants if grant["GrantId"] == grant_id1][0]
    grant_2 = [grant for grant in grants if grant["GrantId"] == grant_id2][0]

    grant_1.should.have.key("KeyId").equals(key_id)
    grant_1.should.have.key("GrantId").equals(grant_id1)
    grant_1.should.have.key("Name").equals("testgrant")
    grant_1.should.have.key("GranteePrincipal").equals(grantee_principal)
    grant_1.should.have.key("Operations").equals(["DECRYPT"])

    grant_2.should.have.key("KeyId").equals(key_id)
    grant_2.should.have.key("GrantId").equals(grant_id2)
    grant_2.shouldnt.have.key("Name")
    grant_2.should.have.key("GranteePrincipal").equals(grantee_principal)
    grant_2.should.have.key("Operations").equals(["DECRYPT", "ENCRYPT"])
    grant_2.should.have.key("Constraints").equals(
        {"EncryptionContextSubset": {"baz": "kaz", "foo": "bar"}}
    )

    # List by grant_id
    grants = client.list_grants(KeyId=key_id, GrantId=grant_id2)["Grants"]
    grants.should.have.length_of(1)
    grants[0]["GrantId"].should.equal(grant_id2)

    # List by unknown grant_id
    grants = client.list_grants(KeyId=key_id, GrantId="unknown")["Grants"]
    grants.should.have.length_of(0)


@mock_kms
def test_list_retirable_grants():
    client = boto3.client("kms", region_name="us-east-1")
    key_id1 = client.create_key(Policy="my policy")["KeyMetadata"]["KeyId"]
    key_id2 = client.create_key(Policy="my policy")["KeyMetadata"]["KeyId"]

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
    grants.should.have.length_of(1)
    grants[0]["KeyId"].should.equal(key_id2)
    grants[0]["GrantId"].should.equal(grant2_key2)


@mock_kms
def test_revoke_grant():

    client = boto3.client("kms", region_name="us-east-1")
    key_id = client.create_key(Policy="my policy")["KeyMetadata"]["KeyId"]

    client.list_grants(KeyId=key_id).should.have.key("Grants").equals([])

    grant_id = client.create_grant(
        KeyId=key_id,
        GranteePrincipal=grantee_principal,
        Operations=["DECRYPT"],
        Name="testgrant",
    )["GrantId"]

    client.revoke_grant(KeyId=key_id, GrantId=grant_id)

    client.list_grants(KeyId=key_id)["Grants"].should.have.length_of(0)


@mock_kms
def test_revoke_grant_raises_when_grant_does_not_exist():
    client = boto3.client("kms", region_name="us-east-1")
    key_id = client.create_key(Policy="my policy")["KeyMetadata"]["KeyId"]
    not_existent_grant_id = "aabbccdd"

    with pytest.raises(client.exceptions.NotFoundException) as ex:
        client.revoke_grant(KeyId=key_id, GrantId=not_existent_grant_id)

    ex.value.response["Error"]["Code"].should.equal("NotFoundException")
    ex.value.response["Error"]["Message"].should.equal(
        f"Grant ID {not_existent_grant_id} not found"
    )


@mock_kms
def test_retire_grant_by_token():

    client = boto3.client("kms", region_name="us-east-1")
    key_id = client.create_key(Policy="my policy")["KeyMetadata"]["KeyId"]

    for idx in range(0, 3):
        grant_token = client.create_grant(
            KeyId=key_id,
            GranteePrincipal=grantee_principal,
            Operations=["DECRYPT"],
            Name=f"testgrant{idx}",
        )["GrantToken"]

    client.retire_grant(GrantToken=grant_token)

    client.list_grants(KeyId=key_id)["Grants"].should.have.length_of(2)


@mock_kms
def test_retire_grant_by_grant_id():

    client = boto3.client("kms", region_name="us-east-1")
    key_id = client.create_key(Policy="my policy")["KeyMetadata"]["KeyId"]

    for idx in range(0, 3):
        grant_id = client.create_grant(
            KeyId=key_id,
            GranteePrincipal=grantee_principal,
            Operations=["DECRYPT"],
            Name=f"testgrant{idx}",
        )["GrantId"]

    client.retire_grant(KeyId=key_id, GrantId=grant_id)

    client.list_grants(KeyId=key_id)["Grants"].should.have.length_of(2)
