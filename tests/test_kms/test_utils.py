import pytest
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.serialization import load_der_public_key

from moto.kms.exceptions import (
    AccessDeniedException,
    InvalidCiphertextException,
    NotFoundException,
    ValidationException,
)
from moto.kms.models import Key
from moto.kms.utils import (
    MASTER_KEY_LEN,
    Ciphertext,
    ECDSAPrivateKey,
    KeySpec,
    RSAPrivateKey,
    RSAWrappingKey,
    SigningAlgorithm,
    _deserialize_ciphertext_blob,
    _serialize_ciphertext_blob,
    _serialize_encryption_context,
    decrypt,
    encrypt,
    generate_data_key,
    generate_master_key,
)

ENCRYPTION_CONTEXT_VECTORS = [
    (
        {"this": "is", "an": "encryption", "context": "example"},
        b"anencryptioncontextexamplethisis",
    ),
    (
        {"a_this": "one", "b_is": "actually", "c_in": "order"},
        b"a_thisoneb_isactuallyc_inorder",
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


def test_KeySpec_Enum():
    assert KeySpec.rsa_key_specs() == sorted(
        [KeySpec.RSA_2048, KeySpec.RSA_3072, KeySpec.RSA_4096]
    )
    assert KeySpec.ecc_key_specs() == sorted(
        [
            KeySpec.ECC_NIST_P256,
            KeySpec.ECC_SECG_P256K1,
            KeySpec.ECC_NIST_P384,
            KeySpec.ECC_NIST_P521,
        ]
    )
    assert KeySpec.hmac_key_specs() == sorted(
        [KeySpec.HMAC_224, KeySpec.HMAC_256, KeySpec.HMAC_284, KeySpec.HMAC_512]
    )


def test_SigningAlgorithm_Enum():
    assert SigningAlgorithm.rsa_signing_algorithms() == sorted(
        [
            SigningAlgorithm.RSASSA_PSS_SHA_256,
            SigningAlgorithm.RSASSA_PSS_SHA_384,
            SigningAlgorithm.RSASSA_PSS_SHA_512,
            SigningAlgorithm.RSASSA_PKCS1_V1_5_SHA_256,
            SigningAlgorithm.RSASSA_PKCS1_V1_5_SHA_384,
            SigningAlgorithm.RSASSA_PKCS1_V1_5_SHA_512,
        ]
    )
    assert SigningAlgorithm.ecc_signing_algorithms() == sorted(
        [
            SigningAlgorithm.ECDSA_SHA_256,
            SigningAlgorithm.ECDSA_SHA_384,
            SigningAlgorithm.ECDSA_SHA_512,
        ]
    )


def test_RSAPrivateKey_invalid_key_size():
    with pytest.raises(ValidationException) as ex:
        _ = RSAPrivateKey(key_size=100)
    assert (
        ex.value.message
        == "1 validation error detected: Value at 'key_size' failed to satisfy constraint: Member must satisfy enum value set: [2048, 3072, 4096]"
    )


def test_ECDSAPrivateKey_invalid_key_spec():
    with pytest.raises(ValidationException) as ex:
        _ = ECDSAPrivateKey(key_spec="InvalidKeySpec")
    assert (
        ex.value.message
        == "1 validation error detected: Value at 'key_spec' failed to satisfy constraint: Member must satisfy enum value set: ['ECC_NIST_P256', 'ECC_NIST_P384', 'ECC_NIST_P521', 'ECC_SECG_P256K1']"
    )


def test_generate_data_key():
    test = generate_data_key(123)

    assert isinstance(test, bytes)
    assert len(test) == 123


def test_generate_master_key():
    test = generate_master_key()

    assert isinstance(test, bytes)
    assert len(test) == MASTER_KEY_LEN


@pytest.mark.parametrize("raw,serialized", ENCRYPTION_CONTEXT_VECTORS)
def test_serialize_encryption_context(raw, serialized):
    test = _serialize_encryption_context(raw)
    assert test == serialized


@pytest.mark.parametrize("raw,_serialized", CIPHERTEXT_BLOB_VECTORS)
def test_cycle_ciphertext_blob(raw, _serialized):
    test_serialized = _serialize_ciphertext_blob(raw)
    test_deserialized = _deserialize_ciphertext_blob(test_serialized)
    assert test_deserialized == raw


@pytest.mark.parametrize("raw,serialized", CIPHERTEXT_BLOB_VECTORS)
def test_serialize_ciphertext_blob(raw, serialized):
    test = _serialize_ciphertext_blob(raw)
    assert test == serialized


@pytest.mark.parametrize("raw,serialized", CIPHERTEXT_BLOB_VECTORS)
def test_deserialize_ciphertext_blob(raw, serialized):
    test = _deserialize_ciphertext_blob(serialized)
    assert test == raw


@pytest.mark.parametrize(
    "encryption_context", [ec[0] for ec in ENCRYPTION_CONTEXT_VECTORS]
)
def test_encrypt_decrypt_cycle(encryption_context):
    plaintext = b"some secret plaintext"
    master_key = Key("nop", "nop", "nop", "nop", "nop", "nop")
    master_key_map = {master_key.id: master_key}

    ciphertext_blob = encrypt(
        master_keys=master_key_map,
        key_id=master_key.id,
        plaintext=plaintext,
        encryption_context=encryption_context,
    )
    assert ciphertext_blob != plaintext

    decrypted, decrypting_key_id = decrypt(
        master_keys=master_key_map,
        ciphertext_blob=ciphertext_blob,
        encryption_context=encryption_context,
    )
    assert decrypted == plaintext
    assert decrypting_key_id == master_key.id


def test_encrypt_unknown_key_id():
    with pytest.raises(NotFoundException):
        encrypt(
            master_keys={},
            key_id="anything",
            plaintext=b"secrets",
            encryption_context={},
        )


def test_decrypt_invalid_ciphertext_format():
    master_key = Key("nop", "nop", "nop", "nop", "nop", "nop")
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
    master_key = Key("nop", "nop", "nop", "nop", "nop", "nop")
    master_key_map = {master_key.id: master_key}
    ciphertext_blob = (
        master_key.id.encode("utf-8") + b"1234567890121234567890123456some ciphertext"
    )

    with pytest.raises(InvalidCiphertextException):
        decrypt(
            master_keys=master_key_map,
            ciphertext_blob=ciphertext_blob,
            encryption_context={},
        )


def test_decrypt_invalid_encryption_context():
    plaintext = b"some secret plaintext"
    master_key = Key("nop", "nop", "nop", "nop", "nop", "nop")
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


# RSAWrappingKey tests


def test_rsa_wrapping_key_supports_all_key_sizes():
    for key_size in (2048, 3072, 4096):
        wrapping_key = RSAWrappingKey(key_size)
        public_key = load_der_public_key(wrapping_key.public_key())
        assert public_key.key_size == key_size


def test_rsa_wrapping_key_rejects_invalid_key_size():
    with pytest.raises(ValidationException):
        RSAWrappingKey(1024)


def test_rsa_wrapping_key_unwrap_sha256():
    wrapping_key = RSAWrappingKey(2048)
    plaintext = b"\x00" * 32  # 256-bit key material

    # Encrypt with the public key using OAEP SHA-256
    public_key = load_der_public_key(wrapping_key.public_key())
    encrypted = public_key.encrypt(
        plaintext,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )

    # Unwrap should recover the original plaintext
    result = wrapping_key.unwrap(encrypted, "RSAES_OAEP_SHA_256")
    assert result == plaintext


def test_rsa_wrapping_key_unwrap_sha1():
    wrapping_key = RSAWrappingKey(2048)
    plaintext = b"\xab" * 32

    public_key = load_der_public_key(wrapping_key.public_key())
    encrypted = public_key.encrypt(
        plaintext,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA1()),
            algorithm=hashes.SHA1(),
            label=None,
        ),
    )

    result = wrapping_key.unwrap(encrypted, "RSAES_OAEP_SHA_1")
    assert result == plaintext


def test_rsa_wrapping_key_unwrap_rejects_invalid_algorithm():
    wrapping_key = RSAWrappingKey(2048)

    with pytest.raises(ValidationException):
        wrapping_key.unwrap(b"fake_data", "RSA_AES_KEY_WRAP_SHA_256")


def test_rsa_wrapping_key_unwrap_rejects_bad_ciphertext():
    wrapping_key = RSAWrappingKey(2048)

    with pytest.raises(ValueError):
        wrapping_key.unwrap(b"not_valid_ciphertext", "RSAES_OAEP_SHA_256")
