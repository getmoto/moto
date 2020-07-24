def name(secret, names):
    for n in names:
        if n in secret["name"]:
            return True
    return False


def description(secret, descriptions):
    for d in descriptions:
        if d in secret["description"]:
            return True
    return False


def tag_key(secret, tag_keys):
    for tag in secret["tags"]:
        if tag["Key"] in tag_keys:
            return True
    return False


def tag_value(secret, tag_values):
    for tag in secret["tags"]:
        if tag["Value"] in tag_values:
            return True
    return False


def all(secret, values):
    # TODO implement
    return True
