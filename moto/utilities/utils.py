import random
import string
from six.moves.urllib.parse import urlparse


def random_string(length=None):
    n = length or 20
    random_str = "".join(
        [random.choice(string.ascii_letters + string.digits) for i in range(n)]
    )
    return random_str


def uri_validator(x):
    try:
        result = urlparse(x)
        return all([result.scheme, result.netloc, result.path])
    except:
        return False
