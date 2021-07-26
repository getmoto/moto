import json
import random
import string


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


def load_resource(filename, as_json=True):
    """
    Open a file, and return the contents as JSON.
    Usage:
    from pkg_resources import resource_filename
    load_resource(resource_filename(__name__, "resources/file.json"))
    """
    with open(filename, "r", encoding="utf-8") as f:
        return json.load(f) if as_json else f.read()


def merge_multiple_dicts(*args):
    result = {}
    for d in args:
        result.update(d)
    return result
