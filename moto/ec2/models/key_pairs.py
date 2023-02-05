from typing import Any, Dict, List

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
    random_key_pair_id,
)


class KeyPair(BaseModel):
    def __init__(self, name: str, fingerprint: str, material: str):
        self.id = random_key_pair_id()
        self.name = name
        self.fingerprint = fingerprint
        self.material = material

    def get_filter_value(self, filter_name: str) -> str:
        if filter_name == "key-name":
            return self.name
        elif filter_name == "fingerprint":
            return self.fingerprint
        else:
            raise FilterNotImplementedError(filter_name, "DescribeKeyPairs")


class KeyPairBackend:
    def __init__(self) -> None:
        self.keypairs: Dict[str, KeyPair] = {}

    def create_key_pair(self, name: str) -> KeyPair:
        if name in self.keypairs:
            raise InvalidKeyPairDuplicateError(name)
        keypair = KeyPair(name, **random_key_pair())
        self.keypairs[name] = keypair
        return keypair

    def delete_key_pair(self, name: str) -> None:
        self.keypairs.pop(name, None)

    def describe_key_pairs(
        self, key_names: List[str], filters: Any = None
    ) -> List[KeyPair]:
        if any(key_names):
            results = [
                keypair
                for keypair in self.keypairs.values()
                if keypair.name in key_names
            ]
            if len(key_names) > len(results):
                unknown_keys = set(key_names) - set(results)  # type: ignore
                raise InvalidKeyPairNameError(unknown_keys)
        else:
            results = list(self.keypairs.values())

        if filters:
            return generic_filter(filters, results)
        else:
            return results

    def import_key_pair(self, key_name: str, public_key_material: str) -> KeyPair:
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
