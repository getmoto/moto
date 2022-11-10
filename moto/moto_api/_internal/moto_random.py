from random import Random
import string
from uuid import UUID


HEX_CHARS = list(range(10)) + ["a", "b", "c", "d", "e", "f"]


class MotoRandom(Random):
    """
    Class used for all sources of random-ness in Moto.
    Used as a singleton, which is exposed in `moto/moto_api/_internal`.
    This Singleton can be seeded to make identifiers deterministic.
    """

    def uuid1(self) -> UUID:
        return UUID(int=self.getrandbits(128), version=1)

    def uuid4(self) -> UUID:
        return UUID(int=self.getrandbits(128), version=4)

    def get_random_hex(self, length: int = 8) -> str:
        return "".join(str(self.choice(HEX_CHARS)) for _ in range(length))

    def get_random_string(
        self, length: int = 20, include_digits: bool = True, lower_case: bool = False
    ) -> str:
        pool = string.ascii_letters
        if include_digits:
            pool += string.digits
        random_str = "".join([self.choice(pool) for i in range(length)])
        return random_str.lower() if lower_case else random_str
