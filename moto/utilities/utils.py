import random
import string


def random_string(length=None):
    n = length or 20
    random_str = "".join(
        [random.choice(string.ascii_letters + string.digits) for i in range(n)]
    )
    return random_str
