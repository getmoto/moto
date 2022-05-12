import sure  # noqa # pylint: disable=unused-import
import pytest

from moto.kms.exceptions import (
    AccessDeniedException,
    InvalidCiphertextException,
    NotFoundException,
)
from moto.kms.models import Key
from moto.kms.utils import (
    _deserialize_ciphertext_blob,
    _serialize_ciphertext_blob,
    _serialize_encryption_context,
    generate_data_key,
    generate_master_key,
    MASTER_KEY_LEN,
    encrypt,
    decrypt,
    Ciphertext,
)

ENCRYPTION_CONTEXT_VECTORS = [
    (
        {"this": "is", "an": "encryption", "context": "example"},
        b"an" b"encryption" b"context" b"example" b"this" b"is",
    ),
    (
        {"a_this": "one", "b_is": "actually", "c_in": "order"},
        b"a_this" b"one" b"b_is" b"actually" b"c_in" b"order",
    ),
]
CIPHERTEXT_BLOB_VECTORS = [
    (
        Ciphertext(
            key_id="d25652e4-d2d2-49f7-929a-671ccda580c6",
            iv=b"123456789012",
            ciphertext=b"some ciphertext",
            tag=b"1234567890123456",
        ),
        b"d25652e4-d2d2-49f7-929a-671ccda580c6"
        b"123456789012"
        b"1234567890123456"
        b"some ciphertext",
    ),
    (
        Ciphertext(
            key_id="d25652e4-d2d2-49f7-929a-671ccda580c6",
            iv=b"123456789012",
            ciphertext=b"some ciphertext that is much longer now",
            tag=b"1234567890123456",
        ),
        b"d25652e4-d2d2-49f7-929a-671ccda580c6"
        b"123456789012"
        b"1234567890123456"
        b"some ciphertext that is much longer now",
    ),
]


def test_generate_data_key():
    test = generate_data_key(123)

    test.should.be.a(bytes)
    len(test).should.equal(123)


def test_generate_master_key():
    test = generate_master_key()

    test.should.be.a(bytes)
    len(test).should.equal(MASTER_KEY_LEN)


@pytest.mark.parametrize("raw,serialized", ENCRYPTION_CONTEXT_VECTORS)
def test_serialize_encryption_context(raw, serialized):
    test = _serialize_encryption_context(raw)
    test.should.equal(serialized)


@pytest.mark.parametrize("raw,_serialized", CIPHERTEXT_BLOB_VECTORS)
def test_cycle_ciphertext_blob(raw, _serialized):
    test_serialized = _serialize_ciphertext_blob(raw)
    test_deserialized = _deserialize_ciphertext_blob(test_serialized)
    test_deserialized.should.equal(raw)


@pytest.mark.parametrize("raw,serialized", CIPHERTEXT_BLOB_VECTORS)
def test_serialize_ciphertext_blob(raw, serialized):
    test = _serialize_ciphertext_blob(raw)
    test.should.equal(serialized)


@pytest.mark.parametrize("raw,serialized", CIPHERTEXT_BLOB_VECTORS)
def test_deserialize_ciphertext_blob(raw, serialized):
    test = _deserialize_ciphertext_blob(serialized)
    test.should.equal(raw)


@pytest.mark.parametrize(
    "encryption_context", [ec[0] for ec in ENCRYPTION_CONTEXT_VECTORS]
)
def test_encrypt_decrypt_cycle(encryption_context):
    plaintext = b"some secret plaintext"
    master_key = Key("nop", "nop", "nop", "nop", "nop")
    master_key_map = {master_key.id: master_key}

    ciphertext_blob = encrypt(
        master_keys=master_key_map,
        key_id=master_key.id,
        plaintext=plaintext,
        encryption_context=encryption_context,
    )
    ciphertext_blob.should_not.equal(plaintext)

    decrypted, decrypting_key_id = decrypt(
        master_keys=master_key_map,
        ciphertext_blob=ciphertext_blob,
        encryption_context=encryption_context,
    )
    decrypted.should.equal(plaintext)
    decrypting_key_id.should.equal(master_key.id)


def test_encrypt_unknown_key_id():
    with pytest.raises(NotFoundException):
        encrypt(
            master_keys={},
            key_id="anything",
            plaintext=b"secrets",
            encryption_context={},
        )


def test_decrypt_invalid_ciphertext_format():
    master_key = Key("nop", "nop", "nop", "nop", "nop")
    master_key_map = {master_key.id: master_key}

    with pytest.raises(InvalidCiphertextException):
        decrypt(master_keys=master_key_map, ciphertext_blob=b"", encryption_context={})


def test_decrypt_unknwown_key_id():
    ciphertext_blob = (
        b"d25652e4-d2d2-49f7-929a-671ccda580c6"
        b"123456789012"
        b"1234567890123456"
        b"some ciphertext"
    )

    with pytest.raises(AccessDeniedException):
        decrypt(master_keys={}, ciphertext_blob=ciphertext_blob, encryption_context={})


def test_decrypt_invalid_ciphertext():
    master_key = Key("nop", "nop", "nop", "nop", "nop")
    master_key_map = {master_key.id: master_key}
    ciphertext_blob = (
        master_key.id.encode("utf-8") + b"123456789012"
        b"1234567890123456"
        b"some ciphertext"
    )

    with pytest.raises(InvalidCiphertextException):
        decrypt(
            master_keys=master_key_map,
            ciphertext_blob=ciphertext_blob,
            encryption_context={},
        )


def test_decrypt_invalid_encryption_context():
    plaintext = b"some secret plaintext"
    master_key = Key("nop", "nop", "nop", "nop", "nop")
    master_key_map = {master_key.id: master_key}

    ciphertext_blob = encrypt(
        master_keys=master_key_map,
        key_id=master_key.id,
        plaintext=plaintext,
        encryption_context={"some": "encryption", "context": "here"},
    )

    with pytest.raises(InvalidCiphertextException):
        decrypt(
            master_keys=master_key_map,
            ciphertext_blob=ciphertext_blob,
            encryption_context={},
        )
