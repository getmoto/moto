from __future__ import unicode_literals

from collections import namedtuple
import io
import os
import struct
import uuid

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa, ec, utils
from cryptography.hazmat.primitives.ciphers import algorithms, Cipher, modes

from .exceptions import (
    InvalidCiphertextException,
    AccessDeniedException,
    NotFoundException,
)
from ..core.exceptions import JsonRESTError

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

signing_algorithms = {
    "RSASSA_PSS_SHA_256": {
        "padding": padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()), salt_length=int(256 / 8)
        ),
        "hash": hashes.SHA256(),
    },
    "RSASSA_PSS_SHA_384": {
        "padding": padding.PSS(
            mgf=padding.MGF1(hashes.SHA384()), salt_length=int(384 / 8)
        ),
        "hash": hashes.SHA256(),
    },
    "RSASSA_PSS_SHA_512": {
        "padding": padding.PSS(
            mgf=padding.MGF1(hashes.SHA512()), salt_length=int(512 / 8)
        ),
        "hash": hashes.SHA256(),
    },
    "RSASSA_PKCS1_V1_5_SHA_256": {
        "padding": padding.PKCS1v15(),
        "hash": hashes.SHA256(),
    },
    "RSASSA_PKCS1_V1_5_SHA_384": {
        "padding": padding.PKCS1v15(),
        "hash": hashes.SHA384(),
    },
    "RSASSA_PKCS1_V1_5_SHA_512": {
        "padding": padding.PKCS1v15(),
        "hash": hashes.SHA512(),
    },
}

encryption_algorithms = {
    "RSAES_OAEP_SHA_1": {
        "padding": padding.OAEP(
            mgf=padding.MGF1(hashes.SHA1()), algorithm=hashes.SHA1(), label=None
        )
    },
    "RSAES_OAEP_SHA_256": {
        "padding": padding.OAEP(
            mgf=padding.MGF1(hashes.SHA256()), algorithm=hashes.SHA256(), label=None
        )
    },
}

key_specs = {
    "SYMMETRIC_DEFAULT": {"generate": lambda: generate_data_key(MASTER_KEY_LEN),},
    "RSA_2048": {
        "generate": lambda: rsa.generate_private_key(
            public_exponent=65537, key_size=2048
        ),
    },
    "RSA_3072": {
        "generate": lambda: rsa.generate_private_key(
            public_exponent=65537, key_size=3072
        ),
    },
    "RSA_4096": {
        "generate": lambda: rsa.generate_private_key(
            public_exponent=65537, key_size=4096
        )
    },
    "ECC_NIST_P256": {"generate": lambda: ec.generate_private_key(ec.SECP256R1())},
    "ECC_NIST_P384": {"generate": lambda: ec.generate_private_key(ec.SECP384R1())},
    "ECC_NIST_P521": {"generate": lambda: ec.generate_private_key(ec.SECP521R1())},
    "ECC_SECG_P256K1": {"generate": lambda: ec.generate_private_key(ec.SECP256K1())},
}


def generate_key_id():
    return str(uuid.uuid4())


def generate_data_key(number_of_bytes):
    """Generate a data key."""
    return os.urandom(number_of_bytes)


def generate_master_key(key_spec):
    """Generate a master key."""
    print(key_spec)
    return key_specs[key_spec]["generate"]()


def serialize_ciphertext_blob(ciphertext):
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


def deserialize_ciphertext_blob(ciphertext_blob):
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


def encrypt(master_keys, key_id, plaintext, encryption_context, encryption_algorithm):
    """Encrypt data using a master key material.

    NOTE: This is not necessarily what KMS does, but it retains the same properties.

    NOTE: This function is NOT compatible with KMS APIs.
    :param dict master_keys: Mapping of a KmsBackend's known master keys
    :param str key_id: Key ID of moto master key
    :param bytes plaintext: Plaintext data to encrypt
    :param dict[str, str] encryption_context: KMS-style encryption context
    :param str encryption_algorithm: Specifies the encryption algorithm that will be used to encrypt the plaintext.
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

    if encryption_algorithm == "SYMMETRIC_DEFAULT":
        iv = os.urandom(IV_LEN)
        aad = _serialize_encryption_context(encryption_context=encryption_context)

        encryptor = Cipher(
            algorithms.AES(key.key_material), modes.GCM(iv), backend=default_backend()
        ).encryptor()
        encryptor.authenticate_additional_data(aad)
        ciphertext = encryptor.update(plaintext) + encryptor.finalize()
        return Ciphertext(
            key_id=key_id, iv=iv, ciphertext=ciphertext, tag=encryptor.tag
        )

    else:
        return key.key_material.public_key().encrypt(
            plaintext, encryption_algorithms[encryption_algorithm]["padding"]
        )


def decrypt(master_keys, ciphertext, encryption_context, encryption_algorithm, key_id):
    """Decrypt a ciphertext blob using a master key material.

    NOTE: This is not necessarily what KMS does, but it retains the same properties.

    NOTE: This function is NOT compatible with KMS APIs.

    :param dict master_keys: Mapping of a KmsBackend's known master keys
    :param Union[Ciphertext,bytes] ciphertext: moto-structured ciphertext blob encrypted under a moto master key in master_keys
    :param dict[str, str] encryption_context: KMS-style encryption context
    :param str encryption_algorithm: Specifies the encryption algorithm that will be used to decrypt the ciphertext.
    :param Optional[str] key_id: Specifies the customer master key (CMK) that AWS KMS uses to decrypt the ciphertext.
    :returns: plaintext bytes and moto key ID
    :rtype: bytes and str
    """
    try:
        key = master_keys[key_id]
    except KeyError:
        raise AccessDeniedException(
            "The ciphertext refers to a customer master key that does not exist, "
            "does not exist in this region, or you are not allowed to access."
        )

    if encryption_algorithm == "SYMMETRIC_DEFAULT":
        aad = _serialize_encryption_context(encryption_context=encryption_context)
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
    else:
        plaintext = key.key_material.decrypt(
            ciphertext, encryption_algorithms[encryption_algorithm]["padding"]
        )

    return plaintext, key_id


def sign(master_keys, key_id, message, message_type, signing_algorithm):
    """Sign a message using master key material.
    NOTE: This is not necessarily what KMS does, but it retains the same properties.
    NOTE: This function is NOT compatible with KMS APIs.
    :param dict master_keys: Mapping of a KmsBackend's known master keys
    :param str key_id: Key ID of moto master key
    :param bytes message: Plaintext message to sign
    :param str message_type: Either DIGEST or RAW.
    :param signing_algorithm: The signing algorithm to use
    :returns: Moto-structured signature blob
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
    _check_for_activation(key)
    if message_type == "RAW":
        return key.key_material.sign(
            message,
            signing_algorithms[signing_algorithm]["padding"],
            signing_algorithms[signing_algorithm]["hash"],
        )
    else:
        return key.key_material.sign(
            message,
            signing_algorithms[signing_algorithm]["padding"],
            signing_algorithms[signing_algorithm]["hash"],
            utils.Prehashed(signing_algorithms[signing_algorithm]["hash"]),
        )


def verify(master_keys, key_id, message, message_type, signature, signing_algorithm):
    """Verify a signature using master key material.

    NOTE: This is not necessarily what KMS does, but it retains the same properties.

    NOTE: This function is NOT compatible with KMS APIs.
    :param dict master_keys: Mapping of a KmsBackend's known master keys
    :param str key_id: Key ID of moto master key
    :param bytes message: The message which was signed
    :param str message_type: Either 'RAW' or 'DIGEST'
    :param bytes signature: The signature that the `sign` operation generated
    :param str signing_algorithm: The signing algorithm which was used to generate the signature.
    :returns: True if the signature is valid, False otherwise.
    :rtype: bool
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
    _check_for_activation(key)
    try:
        if message_type == "RAW":
            key.key_material.public_key().verify(
                signature,
                message,
                signing_algorithms[signing_algorithm]["padding"],
                signing_algorithms[signing_algorithm]["hash"],
            )
        else:
            key.key_material.public_key().verify(
                signature,
                message,
                signing_algorithms[signing_algorithm]["padding"],
                signing_algorithms[signing_algorithm]["hash"],
                utils.Prehashed(signing_algorithms[signing_algorithm]["hash"]),
            )
        return True
    except InvalidSignature:
        return False


def _check_for_activation(key):
    """Throw a DisabledException if the key is disabled."""
    if not key.enabled:
        raise JsonRESTError(
            "DisabledException",
            "The request was rejected because the specified key is disabled.",
        )
