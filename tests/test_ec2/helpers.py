from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa, ed25519


def check_private_key(private_key_material, key_type):
    assert isinstance(private_key_material, str)

    if key_type == "rsa":
        private_key = serialization.load_pem_private_key(
            data=private_key_material.encode("ascii"),
            backend=default_backend(),
            password=None,
        )
        assert isinstance(private_key, rsa.RSAPrivateKey)
    elif key_type == "ed25519":
        private_key = serialization.load_ssh_private_key(
            data=private_key_material.encode("ascii"),
            password=None,
        )
        assert isinstance(private_key, ed25519.Ed25519PrivateKey)
    else:
        raise AssertionError("Bad private key")
