import random
import string


def random_resource_id():
    size = 20
    chars = range(10) + list(string.lowercase)

    return ''.join(unicode(random.choice(chars)) for x in range(size))
