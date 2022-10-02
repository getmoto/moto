import pytest

from moto.kms.models import KmsBackend

PLAINTEXT = b"text"
REGION = "us-east-1"


@pytest.fixture(name="backend")
def fixture_backend():
    return KmsBackend(REGION)


@pytest.fixture(name="key")
def fixture_key(backend):
    return backend.create_key(
        None, "ENCRYPT_DECRYPT", "SYMMETRIC_DEFAULT", "Test key", None
    )


def test_encrypt_key_id(backend, key):
    ciphertext, arn = backend.encrypt(key.id, PLAINTEXT, {})

    assert ciphertext is not None
    assert arn == key.arn


def test_encrypt_key_arn(backend, key):
    ciphertext, arn = backend.encrypt(key.arn, PLAINTEXT, {})

    assert ciphertext is not None
    assert arn == key.arn


def test_encrypt_alias_name(backend, key):
    backend.add_alias(key.id, "alias/test/test")

    ciphertext, arn = backend.encrypt("alias/test/test", PLAINTEXT, {})

    assert ciphertext is not None
    assert arn == key.arn


def test_encrypt_alias_arn(backend, key):
    backend.add_alias(key.id, "alias/test/test")

    ciphertext, arn = backend.encrypt(
        f"arn:aws:kms:{REGION}:{key.account_id}:alias/test/test", PLAINTEXT, {}
    )

    assert ciphertext is not None
    assert arn == key.arn
