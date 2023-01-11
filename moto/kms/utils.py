from collections import namedtuple
import io
import os
import struct
from moto.moto_api._internal import mock_random

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import algorithms, Cipher, modes
from cryptography.hazmat.primitives.asymmetric import rsa

from .exceptions import (
    InvalidCiphertextException,
    AccessDeniedException,
    NotFoundException,
    ValidationException,
)


MASTER_KEY_LEN = 32
KEY_ID_LEN = 36
IV_LEN = 12
TAG_LEN = 16
HEADER_LEN = KEY_ID_LEN + IV_LEN + TAG_LEN
# NOTE: This is just a simple binary format. It is not what KMS actually does.
CIPHERTEXT_HEADER_FORMAT = f">{KEY_ID_LEN}s{IV_LEN}s{TAG_LEN}s"
Ciphertext = namedtuple("Ciphertext", ("key_id", "iv", "ciphertext", "tag"))

RESERVED_ALIASE_TARGET_KEY_IDS = {
    # NOTE: These would technically differ across account, but in that they are
    # out of customer control, testing that they are different would be redundant.
    "alias/aws/acm": "4f58743d-e279-4214-9270-8cc28277958d",
    "alias/aws/dynamodb": "7e6aa0ea-15a4-4e72-8b32-58e46e776888",
    "alias/aws/ebs": "7adeb491-68c9-4a5b-86ec-a86ce5364094",
    "alias/aws/elasticfilesystem": "0ef0f111-cdc8-4dda-b0bc-bf625bd5f154",
    "alias/aws/es": "3c7c1880-c353-4cea-9866-d8bc12f05573",
    "alias/aws/glue": "90fd783f-e582-4cc2-a207-672ee67f8d58",
    "alias/aws/kinesisvideo": "7fd4bff3-6eb7-4283-8f11-a7e0a793a181",
    "alias/aws/lambda": "ff9c4f27-2f29-4d9b-bf38-02f88b52a70c",
    "alias/aws/rds": "f5f30938-abed-41a2-a0f6-5482d02a2489",
    "alias/aws/redshift": "dcdae9aa-593a-4e0b-9153-37325591901f",
    "alias/aws/s3": "8c3faf07-f43c-4d11-abdb-9183079214c7",
    "alias/aws/secretsmanager": "fee5173a-3972-428e-ae73-cd4c2a371222",
    "alias/aws/ssm": "cb3f6250-5078-48c0-a75f-0290bf47694e",
    "alias/aws/xray": "e9b758eb-6230-4744-93d1-ad3b7d71f2f6",
}

RESERVED_ALIASES = list(RESERVED_ALIASE_TARGET_KEY_IDS.keys())


def generate_key_id(multi_region=False):
    key = str(mock_random.uuid4())
    # https://docs.aws.amazon.com/kms/latest/developerguide/multi-region-keys-overview.html
    # "Notice that multi-Region keys have a distinctive key ID that begins with mrk-. You can use the mrk- prefix to
    # identify MRKs programmatically."
    if multi_region:
        key = "mrk-" + key

    return key


def generate_data_key(number_of_bytes):
    """Generate a data key."""
    return os.urandom(number_of_bytes)


def generate_master_key():
    """Generate a master key."""
    return generate_data_key(MASTER_KEY_LEN)


def generate_private_key():
    """Generate a private key to be used on asymmetric sign/verify.

    NOTE: KeySpec is not taken into consideration and the key is always RSA_2048
    this could be improved to support multiple key types
    """
    return rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )


def _serialize_ciphertext_blob(ciphertext):
    """Serialize Ciphertext object into a ciphertext blob.

    NOTE: This is just a simple binary format. It is not what KMS actually does.
    """
    header = struct.pack(
        CIPHERTEXT_HEADER_FORMAT,
        ciphertext.key_id.encode("utf-8"),
        ciphertext.iv,
        ciphertext.tag,
    )
    return header + ciphertext.ciphertext


def _deserialize_ciphertext_blob(ciphertext_blob):
    """Deserialize ciphertext blob into a Ciphertext object.

    NOTE: This is just a simple binary format. It is not what KMS actually does.
    """
    header = ciphertext_blob[:HEADER_LEN]
    ciphertext = ciphertext_blob[HEADER_LEN:]
    key_id, iv, tag = struct.unpack(CIPHERTEXT_HEADER_FORMAT, header)
    return Ciphertext(
        key_id=key_id.decode("utf-8"), iv=iv, ciphertext=ciphertext, tag=tag
    )


def _serialize_encryption_context(encryption_context):
    """Serialize encryption context for use a AAD.

    NOTE: This is not necessarily what KMS does, but it retains the same properties.
    """
    aad = io.BytesIO()
    for key, value in sorted(encryption_context.items(), key=lambda x: x[0]):
        aad.write(key.encode("utf-8"))
        aad.write(value.encode("utf-8"))
    return aad.getvalue()


def encrypt(master_keys, key_id, plaintext, encryption_context):
    """Encrypt data using a master key material.

    NOTE: This is not necessarily what KMS does, but it retains the same properties.

    NOTE: This function is NOT compatible with KMS APIs.
    :param dict master_keys: Mapping of a KmsBackend's known master keys
    :param str key_id: Key ID of moto master key
    :param bytes plaintext: Plaintext data to encrypt
    :param dict[str, str] encryption_context: KMS-style encryption context
    :returns: Moto-structured ciphertext blob encrypted under a moto master key in master_keys
    :rtype: bytes
    """
    try:
        key = master_keys[key_id]
    except KeyError:
        is_alias = key_id.startswith("alias/") or ":alias/" in key_id
        id_type = "Alias" if is_alias else "keyId"
        raise NotFoundException(f"{id_type} {key_id} is not found.")

    if plaintext == b"":
        raise ValidationException(
            "1 validation error detected: Value at 'plaintext' failed to satisfy constraint: Member must have length greater than or equal to 1"
        )

    iv = os.urandom(IV_LEN)
    aad = _serialize_encryption_context(encryption_context=encryption_context)

    encryptor = Cipher(
        algorithms.AES(key.key_material), modes.GCM(iv), backend=default_backend()
    ).encryptor()
    encryptor.authenticate_additional_data(aad)
    ciphertext = encryptor.update(plaintext) + encryptor.finalize()
    return _serialize_ciphertext_blob(
        ciphertext=Ciphertext(
            key_id=key_id, iv=iv, ciphertext=ciphertext, tag=encryptor.tag
        )
    )


def decrypt(master_keys, ciphertext_blob, encryption_context):
    """Decrypt a ciphertext blob using a master key material.

    NOTE: This is not necessarily what KMS does, but it retains the same properties.

    NOTE: This function is NOT compatible with KMS APIs.

    :param dict master_keys: Mapping of a KmsBackend's known master keys
    :param bytes ciphertext_blob: moto-structured ciphertext blob encrypted under a moto master key in master_keys
    :param dict[str, str] encryption_context: KMS-style encryption context
    :returns: plaintext bytes and moto key ID
    :rtype: bytes and str
    """
    try:
        ciphertext = _deserialize_ciphertext_blob(ciphertext_blob=ciphertext_blob)
    except Exception:
        raise InvalidCiphertextException()

    aad = _serialize_encryption_context(encryption_context=encryption_context)

    try:
        key = master_keys[ciphertext.key_id]
    except KeyError:
        raise AccessDeniedException(
            "The ciphertext refers to a customer master key that does not exist, "
            "does not exist in this region, or you are not allowed to access."
        )

    try:
        decryptor = Cipher(
            algorithms.AES(key.key_material),
            modes.GCM(ciphertext.iv, ciphertext.tag),
            backend=default_backend(),
        ).decryptor()
        decryptor.authenticate_additional_data(aad)
        plaintext = decryptor.update(ciphertext.ciphertext) + decryptor.finalize()
    except Exception:
        raise InvalidCiphertextException()

    return plaintext, ciphertext.key_id
