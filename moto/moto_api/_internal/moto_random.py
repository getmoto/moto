from random import Random
import string
import uuid


HEX_CHARS = list(range(10)) + ["a", "b", "c", "d", "e", "f"]


class MotoRandom(Random):
    """
    Class used for all sources of random-ness in Moto.
    Used as a singleton, which is exposed in `moto/moto_api/_internal`.
    This Singleton can be seeded to make identifiers deterministic.
    """

    def uuid1(self):
        return uuid.UUID(int=self.getrandbits(128), version=1)

    def uuid4(self):
        return uuid.UUID(int=self.getrandbits(128), version=4)

    def get_random_hex(self, length=8):
        return "".join(str(self.choice(HEX_CHARS)) for _ in range(length))

    def get_random_string(self, length=20, include_digits=True, lower_case=False):
        pool = string.ascii_letters
        if include_digits:
            pool += string.digits
        random_str = "".join([self.choice(pool) for i in range(length)])
        return random_str.lower() if lower_case else random_str
