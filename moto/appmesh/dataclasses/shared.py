from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Literal
from uuid import uuid4

from moto.appmesh.utils.common import clean_dict
from moto.core.utils import utcnow

Status = dict[Literal["status"], str]


@dataclass
class Metadata:
    arn: str
    mesh_owner: str
    resource_owner: str
    # Factories, so that each resource gets its own creation time and uid
    # instead of the values computed once when this module was imported.
    created_at: datetime = field(default_factory=utcnow)
    last_updated_at: datetime = field(default_factory=utcnow)
    uid: str = field(default_factory=lambda: uuid4().hex)
    version: int = 1

    def update_timestamp(self) -> None:
        self.last_updated_at = utcnow()


@dataclass
class Duration:
    unit: str
    value: int
    to_dict = asdict


class MissingField:
    def to_dict(self) -> None:
        return


@dataclass
class Timeout:
    idle: Duration | None = field(default=None)
    per_request: Duration | None = field(default=None)

    def to_dict(self) -> dict[str, Any]:  # type: ignore[misc]
        return clean_dict(
            {
                "idle": (self.idle or MissingField()).to_dict(),
                "perRequest": (self.per_request or MissingField()).to_dict(),
            }
        )
