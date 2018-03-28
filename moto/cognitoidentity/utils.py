import collections
import six
from moto.core.utils import get_random_hex


def get_random_identity_id(region):
    return "{0}:{0}".format(region, get_random_hex(length=19))


def remove_capitalization_of_dict_keys(obj):
    if isinstance(obj, collections.Mapping):
        result = obj.__class__()
        for key, value in obj.items():
            normalized_key = key[:1].lower() + key[1:]
            result[normalized_key] = remove_capitalization_of_dict_keys(value)
        return result
    elif isinstance(obj, collections.Iterable) and not isinstance(obj, six.string_types):
        result = obj.__class__()
        for item in obj:
            result += (remove_capitalization_of_dict_keys(item),)
        return result
    else:
        return obj
