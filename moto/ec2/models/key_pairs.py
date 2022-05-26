from moto.core import BaseModel
from ..exceptions import (
    FilterNotImplementedError,
    InvalidKeyPairNameError,
    InvalidKeyPairDuplicateError,
    InvalidKeyPairFormatError,
)
from ..utils import (
    random_key_pair,
    rsa_public_key_fingerprint,
    rsa_public_key_parse,
    generic_filter,
)


class KeyPair(BaseModel):
    def __init__(self, name, fingerprint, material):
        self.name = name
        self.fingerprint = fingerprint
        self.material = material

    def get_filter_value(self, filter_name):
        if filter_name == "key-name":
            return self.name
        elif filter_name == "fingerprint":
            return self.fingerprint
        else:
            raise FilterNotImplementedError(filter_name, "DescribeKeyPairs")


class KeyPairBackend(object):
    def __init__(self):
        self.keypairs = {}
        super().__init__()

    def create_key_pair(self, name):
        if name in self.keypairs:
            raise InvalidKeyPairDuplicateError(name)
        keypair = KeyPair(name, **random_key_pair())
        self.keypairs[name] = keypair
        return keypair

    def delete_key_pair(self, name):
        if name in self.keypairs:
            self.keypairs.pop(name)
        return True

    def describe_key_pairs(self, key_names=None, filters=None):
        results = []
        if any(key_names):
            results = [
                keypair
                for keypair in self.keypairs.values()
                if keypair.name in key_names
            ]
            if len(key_names) > len(results):
                unknown_keys = set(key_names) - set(results)
                raise InvalidKeyPairNameError(unknown_keys)
        else:
            results = self.keypairs.values()

        if filters:
            return generic_filter(filters, results)
        else:
            return results

    def import_key_pair(self, key_name, public_key_material):
        if key_name in self.keypairs:
            raise InvalidKeyPairDuplicateError(key_name)

        try:
            rsa_public_key = rsa_public_key_parse(public_key_material)
        except ValueError:
            raise InvalidKeyPairFormatError()

        fingerprint = rsa_public_key_fingerprint(rsa_public_key)
        keypair = KeyPair(
            key_name, material=public_key_material, fingerprint=fingerprint
        )
        self.keypairs[key_name] = keypair
        return keypair
