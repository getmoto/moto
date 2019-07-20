import six

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


def rsa_check_private_key(private_key_material):
    assert isinstance(private_key_material, six.string_types)

    private_key = serialization.load_pem_private_key(
        data=private_key_material.encode('ascii'),
        backend=default_backend(),
        password=None)
    assert isinstance(private_key, rsa.RSAPrivateKey)
