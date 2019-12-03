from __future__ import unicode_literals

from collections import namedtuple
import io
import os
import struct
import uuid

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import algorithms, Cipher, modes

from .exceptions import (
    InvalidCiphertextException,
    AccessDeniedException,
    NotFoundException,
)


MASTER_KEY_LEN = 32
KEY_ID_LEN = 36
IV_LEN = 12
TAG_LEN = 16
HEADER_LEN = KEY_ID_LEN + IV_LEN + TAG_LEN
# NOTE: This is just a simple binary format. It is not what KMS actually does.
CIPHERTEXT_HEADER_FORMAT = ">{key_id_len}s{iv_len}s{tag_len}s".format(
    key_id_len=KEY_ID_LEN, iv_len=IV_LEN, tag_len=TAG_LEN
)
Ciphertext = namedtuple("Ciphertext", ("key_id", "iv", "ciphertext", "tag"))


def generate_key_id():
    return str(uuid.uuid4())


def generate_data_key(number_of_bytes):
    """Generate a data key."""
    return os.urandom(number_of_bytes)


def generate_master_key():
    """Generate a master key."""
    return generate_data_key(MASTER_KEY_LEN)


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
        raise NotFoundException(
            "{id_type} {key_id} is not found.".format(
                id_type="Alias" if is_alias else "keyId", key_id=key_id
            )
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
