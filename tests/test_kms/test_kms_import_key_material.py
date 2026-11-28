import boto3
import pytest
from botocore.exceptions import ClientError
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.serialization import load_der_public_key

from moto import mock_aws

STATIC_KEY_MATERIAL = b"\x00" * 32  # 256-bit key for testing


def _encrypt_key_material(public_key_bytes: bytes, key_material: bytes) -> bytes:
    """Encrypt key material using the wrapping public key with OAEP SHA-256."""
    public_key = load_der_public_key(public_key_bytes)
    return public_key.encrypt(
        key_material,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )


@mock_aws
def test_create_key_with_external_origin():
    """A key with EXTERNAL origin should be in PendingImport state with no key material."""
    client = boto3.client("kms", region_name="us-east-1")

    key = client.create_key(Origin="EXTERNAL")["KeyMetadata"]

    assert key["Origin"] == "EXTERNAL"
    assert key["KeyState"] == "PendingImport"
    assert key["Enabled"] is False


@mock_aws
def test_get_parameters_for_import_happy_path():
    """get_parameters_for_import returns a public key and import token."""
    client = boto3.client("kms", region_name="us-east-1")

    key = client.create_key(Origin="EXTERNAL")["KeyMetadata"]
    key_id = key["KeyId"]

    response = client.get_parameters_for_import(
        KeyId=key_id,
        WrappingAlgorithm="RSAES_OAEP_SHA_256",
        WrappingKeySpec="RSA_2048",
    )

    assert "PublicKey" in response
    assert "ImportToken" in response
    assert "ParametersValidTo" in response
    assert response["KeyId"] == key_id

    # Verify public key is valid DER
    public_key = load_der_public_key(response["PublicKey"])
    assert public_key.key_size == 2048


@mock_aws
def test_get_parameters_for_import_non_external_key():
    """get_parameters_for_import should fail on a key with AWS_KMS origin."""
    client = boto3.client("kms", region_name="us-east-1")

    key = client.create_key()["KeyMetadata"]
    key_id = key["KeyId"]

    with pytest.raises(ClientError) as exc:
        client.get_parameters_for_import(
            KeyId=key_id,
            WrappingAlgorithm="RSAES_OAEP_SHA_256",
            WrappingKeySpec="RSA_2048",
        )

    err = exc.value.response["Error"]
    assert err["Code"] == "UnsupportedOperationException"


@mock_aws
def test_import_key_material_happy_path():
    """Full flow: create EXTERNAL key, get params, import material, encrypt/decrypt."""
    client = boto3.client("kms", region_name="us-east-1")

    # Create EXTERNAL key
    key = client.create_key(Origin="EXTERNAL")["KeyMetadata"]
    key_id = key["KeyId"]

    # Get wrapping parameters
    params = client.get_parameters_for_import(
        KeyId=key_id,
        WrappingAlgorithm="RSAES_OAEP_SHA_256",
        WrappingKeySpec="RSA_2048",
    )

    # Encrypt key material with the public key
    encrypted_key_material = _encrypt_key_material(
        params["PublicKey"], STATIC_KEY_MATERIAL
    )

    # Import key material
    client.import_key_material(
        KeyId=key_id,
        ImportToken=params["ImportToken"],
        EncryptedKeyMaterial=encrypted_key_material,
        ExpirationModel="KEY_MATERIAL_DOES_NOT_EXPIRE",
    )

    # Verify key is now enabled
    key_desc = client.describe_key(KeyId=key_id)["KeyMetadata"]
    assert key_desc["KeyState"] == "Enabled"
    assert key_desc["Enabled"] is True

    # Verify encrypt/decrypt works
    plaintext = b"Hello, World!"
    encrypt_response = client.encrypt(KeyId=key_id, Plaintext=plaintext)
    decrypt_response = client.decrypt(CiphertextBlob=encrypt_response["CiphertextBlob"])
    assert decrypt_response["Plaintext"] == plaintext


@mock_aws
def test_import_key_material_non_external_key():
    """import_key_material should fail on a key with AWS_KMS origin."""
    client = boto3.client("kms", region_name="us-east-1")

    key = client.create_key()["KeyMetadata"]
    key_id = key["KeyId"]

    with pytest.raises(ClientError) as exc:
        client.import_key_material(
            KeyId=key_id,
            ImportToken=b"fake-token",
            EncryptedKeyMaterial=b"fake-material",
            ExpirationModel="KEY_MATERIAL_DOES_NOT_EXPIRE",
        )

    err = exc.value.response["Error"]
    assert err["Code"] == "UnsupportedOperationException"


@mock_aws
def test_import_key_material_invalid_token():
    """import_key_material should fail with a wrong import token."""
    client = boto3.client("kms", region_name="us-east-1")

    key = client.create_key(Origin="EXTERNAL")["KeyMetadata"]
    key_id = key["KeyId"]

    # Get params to initialize wrapping key
    client.get_parameters_for_import(
        KeyId=key_id,
        WrappingAlgorithm="RSAES_OAEP_SHA_256",
        WrappingKeySpec="RSA_2048",
    )

    with pytest.raises(ClientError) as exc:
        client.import_key_material(
            KeyId=key_id,
            ImportToken=b"wrong-token",
            EncryptedKeyMaterial=b"fake-material",
            ExpirationModel="KEY_MATERIAL_DOES_NOT_EXPIRE",
        )

    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidImportTokenException"


@mock_aws
def test_delete_imported_key_material():
    """delete_imported_key_material should reset key to PendingImport state."""
    client = boto3.client("kms", region_name="us-east-1")

    # Create and import key material
    key = client.create_key(Origin="EXTERNAL")["KeyMetadata"]
    key_id = key["KeyId"]

    params = client.get_parameters_for_import(
        KeyId=key_id,
        WrappingAlgorithm="RSAES_OAEP_SHA_256",
        WrappingKeySpec="RSA_2048",
    )

    encrypted_key_material = _encrypt_key_material(
        params["PublicKey"], STATIC_KEY_MATERIAL
    )

    client.import_key_material(
        KeyId=key_id,
        ImportToken=params["ImportToken"],
        EncryptedKeyMaterial=encrypted_key_material,
        ExpirationModel="KEY_MATERIAL_DOES_NOT_EXPIRE",
    )

    # Verify key is enabled
    key_desc = client.describe_key(KeyId=key_id)["KeyMetadata"]
    assert key_desc["KeyState"] == "Enabled"

    # Delete imported key material
    client.delete_imported_key_material(KeyId=key_id)

    # Verify key is back to PendingImport
    key_desc = client.describe_key(KeyId=key_id)["KeyMetadata"]
    assert key_desc["KeyState"] == "PendingImport"
    assert key_desc["Enabled"] is False

    # Verify encrypt no longer works
    with pytest.raises(ClientError):
        client.encrypt(KeyId=key_id, Plaintext=b"test")
    # Key in PendingImport state should not be usable


@mock_aws
def test_delete_imported_key_material_non_external_key():
    """delete_imported_key_material should fail on a key with AWS_KMS origin."""
    client = boto3.client("kms", region_name="us-east-1")

    key = client.create_key()["KeyMetadata"]
    key_id = key["KeyId"]

    with pytest.raises(ClientError) as exc:
        client.delete_imported_key_material(KeyId=key_id)

    err = exc.value.response["Error"]
    assert err["Code"] == "UnsupportedOperationException"


@mock_aws
def test_reimport_same_key_material():
    """Reimporting key material into an already-enabled key should succeed."""
    client = boto3.client("kms", region_name="us-east-1")

    key = client.create_key(Origin="EXTERNAL")["KeyMetadata"]
    key_id = key["KeyId"]

    # First import
    params = client.get_parameters_for_import(
        KeyId=key_id,
        WrappingAlgorithm="RSAES_OAEP_SHA_256",
        WrappingKeySpec="RSA_2048",
    )
    encrypted_key_material = _encrypt_key_material(
        params["PublicKey"], STATIC_KEY_MATERIAL
    )
    client.import_key_material(
        KeyId=key_id,
        ImportToken=params["ImportToken"],
        EncryptedKeyMaterial=encrypted_key_material,
        ExpirationModel="KEY_MATERIAL_DOES_NOT_EXPIRE",
    )

    # Encrypt something
    plaintext = b"test data"
    encrypt_response = client.encrypt(KeyId=key_id, Plaintext=plaintext)

    # Reimport the same key material (need fresh params)
    params2 = client.get_parameters_for_import(
        KeyId=key_id,
        WrappingAlgorithm="RSAES_OAEP_SHA_256",
        WrappingKeySpec="RSA_2048",
    )
    encrypted_key_material2 = _encrypt_key_material(
        params2["PublicKey"], STATIC_KEY_MATERIAL
    )
    client.import_key_material(
        KeyId=key_id,
        ImportToken=params2["ImportToken"],
        EncryptedKeyMaterial=encrypted_key_material2,
        ExpirationModel="KEY_MATERIAL_DOES_NOT_EXPIRE",
    )

    # Should still be able to decrypt with the same key material
    decrypt_response = client.decrypt(CiphertextBlob=encrypt_response["CiphertextBlob"])
    assert decrypt_response["Plaintext"] == plaintext


@mock_aws
def test_import_key_material_with_sha1_wrapping():
    """Import key material using RSAES_OAEP_SHA_1 wrapping algorithm."""
    client = boto3.client("kms", region_name="us-east-1")

    key = client.create_key(Origin="EXTERNAL")["KeyMetadata"]
    key_id = key["KeyId"]

    params = client.get_parameters_for_import(
        KeyId=key_id,
        WrappingAlgorithm="RSAES_OAEP_SHA_1",
        WrappingKeySpec="RSA_2048",
    )

    # Encrypt with SHA-1 OAEP
    public_key = load_der_public_key(params["PublicKey"])
    encrypted_key_material = public_key.encrypt(
        STATIC_KEY_MATERIAL,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA1()),
            algorithm=hashes.SHA1(),
            label=None,
        ),
    )

    client.import_key_material(
        KeyId=key_id,
        ImportToken=params["ImportToken"],
        EncryptedKeyMaterial=encrypted_key_material,
        ExpirationModel="KEY_MATERIAL_DOES_NOT_EXPIRE",
    )

    # Verify works
    key_desc = client.describe_key(KeyId=key_id)["KeyMetadata"]
    assert key_desc["KeyState"] == "Enabled"

    plaintext = b"SHA1 wrapping test"
    encrypt_response = client.encrypt(KeyId=key_id, Plaintext=plaintext)
    decrypt_response = client.decrypt(CiphertextBlob=encrypt_response["CiphertextBlob"])
    assert decrypt_response["Plaintext"] == plaintext
