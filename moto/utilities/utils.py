import json
import random
import string
import pkgutil


from collections.abc import MutableMapping


def str2bool(v):
    if v in ("yes", True, "true", "True", "TRUE", "t", "1"):
        return True
    elif v in ("no", False, "false", "False", "FALSE", "f", "0"):
        return False


def random_string(length=None):
    n = length or 20
    random_str = "".join(
        [random.choice(string.ascii_letters + string.digits) for i in range(n)]
    )
    return random_str


def load_resource(package, resource, as_json=True):
    """
    Open a file, and return the contents as JSON.
    Usage:
    load_resource(__name__, "resources/file.json")
    """
    resource = pkgutil.get_data(package, resource)
    return json.loads(resource) if as_json else resource.decode("utf-8")


def merge_multiple_dicts(*args):
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
