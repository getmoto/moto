import random
import string


def create_id():
    size = 10
    chars = list(range(10)) + list(string.ascii_lowercase)
    return "".join(str(random.choice(chars)) for x in range(size))


def to_path(prop):
    return "/" + prop
