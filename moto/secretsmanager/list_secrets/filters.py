def name(secret, names):
    return _matcher(names, [secret.name])


def description(secret, descriptions):
    return _matcher(descriptions, [secret.description])


def tag_key(secret, tag_keys):
    return _matcher(tag_keys, [tag["Key"] for tag in secret.tags])


def tag_value(secret, tag_values):
    return _matcher(tag_values, [tag["Value"] for tag in secret.tags])


def all(secret, values):
    attributes = (
        [secret.name, secret.description]
        + [tag["Key"] for tag in secret.tags]
        + [tag["Value"] for tag in secret.tags]
    )

    return _matcher(values, attributes)


def _matcher(patterns, strings):
    for pattern in [p for p in patterns if p.startswith("!")]:
        for string in strings:
            if _match_pattern(pattern[1:], string):
                return False

    for pattern in [p for p in patterns if not p.startswith("!")]:
        for string in strings:
            if _match_pattern(pattern, string):
                return True
    return False


def _match_pattern(pattern, str):
    for word in pattern.split(" "):
        if word not in str:
            return False
    return True
