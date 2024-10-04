import threading
from typing import Any, Callable

from moto.moto_api._internal import mock_random

IdSource = Callable[[str, str, str, str, str], str | None]


class MotoIdManager:
    """class to manage custom ids. Do not create instance and instead
    use the `id_manager` instance created below."""

    _custom_ids: dict[str, str]
    _id_sources: list[IdSource]

    _lock: threading.RLock

    def __init__(self) -> None:
        self._custom_ids = {}
        self._lock = threading.RLock()
        self._id_sources = []

        self.add_id_source(self.get_custom_id)

    def get_custom_id(
        self, account_id: str, region: str, service: str, resource: str, name: str
    ) -> str | None:
        # retrieves a custom_id for a resource. Returns None
        return self._custom_ids.get(
            ".".join([account_id, region, service, resource, name])
        )

    def set_custom_id(
        self,
        account_id: str,
        region: str,
        service: str,
        resource: str,
        name: str,
        custom_id: str,
    ) -> None:
        # sets a custom_id for a resource
        with self._lock:
            self._custom_ids[
                ".".join([account_id, region, service, resource, name])
            ] = custom_id

    def unset_custom_id(
        self, account_id: str, region: str, service: str, resource: str, name: str
    ) -> None:
        # removes a set custom_id for a resource
        with self._lock:
            self._custom_ids.pop(
                ".".join([account_id, region, service, resource, name]), None
            )

    def add_id_source(self, id_source: IdSource) -> None:
        self._id_sources.append(id_source)

    def find_id_from_sources(
        self, account_id: str, region: str, service: str, resource: str, name: str
    ) -> str | None:
        for id_source in self._id_sources:
            if found_id := id_source(account_id, region, service, resource, name):
                return found_id
        return None


id_manager = MotoIdManager()


def moto_id(fn: Callable[..., str]) -> Callable[..., str]:
    # Decorator for helping in creation of static ids within Moto.
    def _wrapper(
        account_id: str,
        region: str,
        service: str,
        resource: str,
        name: str,
        **kwargs: dict[str, Any],
    ) -> str:
        if found_id := id_manager.find_id_from_sources(
            account_id, region, service, resource, name
        ):
            return found_id
        return fn(account_id, region, service, resource, name, **kwargs)

    return _wrapper


@moto_id
def generate_str_id(  # type: ignore
    account_id: str,
    region: str,
    service: str,
    resource: str,
    name: str,
    length: int = 20,
    include_digits: bool = True,
    lower_case: bool = False,
) -> str:
    return mock_random.get_random_string(length, include_digits, lower_case)
