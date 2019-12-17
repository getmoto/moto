import six
from moto.compat import collections_abc
from moto.core.utils import get_random_hex


def get_random_pipeline_id():
    return "df-{0}".format(get_random_hex(length=19))


def remove_capitalization_of_dict_keys(obj):
    if isinstance(obj, collections_abc.Mapping):
        result = obj.__class__()
        for key, value in obj.items():
            normalized_key = key[:1].lower() + key[1:]
            result[normalized_key] = remove_capitalization_of_dict_keys(value)
        return result
    elif isinstance(obj, collections_abc.Iterable) and not isinstance(
        obj, six.string_types
    ):
        result = obj.__class__()
        for item in obj:
            result += (remove_capitalization_of_dict_keys(item),)
        return result
    else:
        return obj
