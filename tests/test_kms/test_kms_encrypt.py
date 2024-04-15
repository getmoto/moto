import base64

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws

from . import kms_aws_verified
from .test_kms_boto3 import PLAINTEXT_VECTORS, _get_encoded_value


@pytest.mark.aws_verified
@kms_aws_verified
def test_encrypt_key_with_empty_content():
    client_kms = boto3.client("kms", region_name="ap-northeast-1")
    metadata = client_kms.create_key()["KeyMetadata"]
    with pytest.raises(ClientError) as exc:
        client_kms.encrypt(KeyId=metadata["KeyId"], Plaintext="")
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert (
        err["Message"]
        == "1 validation error detected: Value at 'plaintext' failed to satisfy constraint: Member must have length greater than or equal to 1"
    )
    client_kms.schedule_key_deletion(KeyId=metadata["KeyId"], PendingWindowInDays=7)


@pytest.mark.aws_verified
@kms_aws_verified
def test_encrypt_key_with_large_content():
    client_kms = boto3.client("kms", region_name="ap-northeast-1")
    metadata = client_kms.create_key()["KeyMetadata"]
    with pytest.raises(ClientError) as exc:
        client_kms.encrypt(KeyId=metadata["KeyId"], Plaintext=b"x" * 4097)
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert (
        err["Message"]
        == "1 validation error detected: Value at 'plaintext' failed to satisfy constraint: Member must have length less than or equal to 4096"
    )
    client_kms.schedule_key_deletion(KeyId=metadata["KeyId"], PendingWindowInDays=7)


@pytest.mark.parametrize("plaintext", PLAINTEXT_VECTORS)
@mock_aws
def test_encrypt(plaintext):
    client = boto3.client("kms", region_name="us-west-2")

    key = client.create_key(Description="key")
    key_id = key["KeyMetadata"]["KeyId"]
    key_arn = key["KeyMetadata"]["Arn"]

    response = client.encrypt(KeyId=key_id, Plaintext=plaintext)
    assert response["CiphertextBlob"] != plaintext

    # CiphertextBlob must NOT be base64-encoded
    with pytest.raises(Exception):
        base64.b64decode(response["CiphertextBlob"], validate=True)

    assert response["KeyId"] == key_arn


@mock_aws
def test_encrypt_using_alias_name():
    kms = boto3.client("kms", region_name="us-east-1")
    key_details = kms.create_key()
    key_alias = "alias/examplekey"
    kms.create_alias(AliasName=key_alias, TargetKeyId=key_details["KeyMetadata"]["Arn"])

    # Just ensure that they do not throw an error, i.e. verify that it's possible to call this method using the Alias
    resp = kms.encrypt(KeyId=key_alias, Plaintext="hello")
    kms.decrypt(CiphertextBlob=resp["CiphertextBlob"])


@mock_aws
def test_encrypt_using_alias_arn():
    kms = boto3.client("kms", region_name="us-east-1")
    key_details = kms.create_key()
    key_alias = "alias/examplekey"
    kms.create_alias(AliasName=key_alias, TargetKeyId=key_details["KeyMetadata"]["Arn"])

    aliases = kms.list_aliases(KeyId=key_details["KeyMetadata"]["Arn"])["Aliases"]
    my_alias = [a for a in aliases if a["AliasName"] == key_alias][0]

    kms.encrypt(KeyId=my_alias["AliasArn"], Plaintext="hello")


@mock_aws
def test_encrypt_using_key_arn():
    kms = boto3.client("kms", region_name="us-east-1")
    key_details = kms.create_key()
    key_alias = "alias/examplekey"
    kms.create_alias(AliasName=key_alias, TargetKeyId=key_details["KeyMetadata"]["Arn"])

    kms.encrypt(KeyId=key_details["KeyMetadata"]["Arn"], Plaintext="hello")


@mock_aws
def test_re_encrypt_using_aliases():
    client = boto3.client("kms", region_name="us-west-2")

    key_1_id = client.create_key(Description="key 1")["KeyMetadata"]["KeyId"]
    key_2_arn = client.create_key(Description="key 2")["KeyMetadata"]["Arn"]

    key_alias = "alias/examplekey"
    client.create_alias(AliasName=key_alias, TargetKeyId=key_2_arn)

    encrypt_response = client.encrypt(KeyId=key_1_id, Plaintext="data")

    client.re_encrypt(
        CiphertextBlob=encrypt_response["CiphertextBlob"],
        DestinationKeyId=key_alias,
    )


@pytest.mark.parametrize("plaintext", PLAINTEXT_VECTORS)
@mock_aws
def test_decrypt(plaintext):
    client = boto3.client("kms", region_name="us-west-2")

    key = client.create_key(Description="key")
    key_id = key["KeyMetadata"]["KeyId"]
    key_arn = key["KeyMetadata"]["Arn"]

    encrypt_response = client.encrypt(KeyId=key_id, Plaintext=plaintext)

    client.create_key(Description="key")
    # CiphertextBlob must NOT be base64-encoded
    with pytest.raises(Exception):
        base64.b64decode(encrypt_response["CiphertextBlob"], validate=True)

    decrypt_response = client.decrypt(CiphertextBlob=encrypt_response["CiphertextBlob"])

    # Plaintext must NOT be base64-encoded
    with pytest.raises(Exception):
        base64.b64decode(decrypt_response["Plaintext"], validate=True)

    assert decrypt_response["Plaintext"] == _get_encoded_value(plaintext)
    assert decrypt_response["KeyId"] == key_arn


@pytest.mark.parametrize("plaintext", PLAINTEXT_VECTORS)
@mock_aws
def test_kms_encrypt(plaintext):
    client = boto3.client("kms", region_name="us-east-1")
    key = client.create_key(Description="key")
    response = client.encrypt(KeyId=key["KeyMetadata"]["KeyId"], Plaintext=plaintext)

    response = client.decrypt(CiphertextBlob=response["CiphertextBlob"])
    assert response["Plaintext"] == _get_encoded_value(plaintext)


@pytest.mark.parametrize("plaintext", PLAINTEXT_VECTORS)
@mock_aws
def test_re_encrypt_decrypt(plaintext):
    client = boto3.client("kms", region_name="us-west-2")

    key_1 = client.create_key(Description="key 1")
    key_1_id = key_1["KeyMetadata"]["KeyId"]
    key_1_arn = key_1["KeyMetadata"]["Arn"]
    key_2 = client.create_key(Description="key 2")
    key_2_id = key_2["KeyMetadata"]["KeyId"]
    key_2_arn = key_2["KeyMetadata"]["Arn"]

    encrypt_response = client.encrypt(
        KeyId=key_1_id, Plaintext=plaintext, EncryptionContext={"encryption": "context"}
    )

    re_encrypt_response = client.re_encrypt(
        CiphertextBlob=encrypt_response["CiphertextBlob"],
        SourceEncryptionContext={"encryption": "context"},
        DestinationKeyId=key_2_id,
        DestinationEncryptionContext={"another": "context"},
    )

    # CiphertextBlob must NOT be base64-encoded
    with pytest.raises(Exception):
        base64.b64decode(re_encrypt_response["CiphertextBlob"], validate=True)

    assert re_encrypt_response["SourceKeyId"] == key_1_arn
    assert re_encrypt_response["KeyId"] == key_2_arn

    decrypt_response_1 = client.decrypt(
        CiphertextBlob=encrypt_response["CiphertextBlob"],
        EncryptionContext={"encryption": "context"},
    )
    assert decrypt_response_1["Plaintext"] == _get_encoded_value(plaintext)
    assert decrypt_response_1["KeyId"] == key_1_arn

    decrypt_response_2 = client.decrypt(
        CiphertextBlob=re_encrypt_response["CiphertextBlob"],
        EncryptionContext={"another": "context"},
    )
    assert decrypt_response_2["Plaintext"] == _get_encoded_value(plaintext)
    assert decrypt_response_2["KeyId"] == key_2_arn

    assert decrypt_response_1["Plaintext"] == decrypt_response_2["Plaintext"]


@mock_aws
def test_re_encrypt_to_invalid_destination():
    client = boto3.client("kms", region_name="us-west-2")

    key = client.create_key(Description="key 1")
    key_id = key["KeyMetadata"]["KeyId"]

    encrypt_response = client.encrypt(KeyId=key_id, Plaintext=b"some plaintext")

    with pytest.raises(client.exceptions.NotFoundException):
        client.re_encrypt(
            CiphertextBlob=encrypt_response["CiphertextBlob"],
            DestinationKeyId="alias/DoesNotExist",
        )
