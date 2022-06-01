import pytest
import sure  # noqa # pylint: disable=unused-import

from moto.kms.models import KmsBackend

PLAINTEXT = b"text"
REGION = "us-east-1"


@pytest.fixture
def backend():
    return KmsBackend(REGION)


@pytest.fixture
def key(backend):
    return backend.create_key(
        None, "ENCRYPT_DECRYPT", "SYMMETRIC_DEFAULT", "Test key", None, REGION
    )


def test_encrypt_key_id(backend, key):
    ciphertext, arn = backend.encrypt(key.id, PLAINTEXT, {})

    ciphertext.shouldnt.be.none
    arn.shouldnt.be.none


def test_encrypt_key_arn(backend, key):
    ciphertext, arn = backend.encrypt(key.arn, PLAINTEXT, {})

    ciphertext.shouldnt.be.none
    arn.shouldnt.be.none


def test_encrypt_alias_name(backend, key):
    backend.add_alias(key.id, "alias/test/test")

    ciphertext, arn = backend.encrypt("alias/test/test", PLAINTEXT, {})

    ciphertext.shouldnt.be.none
    arn.shouldnt.be.none


def test_encrypt_alias_arn(backend, key):
    backend.add_alias(key.id, "alias/test/test")

    ciphertext, arn = backend.encrypt(
        "arn:aws:kms::000000000000:alias/test/test", PLAINTEXT, {}
    )

    ciphertext.shouldnt.be.none
    arn.shouldnt.be.none
