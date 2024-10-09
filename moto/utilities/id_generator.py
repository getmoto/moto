import abc
import threading
from typing import Any, Callable, Dict, List, Union

from moto.moto_api._internal import mock_random


class ResourceIdentifier(abc.ABC):
    """
    Base class for resource identifiers. When implementing a new resource, it is important to set
    the service and resource as they will be used to create the unique identifier for that resource.

    It is recommended to implement the `generate` method using functions decorated with `@moto_id`.
    This will ensure that your resource can be assigned a custom id.
    """

    service: str
    resource: str

    def __init__(self, account_id: str, region: str, name: str):
        self.account_id = account_id
        self.region = region
        self.name = name or ""

    @abc.abstractmethod
    def generate(self) -> str: ...

    @property
    def unique_identifier(self) -> str:
        return ".".join(
            [self.account_id, self.region, self.service, self.resource, self.name]
        )


class MotoIdManager:
    """class to manage custom ids. Do not create instance and instead
    use the `id_manager` instance created below."""

    _custom_ids: Dict[str, str]
    _id_sources: List[Callable[[ResourceIdentifier], Union[str, None]]]

    _lock: threading.RLock

    def __init__(self) -> None:
        self._custom_ids = {}
        self._lock = threading.RLock()
        self._id_sources = []

        self.add_id_source(self.get_custom_id)

    def get_custom_id(
        self, resource_identifier: ResourceIdentifier
    ) -> Union[str, None]:
        # retrieves a custom_id for a resource. Returns None
        return self._custom_ids.get(resource_identifier.unique_identifier)

    def set_custom_id(
        self, resource_identifier: ResourceIdentifier, custom_id: str
    ) -> None:
        # Do not set a custom_id for a resource no value was found for the name
        if not resource_identifier.name:
            return
        with self._lock:
            self._custom_ids[resource_identifier.unique_identifier] = custom_id

    def unset_custom_id(self, resource_identifier: ResourceIdentifier) -> None:
        # removes a set custom_id for a resource
        with self._lock:
            self._custom_ids.pop(resource_identifier.unique_identifier, None)

    def add_id_source(
        self, id_source: Callable[[ResourceIdentifier], Union[str, None]]
    ) -> None:
        self._id_sources.append(id_source)

    def find_id_from_sources(
        self, resource_identifier: ResourceIdentifier
    ) -> Union[str, None]:
        for id_source in self._id_sources:
            if found_id := id_source(resource_identifier):
                return found_id
        return None


moto_id_manager = MotoIdManager()


def moto_id(fn: Callable[..., str]) -> Callable[..., str]:
    # Decorator for helping in creation of static ids within Moto.
    def _wrapper(
        resource_identifier: ResourceIdentifier, **kwargs: Dict[str, Any]
    ) -> str:
        if found_id := moto_id_manager.find_id_from_sources(resource_identifier):
            return found_id
        return fn(resource_identifier, **kwargs)

    return _wrapper


@moto_id
def generate_str_id(  # type: ignore
    resource_identifier: ResourceIdentifier,
    length: int = 20,
    include_digits: bool = True,
    lower_case: bool = False,
) -> str:
    return mock_random.get_random_string(length, include_digits, lower_case)
