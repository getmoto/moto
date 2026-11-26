"""Tests against the AWS SDK for Python v4: https://github.com/aws/aws-sdk-python"""

from uuid import uuid4

import pytest

from moto import mock_aws

try:
    from aws_sdk_kms import KMSClient, KMSConfig
    from aws_sdk_kms.models import DisabledException
except ImportError:  # Requires Python 3.12+
    pytest.skip("aws-sdk-kms is not installed", allow_module_level=True)


@pytest.mark.skip(
    reason="Moto returns a 'null' body for operations without output, like CreateAlias/EnableKeyRotation/DisableKey, which the SDK can't parse (it expects '{}'). "
    "Moto also doesn't throw a DisabledException when encrypting with a disabled key"
)
@mock_aws
def test_envelope_encryption():
    """Create a customer-managed key, and use it for envelope encryption."""
    config = KMSConfig.resolve(region="us-east-1")
    alias_name = f"alias/payments-{uuid4()}"
    context = {"department": "payments"}

    with KMSClient(config=config) as client:
        key = client.create_key(
            description="Encrypts payment data",
            key_usage="ENCRYPT_DECRYPT",
            tags=[{"tag_key": "team", "tag_value": "payments"}],
        ).key_metadata
        assert key.enabled is True
        assert key.key_state == "Enabled"
        assert key.description == "Encrypts payment data"

        client.create_alias(alias_name=alias_name, target_key_id=key.key_id)
        aliases = client.list_aliases(key_id=key.key_id).aliases
        assert [alias.alias_name for alias in aliases] == [alias_name]

        client.enable_key_rotation(key_id=key.key_id)
        assert client.get_key_rotation_status(key_id=key.key_id).key_rotation_enabled

        # Generate a data key to encrypt data locally
        data_key = client.generate_data_key(
            key_id=alias_name, key_spec="AES_256", encryption_context=context
        )
        assert len(data_key.plaintext) == 32
        assert data_key.key_id == key.arn

        # Later on: decrypt the stored data key
        decrypted_key = client.decrypt(
            ciphertext_blob=data_key.ciphertext_blob, encryption_context=context
        )
        assert decrypted_key.plaintext == data_key.plaintext
        assert decrypted_key.key_id == key.arn

        # Small secrets can be encrypted with the KMS key directly
        encrypted = client.encrypt(
            key_id=alias_name,
            plaintext=b"4111-1111-1111-1111",
            encryption_context=context,
        )
        decrypted = client.decrypt(
            ciphertext_blob=encrypted.ciphertext_blob, encryption_context=context
        )
        assert decrypted.plaintext == b"4111-1111-1111-1111"

        client.disable_key(key_id=key.key_id)
        with pytest.raises(DisabledException):
            client.encrypt(key_id=key.key_id, plaintext=b"secret")

        deletion = client.schedule_key_deletion(
            key_id=key.key_id, pending_window_in_days=7
        )
        assert deletion.deletion_date is not None
        key = client.describe_key(key_id=key.key_id).key_metadata
        assert key.key_state == "PendingDeletion"
