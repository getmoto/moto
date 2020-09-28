def _matcher(pattern, str):
    for word in pattern.split(" "):
        if word not in str:
            return False
    return True


def name(secret, names):
    for n in names:
        if _matcher(n, secret.name):
            return True
    return False


def description(secret, descriptions):
    for d in descriptions:
        if _matcher(d, secret.description):
            return True
    return False


def tag_key(secret, tag_keys):
    for k in tag_keys:
        for tag in secret.tags:
            if _matcher(k, tag["Key"]):
                return True
    return False


def tag_value(secret, tag_values):
    for v in tag_values:
        for tag in secret.tags:
            if _matcher(v, tag["Value"]):
                return True
    return False


def all(secret, values):
    return (
        name(secret, values)
        or description(secret, values)
        or tag_key(secret, values)
        or tag_value(secret, values)
    )
