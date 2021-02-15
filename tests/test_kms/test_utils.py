from __future__ import unicode_literals

from itertools import product

import sure  # noqa
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa, ec

from moto.kms.exceptions import (
    AccessDeniedException,
    InvalidCiphertextException,
    NotFoundException,
)
from moto.kms.models import Key
from moto.kms.utils import (
    deserialize_ciphertext_blob,
    serialize_ciphertext_blob,
    _serialize_encryption_context,
    generate_data_key,
    generate_master_key,
    MASTER_KEY_LEN,
    encrypt,
    decrypt,
    Ciphertext,
    sign,
    verify,
    KEY_SPECS,
    signing_algorithms,
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
    for key_spec in KEY_SPECS:
        test = generate_master_key(key_spec)

        if key_spec == "SYMMETRIC_DEFAULT":
            test.should.be.a(bytes)
            len(test).should.equal(MASTER_KEY_LEN)
        elif key_spec[:3] == "RSA":
            test.should.be.a(rsa.RSAPrivateKey)
        elif key_spec[:3] == "ECC":
            test.should.be.a(ec.EllipticCurvePrivateKey)


@pytest.mark.parametrize("raw,serialized", ENCRYPTION_CONTEXT_VECTORS)
def test_serialize_encryption_context(raw, serialized):
    test = _serialize_encryption_context(raw)
    test.should.equal(serialized)


@pytest.mark.parametrize("raw,_serialized", CIPHERTEXT_BLOB_VECTORS)
def test_cycle_ciphertext_blob(raw, _serialized):
    test_serialized = serialize_ciphertext_blob(raw)
    test_deserialized = deserialize_ciphertext_blob(test_serialized)
    test_deserialized.should.equal(raw)


@pytest.mark.parametrize("raw,serialized", CIPHERTEXT_BLOB_VECTORS)
def test_serialize_ciphertext_blob(raw, serialized):
    test = serialize_ciphertext_blob(raw)
    test.should.equal(serialized)


@pytest.mark.parametrize("raw,serialized", CIPHERTEXT_BLOB_VECTORS)
def test_deserialize_ciphertext_blob(raw, serialized):
    test = deserialize_ciphertext_blob(serialized)
    test.should.equal(raw)


@pytest.mark.parametrize(
    "encryption_context", [ec[0] for ec in ENCRYPTION_CONTEXT_VECTORS]
)
def test_encrypt_decrypt_cycle(encryption_context):
    plaintext = b"some secret plaintext"
    master_key = Key("nop", "nop", "RSA_2048", "nop", "nop")
    master_key_map = {master_key.id: master_key}

    ciphertext = encrypt(
        master_keys=master_key_map,
        key_id=master_key.id,
        plaintext=plaintext,
        encryption_context=encryption_context,
        encryption_algorithm="RSAES_OAEP_SHA_256",
        # TODO: all the other algorithms
    )
    ciphertext.should_not.equal(plaintext)

    decrypted, decrypting_key_id = decrypt(
        master_keys=master_key_map,
        ciphertext=ciphertext,
        encryption_context=encryption_context,
        encryption_algorithm="RSAES_OAEP_SHA_256",
        key_id=master_key.id,
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
            encryption_algorithm="SYMMETRIC_DEFAULT",
        )


def test_decrypt_invalid_ciphertext_format():
    master_key = Key("nop", "nop", None, "nop", "nop")
    master_key_map = {master_key.id: master_key}

    with pytest.raises(InvalidCiphertextException):
        decrypt(
            master_keys=master_key_map,
            ciphertext=b"",
            encryption_context={},
            encryption_algorithm="SYMMETRIC_DEFAULT",
            key_id=master_key.id,
        )


def test_decrypt_unknown_key_id():
    ciphertext = (
        b"d25652e4-d2d2-49f7-929a-671ccda580c6"
        b"123456789012"
        b"1234567890123456"
        b"some ciphertext"
    )

    with pytest.raises(AccessDeniedException):
        decrypt(
            master_keys={},
            ciphertext=ciphertext,
            encryption_context={},
            encryption_algorithm="SYMMETRIC_DEFAULT",
            key_id=None,
        )


def test_decrypt_invalid_ciphertext():
    master_key = Key("nop", "nop", None, "nop", "nop")
    master_key_map = {master_key.id: master_key}
    ciphertext = (
        master_key.id.encode("utf-8") + b"123456789012"
        b"1234567890123456"
        b"some ciphertext"
    )

    with pytest.raises(InvalidCiphertextException):
        decrypt(
            master_keys=master_key_map,
            ciphertext=ciphertext,
            encryption_context={},
            encryption_algorithm="SYMMETRIC_DEFAULT",
            key_id=master_key.id,
        )


def test_decrypt_invalid_encryption_context():
    plaintext = b"some secret plaintext"
    master_key = Key("nop", "nop", None, "nop", "nop")
    master_key_map = {master_key.id: master_key}

    ciphertext = encrypt(
        master_keys=master_key_map,
        key_id=master_key.id,
        plaintext=plaintext,
        encryption_context={"some": "encryption", "context": "here"},
        encryption_algorithm="SYMMETRIC_DEFAULT",
    )

    with pytest.raises(InvalidCiphertextException):
        decrypt(
            master_keys=master_key_map,
            ciphertext=ciphertext,
            encryption_context={},
            encryption_algorithm="SYMMETRIC_DEFAULT",
            key_id=master_key.id,
        )


@pytest.mark.parametrize(
    "encryption_context,signing_algorithm",
    product([ec[0] for ec in ENCRYPTION_CONTEXT_VECTORS], signing_algorithms.keys()),
)
def test_sign_verify_cycle(encryption_context, signing_algorithm):
    message = b"this is a message which needs to be signed."
    master_key = Key("nop", "nop", "RSA_4096", "nop", "nop")
    master_key_map = {master_key.id: master_key}

    signature = sign(
        master_keys=master_key_map,
        key_id=master_key.id,
        message=message,
        message_type="RAW",
        signing_algorithm=signing_algorithm,
    )

    verified = verify(
        master_keys=master_key_map,
        key_id=master_key.id,
        message=message,
        message_type="RAW",
        signature=signature,
        signing_algorithm=signing_algorithm,
    )

    verified.should.be(True)
