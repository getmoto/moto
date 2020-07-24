from .secret_filters import all, tag_key, tag_value, description, name


def matches(secret, filters):
    if len(filters) == 0:
        return True

    filter_functions = {
        "all": all,
        "name": name,
        "description": description,
        "tag-key": tag_key,
        "tag-value": tag_value
    }

    # TODO are filters combined with OR or AND?
    for f in filters:
        # TODO what's the proper AWS error message?
        filter_function = filter_functions.get(f["Key"], "Invalid filter key")
        is_match = filter_function(secret, f["Values"])
        if is_match:
            return True
    return False
