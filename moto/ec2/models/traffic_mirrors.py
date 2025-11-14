from typing import Any, Optional

from moto.core.utils import unix_time
from ..utils import generic_filter, random_traffic_mirror_id
from .core import TaggedEC2Resource


class TrafficMirrorFilter(TaggedEC2Resource):
    def __init__(
        self,
        description: str,
        tag_specifications: list[str, Any],
        dry_run: bool,
        client_token: str
    ):
        self.id = random_traffic_mirror_id()
        self.description = description
        self.tag_specifications = tag_specifications
        self.dry_run = dry_run
        self.client_token = client_token



class TrafficMirrorsBackend:
    def __init__(self) -> None:
        self.traffic_mirror_filters: dict[str, TrafficMirrorFilter] = {}
        

    def create_traffic_mirror_filter():
        pass


    def create_traffic_mirror_target():
        pass


    def describe_traffic_mirror_filter():
        pass

    def describe_traffic_mirror_target():
        pass