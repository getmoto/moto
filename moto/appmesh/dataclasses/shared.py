from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Dict, Literal
from uuid import uuid4


Status = Dict[Literal["status"], str]


@dataclass
class Metadata:
    arn: str
    mesh_owner: str
    resource_owner: str
    created_at: datetime = datetime.now()
    last_updated_at: datetime = datetime.now()
    uid: str = uuid4().hex
    version: int = 1

    def update_timestamp(self) -> None:
        self.last_updated_at = datetime.now()


@dataclass
class TimeValue:
    unit: str
    value: int
    to_dict = asdict


class MissingField:
    def to_dict(self) -> None:
        return
