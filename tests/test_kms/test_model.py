import sure  # noqa # pylint: disable=unused-import

from moto.kms.models import KmsBackend


def test_encrypt_key_id():
    region = "us-east-1"
    backend = KmsBackend(region)
    # Create key
    key = backend.create_key(
        None, "ENCRYPT_DECRYPT", "SYMMETRIC_DEFAULT", "Test key", None, region
    )
    # Create alias
    backend.add_alias(key.id, "alias/test/test")

    # Test encryption
    ciphertext, arn = backend.encrypt(key.id, b"text", {})

    ciphertext.shouldnt.be.none
    arn.shouldnt.be.none


def test_encrypt_key_arn():
    region = "us-east-1"
    backend = KmsBackend(region)
    # Create key
    key = backend.create_key(
        None, "ENCRYPT_DECRYPT", "SYMMETRIC_DEFAULT", "Test key", None, region
    )

    # Test encryption
    ciphertext, arn = backend.encrypt(key.arn, b"text", {})

    ciphertext.shouldnt.be.none
    arn.shouldnt.be.none


def test_encrypt_alias_name():
    region = "us-east-1"
    backend = KmsBackend(region)
    # Create key
    key = backend.create_key(
        None, "ENCRYPT_DECRYPT", "SYMMETRIC_DEFAULT", "Test key", None, region
    )
    # Create alias
    backend.add_alias(key.id, "alias/test/test")

    # Test encryption
    ciphertext, arn = backend.encrypt("alias/test/test", b"text", {})

    ciphertext.shouldnt.be.none
    arn.shouldnt.be.none


def test_encrypt_alias_arn():
    region = "us-east-1"
    backend = KmsBackend(region)
    # Create key
    key = backend.create_key(
        None, "ENCRYPT_DECRYPT", "SYMMETRIC_DEFAULT", "Test key", None, region
    )
    # Create alias
    backend.add_alias(key.id, "alias/test/test")

    # Test encryption
    ciphertext, arn = backend.encrypt(
        "arn:aws:kms::000000000000:alias/test/test", b"text", {}
    )

    ciphertext.shouldnt.be.none
    arn.shouldnt.be.none
