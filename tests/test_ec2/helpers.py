from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519, rsa
from pytest import ExceptionInfo


def check_private_key(private_key_material, key_type):
    if isinstance(private_key_material, str):
        private_key_material = private_key_material.encode()

    if key_type == "rsa":
        private_key = serialization.load_pem_private_key(
            data=private_key_material,
            backend=default_backend(),
            password=None,
        )
        assert isinstance(private_key, rsa.RSAPrivateKey)
    elif key_type == "ed25519":
        private_key = serialization.load_ssh_private_key(
            data=private_key_material,
            password=None,
        )
        assert isinstance(private_key, ed25519.Ed25519PrivateKey)
    else:
        raise AssertionError("Bad private key")


def assert_dryrun_error(ex: ExceptionInfo):
    error = ex.value.response["Error"]
    assert error["Code"] == "DryRunOperation"
    assert error["Message"] == "Request would have succeeded, but DryRun flag is set."
    response_metadata = ex.value.response["ResponseMetadata"]
    assert response_metadata["HTTPStatusCode"] == 412
