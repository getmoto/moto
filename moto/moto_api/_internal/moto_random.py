from random import Random
import string
import uuid


HEX_CHARS = list(range(10)) + ["a", "b", "c", "d", "e", "f"]


class MotoRandom(Random):
    def __init__(self):
        self._rnd = Random()

    def __getattribute__(self, name):
        if name in ["_rnd", "uuid1", "uuid4", "get_random_hex", "get_random_string"]:
            return object.__getattribute__(self, name)
        return object.__getattribute__(self._rnd, name)

    def uuid1(self):
        return uuid.UUID(int=self._rnd.getrandbits(128), version=1)

    def uuid4(self):
        return uuid.UUID(int=self._rnd.getrandbits(128), version=4)

    def get_random_hex(self, length=8):
        return "".join(str(self._rnd.choice(HEX_CHARS)) for _ in range(length))

    def get_random_string(self, length=20, include_digits=True, lower_case=False):
        pool = string.ascii_letters
        if include_digits:
            pool += string.digits
        random_str = "".join([self._rnd.choice(pool) for i in range(length)])
        return random_str.lower() if lower_case else random_str
