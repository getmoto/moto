from .secret_filters import all, tag_key, tag_value, description, name


_filter_functions = {
    "all": all,
    "name": name,
    "description": description,
    "tag-key": tag_key,
    "tag-value": tag_value
}


def keys():
    return _filter_functions.keys()


def matches(secret, filters):
    is_match = True

    for f in filters:
        # Filter names are pre-validated in the resource layer
        filter_function = _filter_functions.get(f["Key"])
        is_match = is_match and filter_function(secret, f["Values"])

    return is_match
