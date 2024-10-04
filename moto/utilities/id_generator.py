import threading
from typing import Callable

from moto.moto_api._internal import mock_random

IdSource = Callable[[str, str, str, str, str], str | None]


class MotoIdManager:
    """class to manage custom ids. Do not create instance and instead
    use the `id_manager` instance created below."""

    _custom_ids: dict[str, str]
    _id_sources: [IdSource]

    _lock: threading.RLock

    def __init__(self):
        self._custom_ids = {}
        self._lock = threading.RLock()
        self._id_sources = []

        self.add_id_source(self.get_custom_id)

    def get_custom_id(self, account_id, region, service, resource, name) -> str | None:
        # retrieves a custom_id for a resource. Returns None
        return self._custom_ids.get(
            ".".join([account_id, region, service, resource, name])
        )

    def set_custom_id(self, account_id, region, service, resource, name, custom_id):
        # sets a custom_id for a resource
        with self._lock:
            self._custom_ids[
                ".".join([account_id, region, service, resource, name])
            ] = custom_id

    def unset_custom_id(self, account_id, region, service, resource, name):
        # removes a set custom_id for a resource
        with self._lock:
            self._custom_ids.pop(
                ".".join([account_id, region, service, resource, name]), None
            )

    def add_id_source(self, id_source: IdSource):
        self._id_sources.append(id_source)

    def find_id_from_sources(
        self, account_id: str, region: str, service: str, resource: str, name: str
    ) -> str | None:
        for id_source in self._id_sources:
            if found_id := id_source(account_id, region, service, resource, name):
                return found_id


id_manager = MotoIdManager()


def moto_id(fn):
    # Decorator for helping in creation of static ids within Moto.
    def _wrapper(account_id, region, service, resource, name, **kwargs):
        if found_id := id_manager.find_id_from_sources(
            account_id, region, service, resource, name
        ):
            return found_id
        return fn(account_id, region, service, resource, name, **kwargs)

    return _wrapper


@moto_id
def generate_uid(account_id, region, service, resource, name, length=32):
    return mock_random.get_random_hex(length)


@moto_id
def generate_short_uid(account_id, region, service, resource, name):
    return mock_random.get_random_hex(8)


@moto_id
def generate_str_id(
    account_id,
    region,
    service,
    resource,
    name,
    length: int = 20,
    include_digits: bool = True,
    lower_case: bool = False,
):
    return mock_random.get_random_string(length, include_digits, lower_case)
