import json
import hashlib
import pkgutil

from collections.abc import MutableMapping
from typing import Any, Dict


def str2bool(v):
    if v in ("yes", True, "true", "True", "TRUE", "t", "1"):
        return True
    elif v in ("no", False, "false", "False", "FALSE", "f", "0"):
        return False


def load_resource(package, resource, as_json=True):
    """
    Open a file, and return the contents as JSON.
    Usage:
    load_resource(__name__, "resources/file.json")
    """
    resource = pkgutil.get_data(package, resource)
    return json.loads(resource) if as_json else resource.decode("utf-8")


def merge_multiple_dicts(*args: Any) -> Dict[str, any]:
    result = {}
    for d in args:
        result.update(d)
    return result


def filter_resources(resources, filters, attr_pairs):
    """
    Used to filter resources. Usually in get and describe apis.
    """
    result = resources.copy()
    for resource in resources:
        for attrs in attr_pairs:
            values = filters.get(attrs[0]) or None
            if values:
                instance = getattr(resource, attrs[1])
                if (len(attrs) <= 2 and instance not in values) or (
                    len(attrs) == 3 and instance.get(attrs[2]) not in values
                ):
                    result.remove(resource)
                    break
    return result


def md5_hash(data=None):
    """
    MD5-hashing for non-security usecases.
    Required for Moto to work in FIPS-enabled systems
    """
    args = (data,) if data else ()
    try:
        return hashlib.md5(*args, usedforsecurity=False)
    except TypeError:
        # The usedforsecurity-parameter is only available as of Python 3.9
        return hashlib.md5(*args)


class LowercaseDict(MutableMapping):
    """A dictionary that lowercases all keys"""

    def __init__(self, *args, **kwargs):
        self.store = dict()
        self.update(dict(*args, **kwargs))  # use the free update to set keys

    def __getitem__(self, key):
        return self.store[self._keytransform(key)]

    def __setitem__(self, key, value):
        self.store[self._keytransform(key)] = value

    def __delitem__(self, key):
        del self.store[self._keytransform(key)]

    def __iter__(self):
        return iter(self.store)

    def __len__(self):
        return len(self.store)

    def __repr__(self):
        return str(self.store)

    def _keytransform(self, key):
        return key.lower()
