# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json
from datetime import datetime
from dateutil.tz import tzutc
import base64
import os

import boto3
import botocore.exceptions
import sure  # noqa
from freezegun import freeze_time
import pytest

from moto import mock_kms
from moto.core import ACCOUNT_ID

PLAINTEXT_VECTORS = [
    b"some encodeable plaintext",
    b"some unencodeable plaintext \xec\x8a\xcf\xb6r\xe9\xb5\xeb\xff\xa23\x16",
    "some unicode characters ø˚∆øˆˆ∆ßçøˆˆçßøˆ¨¥",
]


def _get_encoded_value(plaintext):
    if isinstance(plaintext, bytes):
        return plaintext

    return plaintext.encode("utf-8")


@mock_kms
def test_create_key():
    conn = boto3.client("kms", region_name="us-east-1")
    key = conn.create_key(
        Policy="my policy",
        Description="my key",
        KeyUsage="ENCRYPT_DECRYPT",
        Tags=[{"TagKey": "project", "TagValue": "moto"}],
    )

    key["KeyMetadata"]["Arn"].should.equal(
        "arn:aws:kms:us-east-1:123456789012:key/{}".format(key["KeyMetadata"]["KeyId"])
    )
    key["KeyMetadata"]["AWSAccountId"].should.equal("123456789012")
    key["KeyMetadata"]["CreationDate"].should.be.a(datetime)
    key["KeyMetadata"]["CustomerMasterKeySpec"].should.equal("SYMMETRIC_DEFAULT")
    key["KeyMetadata"]["Description"].should.equal("my key")
    key["KeyMetadata"]["Enabled"].should.be.ok
    key["KeyMetadata"]["EncryptionAlgorithms"].should.equal(["SYMMETRIC_DEFAULT"])
    key["KeyMetadata"]["KeyId"].should_not.be.empty
    key["KeyMetadata"]["KeyManager"].should.equal("CUSTOMER")
    key["KeyMetadata"]["KeyState"].should.equal("Enabled")
    key["KeyMetadata"]["KeyUsage"].should.equal("ENCRYPT_DECRYPT")
    key["KeyMetadata"]["Origin"].should.equal("AWS_KMS")
    key["KeyMetadata"].should_not.have.key("SigningAlgorithms")

    key = conn.create_key(KeyUsage="ENCRYPT_DECRYPT", CustomerMasterKeySpec="RSA_2048",)

    sorted(key["KeyMetadata"]["EncryptionAlgorithms"]).should.equal(
        ["RSAES_OAEP_SHA_1", "RSAES_OAEP_SHA_256"]
    )
    key["KeyMetadata"].should_not.have.key("SigningAlgorithms")

    key = conn.create_key(KeyUsage="SIGN_VERIFY", CustomerMasterKeySpec="RSA_2048",)

    key["KeyMetadata"].should_not.have.key("EncryptionAlgorithms")
    sorted(key["KeyMetadata"]["SigningAlgorithms"]).should.equal(
        [
            "RSASSA_PKCS1_V1_5_SHA_256",
            "RSASSA_PKCS1_V1_5_SHA_384",
            "RSASSA_PKCS1_V1_5_SHA_512",
            "RSASSA_PSS_SHA_256",
            "RSASSA_PSS_SHA_384",
            "RSASSA_PSS_SHA_512",
        ]
    )

    key = conn.create_key(
        KeyUsage="SIGN_VERIFY", CustomerMasterKeySpec="ECC_SECG_P256K1",
    )

    key["KeyMetadata"].should_not.have.key("EncryptionAlgorithms")
    key["KeyMetadata"]["SigningAlgorithms"].should.equal(["ECDSA_SHA_256"])

    key = conn.create_key(
        KeyUsage="SIGN_VERIFY", CustomerMasterKeySpec="ECC_NIST_P384",
    )

    key["KeyMetadata"].should_not.have.key("EncryptionAlgorithms")
    key["KeyMetadata"]["SigningAlgorithms"].should.equal(["ECDSA_SHA_384"])

    key = conn.create_key(
        KeyUsage="SIGN_VERIFY", CustomerMasterKeySpec="ECC_NIST_P521",
    )

    key["KeyMetadata"].should_not.have.key("EncryptionAlgorithms")
    key["KeyMetadata"]["SigningAlgorithms"].should.equal(["ECDSA_SHA_512"])


@mock_kms
def test_describe_key():
    client = boto3.client("kms", region_name="us-east-1")
    response = client.create_key(Description="my key", KeyUsage="ENCRYPT_DECRYPT",)
    key_id = response["KeyMetadata"]["KeyId"]

    response = client.describe_key(KeyId=key_id)

    response["KeyMetadata"]["AWSAccountId"].should.equal("123456789012")
    response["KeyMetadata"]["CreationDate"].should.be.a(datetime)
    response["KeyMetadata"]["CustomerMasterKeySpec"].should.equal("SYMMETRIC_DEFAULT")
    response["KeyMetadata"]["Description"].should.equal("my key")
    response["KeyMetadata"]["Enabled"].should.be.ok
    response["KeyMetadata"]["EncryptionAlgorithms"].should.equal(["SYMMETRIC_DEFAULT"])
    response["KeyMetadata"]["KeyId"].should_not.be.empty
    response["KeyMetadata"]["KeyManager"].should.equal("CUSTOMER")
    response["KeyMetadata"]["KeyState"].should.equal("Enabled")
    response["KeyMetadata"]["KeyUsage"].should.equal("ENCRYPT_DECRYPT")
    response["KeyMetadata"]["Origin"].should.equal("AWS_KMS")
    response["KeyMetadata"].should_not.have.key("SigningAlgorithms")


@mock_kms
def test_get_key_policy_default():
    # given
    client = boto3.client("kms", region_name="us-east-1")
    key_id = client.create_key()["KeyMetadata"]["KeyId"]

    # when
    policy = client.get_key_policy(KeyId=key_id, PolicyName="default")["Policy"]

    # then
    json.loads(policy).should.equal(
        {
            "Version": "2012-10-17",
            "Id": "key-default-1",
            "Statement": [
                {
                    "Sid": "Enable IAM User Permissions",
                    "Effect": "Allow",
                    "Principal": {"AWS": f"arn:aws:iam::{ACCOUNT_ID}:root"},
                    "Action": "kms:*",
                    "Resource": "*",
                }
            ],
        }
    )


@pytest.mark.parametrize(
    "key_id",
    [
        "alias/does-not-exist",
        "arn:aws:kms:us-east-1:012345678912:alias/does-not-exist",
        "invalid",
    ],
)
@mock_kms
def test_describe_key_via_alias_invalid_alias(key_id):
    client = boto3.client("kms", region_name="us-east-1")
    client.create_key(Description="key")

    with pytest.raises(client.exceptions.NotFoundException):
        client.describe_key(KeyId=key_id)


@mock_kms
def test_generate_data_key():
    kms = boto3.client("kms", region_name="us-west-2")

    key = kms.create_key()
    key_id = key["KeyMetadata"]["KeyId"]
    key_arn = key["KeyMetadata"]["Arn"]

    response = kms.generate_data_key(KeyId=key_id, NumberOfBytes=32)

    # CiphertextBlob must NOT be base64-encoded
    with pytest.raises(Exception):
        base64.b64decode(response["CiphertextBlob"], validate=True)
    # Plaintext must NOT be base64-encoded
    with pytest.raises(Exception):
        base64.b64decode(response["Plaintext"], validate=True)

    response["KeyId"].should.equal(key_arn)


@pytest.mark.parametrize("plaintext", PLAINTEXT_VECTORS)
@mock_kms
def test_encrypt(plaintext):
    client = boto3.client("kms", region_name="us-west-2")

    key = client.create_key(Description="key")
    key_id = key["KeyMetadata"]["KeyId"]
    key_arn = key["KeyMetadata"]["Arn"]

    response = client.encrypt(KeyId=key_id, Plaintext=plaintext)
    response["CiphertextBlob"].should_not.equal(plaintext)

    # CiphertextBlob must NOT be base64-encoded
    with pytest.raises(Exception):
        base64.b64decode(response["CiphertextBlob"], validate=True)

    response["KeyId"].should.equal(key_arn)


@pytest.mark.parametrize("plaintext", PLAINTEXT_VECTORS)
@mock_kms
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

    decrypt_response["Plaintext"].should.equal(_get_encoded_value(plaintext))
    decrypt_response["KeyId"].should.equal(key_arn)


@pytest.mark.parametrize(
    "key_id",
    [
        "not-a-uuid",
        "alias/DoesNotExist",
        "arn:aws:kms:us-east-1:012345678912:alias/DoesNotExist",
        "d25652e4-d2d2-49f7-929a-671ccda580c6",
        "arn:aws:kms:us-east-1:012345678912:key/d25652e4-d2d2-49f7-929a-671ccda580c6",
    ],
)
@mock_kms
def test_invalid_key_ids(key_id):
    client = boto3.client("kms", region_name="us-east-1")

    with pytest.raises(client.exceptions.NotFoundException):
        client.generate_data_key(KeyId=key_id, NumberOfBytes=5)


@pytest.mark.parametrize("plaintext", PLAINTEXT_VECTORS)
@mock_kms
def test_kms_encrypt(plaintext):
    client = boto3.client("kms", region_name="us-east-1")
    key = client.create_key(Description="key")
    response = client.encrypt(KeyId=key["KeyMetadata"]["KeyId"], Plaintext=plaintext)

    response = client.decrypt(CiphertextBlob=response["CiphertextBlob"])
    response["Plaintext"].should.equal(_get_encoded_value(plaintext))


@mock_kms
def test_disable_key():
    client = boto3.client("kms", region_name="us-east-1")
    key = client.create_key(Description="disable-key")
    client.disable_key(KeyId=key["KeyMetadata"]["KeyId"])

    result = client.describe_key(KeyId=key["KeyMetadata"]["KeyId"])
    assert result["KeyMetadata"]["Enabled"] == False
    assert result["KeyMetadata"]["KeyState"] == "Disabled"


@mock_kms
def test_enable_key():
    client = boto3.client("kms", region_name="us-east-1")
    key = client.create_key(Description="enable-key")
    client.disable_key(KeyId=key["KeyMetadata"]["KeyId"])
    client.enable_key(KeyId=key["KeyMetadata"]["KeyId"])

    result = client.describe_key(KeyId=key["KeyMetadata"]["KeyId"])
    assert result["KeyMetadata"]["Enabled"] == True
    assert result["KeyMetadata"]["KeyState"] == "Enabled"


@mock_kms
def test_schedule_key_deletion():
    client = boto3.client("kms", region_name="us-east-1")
    key = client.create_key(Description="schedule-key-deletion")
    if os.environ.get("TEST_SERVER_MODE", "false").lower() == "false":
        with freeze_time("2015-01-01 12:00:00"):
            response = client.schedule_key_deletion(KeyId=key["KeyMetadata"]["KeyId"])
            assert response["KeyId"] == key["KeyMetadata"]["KeyId"]
            assert response["DeletionDate"] == datetime(
                2015, 1, 31, 12, 0, tzinfo=tzutc()
            )
    else:
        # Can't manipulate time in server mode
        response = client.schedule_key_deletion(KeyId=key["KeyMetadata"]["KeyId"])
        assert response["KeyId"] == key["KeyMetadata"]["KeyId"]

    result = client.describe_key(KeyId=key["KeyMetadata"]["KeyId"])
    assert result["KeyMetadata"]["Enabled"] == False
    assert result["KeyMetadata"]["KeyState"] == "PendingDeletion"
    assert "DeletionDate" in result["KeyMetadata"]


@mock_kms
def test_schedule_key_deletion_custom():
    client = boto3.client("kms", region_name="us-east-1")
    key = client.create_key(Description="schedule-key-deletion")
    if os.environ.get("TEST_SERVER_MODE", "false").lower() == "false":
        with freeze_time("2015-01-01 12:00:00"):
            response = client.schedule_key_deletion(
                KeyId=key["KeyMetadata"]["KeyId"], PendingWindowInDays=7
            )
            assert response["KeyId"] == key["KeyMetadata"]["KeyId"]
            assert response["DeletionDate"] == datetime(
                2015, 1, 8, 12, 0, tzinfo=tzutc()
            )
    else:
        # Can't manipulate time in server mode
        response = client.schedule_key_deletion(
            KeyId=key["KeyMetadata"]["KeyId"], PendingWindowInDays=7
        )
        assert response["KeyId"] == key["KeyMetadata"]["KeyId"]

    result = client.describe_key(KeyId=key["KeyMetadata"]["KeyId"])
    assert result["KeyMetadata"]["Enabled"] == False
    assert result["KeyMetadata"]["KeyState"] == "PendingDeletion"
    assert "DeletionDate" in result["KeyMetadata"]


@mock_kms
def test_cancel_key_deletion():
    client = boto3.client("kms", region_name="us-east-1")
    key = client.create_key(Description="cancel-key-deletion")
    client.schedule_key_deletion(KeyId=key["KeyMetadata"]["KeyId"])
    response = client.cancel_key_deletion(KeyId=key["KeyMetadata"]["KeyId"])
    assert response["KeyId"] == key["KeyMetadata"]["KeyId"]

    result = client.describe_key(KeyId=key["KeyMetadata"]["KeyId"])
    assert result["KeyMetadata"]["Enabled"] == False
    assert result["KeyMetadata"]["KeyState"] == "Disabled"
    assert "DeletionDate" not in result["KeyMetadata"]


@mock_kms
def test_update_key_description():
    client = boto3.client("kms", region_name="us-east-1")
    key = client.create_key(Description="old_description")
    key_id = key["KeyMetadata"]["KeyId"]

    result = client.update_key_description(KeyId=key_id, Description="new_description")
    assert "ResponseMetadata" in result


@mock_kms
def test_tag_resource():
    client = boto3.client("kms", region_name="us-east-1")
    key = client.create_key(Description="cancel-key-deletion")
    response = client.schedule_key_deletion(KeyId=key["KeyMetadata"]["KeyId"])

    keyid = response["KeyId"]
    response = client.tag_resource(
        KeyId=keyid, Tags=[{"TagKey": "string", "TagValue": "string"}]
    )

    # Shouldn't have any data, just header
    assert len(response.keys()) == 1


@mock_kms
def test_list_resource_tags():
    client = boto3.client("kms", region_name="us-east-1")
    key = client.create_key(Description="cancel-key-deletion")
    response = client.schedule_key_deletion(KeyId=key["KeyMetadata"]["KeyId"])

    keyid = response["KeyId"]
    response = client.tag_resource(
        KeyId=keyid, Tags=[{"TagKey": "string", "TagValue": "string"}]
    )

    response = client.list_resource_tags(KeyId=keyid)
    assert response["Tags"][0]["TagKey"] == "string"
    assert response["Tags"][0]["TagValue"] == "string"


@pytest.mark.parametrize(
    "kwargs,expected_key_length",
    (
        (dict(KeySpec="AES_256"), 32),
        (dict(KeySpec="AES_128"), 16),
        (dict(NumberOfBytes=64), 64),
        (dict(NumberOfBytes=1), 1),
        (dict(NumberOfBytes=1024), 1024),
    ),
)
@mock_kms
def test_generate_data_key_sizes(kwargs, expected_key_length):
    client = boto3.client("kms", region_name="us-east-1")
    key = client.create_key(Description="generate-data-key-size")

    response = client.generate_data_key(KeyId=key["KeyMetadata"]["KeyId"], **kwargs)

    assert len(response["Plaintext"]) == expected_key_length


@mock_kms
def test_generate_data_key_decrypt():
    client = boto3.client("kms", region_name="us-east-1")
    key = client.create_key(Description="generate-data-key-decrypt")

    resp1 = client.generate_data_key(
        KeyId=key["KeyMetadata"]["KeyId"], KeySpec="AES_256"
    )
    resp2 = client.decrypt(CiphertextBlob=resp1["CiphertextBlob"])

    assert resp1["Plaintext"] == resp2["Plaintext"]


@pytest.mark.parametrize(
    "kwargs",
    [
        dict(KeySpec="AES_257"),
        dict(KeySpec="AES_128", NumberOfBytes=16),
        dict(NumberOfBytes=2048),
        dict(),
    ],
)
@mock_kms
def test_generate_data_key_invalid_size_params(kwargs):
    client = boto3.client("kms", region_name="us-east-1")
    key = client.create_key(Description="generate-data-key-size")

    with pytest.raises(botocore.exceptions.ClientError):
        client.generate_data_key(KeyId=key["KeyMetadata"]["KeyId"], **kwargs)


@pytest.mark.parametrize(
    "key_id",
    [
        "alias/DoesNotExist",
        "arn:aws:kms:us-east-1:012345678912:alias/DoesNotExist",
        "d25652e4-d2d2-49f7-929a-671ccda580c6",
        "arn:aws:kms:us-east-1:012345678912:key/d25652e4-d2d2-49f7-929a-671ccda580c6",
    ],
)
@mock_kms
def test_generate_data_key_invalid_key(key_id):
    client = boto3.client("kms", region_name="us-east-1")

    with pytest.raises(client.exceptions.NotFoundException):
        client.generate_data_key(KeyId=key_id, KeySpec="AES_256")


@pytest.mark.parametrize(
    "prefix,append_key_id",
    [
        ("alias/DoesExist", False),
        ("arn:aws:kms:us-east-1:012345678912:alias/DoesExist", False),
        ("", True),
        ("arn:aws:kms:us-east-1:012345678912:key/", True),
    ],
)
@mock_kms
def test_generate_data_key_all_valid_key_ids(prefix, append_key_id):
    client = boto3.client("kms", region_name="us-east-1")
    key = client.create_key()
    key_id = key["KeyMetadata"]["KeyId"]
    client.create_alias(AliasName="alias/DoesExist", TargetKeyId=key_id)

    target_id = prefix
    if append_key_id:
        target_id += key_id

    client.generate_data_key(KeyId=key_id, NumberOfBytes=32)


@mock_kms
def test_generate_data_key_without_plaintext_decrypt():
    client = boto3.client("kms", region_name="us-east-1")
    key = client.create_key(Description="generate-data-key-decrypt")

    resp1 = client.generate_data_key_without_plaintext(
        KeyId=key["KeyMetadata"]["KeyId"], KeySpec="AES_256"
    )

    assert "Plaintext" not in resp1


@pytest.mark.parametrize("plaintext", PLAINTEXT_VECTORS)
@mock_kms
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

    re_encrypt_response["SourceKeyId"].should.equal(key_1_arn)
    re_encrypt_response["KeyId"].should.equal(key_2_arn)

    decrypt_response_1 = client.decrypt(
        CiphertextBlob=encrypt_response["CiphertextBlob"],
        EncryptionContext={"encryption": "context"},
    )
    decrypt_response_1["Plaintext"].should.equal(_get_encoded_value(plaintext))
    decrypt_response_1["KeyId"].should.equal(key_1_arn)

    decrypt_response_2 = client.decrypt(
        CiphertextBlob=re_encrypt_response["CiphertextBlob"],
        EncryptionContext={"another": "context"},
    )
    decrypt_response_2["Plaintext"].should.equal(_get_encoded_value(plaintext))
    decrypt_response_2["KeyId"].should.equal(key_2_arn)

    decrypt_response_1["Plaintext"].should.equal(decrypt_response_2["Plaintext"])


@mock_kms
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


@pytest.mark.parametrize("number_of_bytes", [12, 44, 91, 1, 1024])
@mock_kms
def test_generate_random(number_of_bytes):
    client = boto3.client("kms", region_name="us-west-2")

    response = client.generate_random(NumberOfBytes=number_of_bytes)

    response["Plaintext"].should.be.a(bytes)
    len(response["Plaintext"]).should.equal(number_of_bytes)


@pytest.mark.parametrize(
    "number_of_bytes,error_type",
    [(2048, botocore.exceptions.ClientError), (1025, botocore.exceptions.ClientError),],
)
@mock_kms
def test_generate_random_invalid_number_of_bytes(number_of_bytes, error_type):
    client = boto3.client("kms", region_name="us-west-2")

    with pytest.raises(error_type):
        client.generate_random(NumberOfBytes=number_of_bytes)


@mock_kms
def test_enable_key_rotation_key_not_found():
    client = boto3.client("kms", region_name="us-east-1")

    with pytest.raises(client.exceptions.NotFoundException):
        client.enable_key_rotation(KeyId="12366f9b-1230-123d-123e-123e6ae60c02")


@mock_kms
def test_disable_key_rotation_key_not_found():
    client = boto3.client("kms", region_name="us-east-1")

    with pytest.raises(client.exceptions.NotFoundException):
        client.disable_key_rotation(KeyId="12366f9b-1230-123d-123e-123e6ae60c02")


@mock_kms
def test_enable_key_key_not_found():
    client = boto3.client("kms", region_name="us-east-1")

    with pytest.raises(client.exceptions.NotFoundException):
        client.enable_key(KeyId="12366f9b-1230-123d-123e-123e6ae60c02")


@mock_kms
def test_disable_key_key_not_found():
    client = boto3.client("kms", region_name="us-east-1")

    with pytest.raises(client.exceptions.NotFoundException):
        client.disable_key(KeyId="12366f9b-1230-123d-123e-123e6ae60c02")


@mock_kms
def test_cancel_key_deletion_key_not_found():
    client = boto3.client("kms", region_name="us-east-1")

    with pytest.raises(client.exceptions.NotFoundException):
        client.cancel_key_deletion(KeyId="12366f9b-1230-123d-123e-123e6ae60c02")


@mock_kms
def test_schedule_key_deletion_key_not_found():
    client = boto3.client("kms", region_name="us-east-1")

    with pytest.raises(client.exceptions.NotFoundException):
        client.schedule_key_deletion(KeyId="12366f9b-1230-123d-123e-123e6ae60c02")


@mock_kms
def test_get_key_rotation_status_key_not_found():
    client = boto3.client("kms", region_name="us-east-1")

    with pytest.raises(client.exceptions.NotFoundException):
        client.get_key_rotation_status(KeyId="12366f9b-1230-123d-123e-123e6ae60c02")


@mock_kms
def test_get_key_policy_key_not_found():
    client = boto3.client("kms", region_name="us-east-1")

    with pytest.raises(client.exceptions.NotFoundException):
        client.get_key_policy(
            KeyId="12366f9b-1230-123d-123e-123e6ae60c02", PolicyName="default"
        )


@mock_kms
def test_list_key_policies_key_not_found():
    client = boto3.client("kms", region_name="us-east-1")

    with pytest.raises(client.exceptions.NotFoundException):
        client.list_key_policies(KeyId="12366f9b-1230-123d-123e-123e6ae60c02")


@mock_kms
def test_put_key_policy_key_not_found():
    client = boto3.client("kms", region_name="us-east-1")

    with pytest.raises(client.exceptions.NotFoundException):
        client.put_key_policy(
            KeyId="00000000-0000-0000-0000-000000000000",
            PolicyName="default",
            Policy="new policy",
        )
