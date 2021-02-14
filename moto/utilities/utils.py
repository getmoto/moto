import json
import random
import string


def random_string(length=None):
    n = length or 20
    random_str = "".join(
        [random.choice(string.ascii_letters + string.digits) for i in range(n)]
    )
    return random_str


def load_resource(filename):
    """
    Open a file, and return the contents as JSON.
    Usage:
    from pkg_resources import resource_filename
    load_resource(resource_filename(__name__, "resources/file.json"))
    """
    with open(filename, "r") as f:
        return json.load(f)
