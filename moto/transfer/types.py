from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, TypedDict

from moto.core.common_models import BaseModel


class HomeDirectoryType(str, Enum):
    PATH = "PATH"
    LOGICAL = "LOGICAL"


class HomeDirectoryMappingType(str, Enum):
    FILE = "FILE"
    DIRECTORY = "DIRECTORY"


class HomeDirectoryMapping(TypedDict):
    Entry: str
    Target: str
    Type: Optional[HomeDirectoryMappingType]


class PosixProfile(TypedDict):
    Uid: int
    Gid: int
    SecondaryGids: Optional[List[int]]


class SshPublicKey(TypedDict):
    DateImported: str
    SshPublicKeyBody: str
    SshPublicKeyId: str


@dataclass
class User(BaseModel):
    HomeDirectory: Optional[str]
    HomeDirectoryType: Optional[HomeDirectoryType]
    Policy: Optional[str]
    PosixProfile: Optional[PosixProfile]
    Role: str
    UserName: str
    Arn: str = field(default="", init=False)
    HomeDirectoryMappings: List[HomeDirectoryMapping] = field(default_factory=list)
    SshPublicKeys: List[SshPublicKey] = field(default_factory=list)
    Tags: List[Dict[str, str]] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.Arn == "":
            self.Arn = f"arn:aws:transfer:{self.UserName}:{datetime.now().strftime('%Y%m%d%H%M%S')}"

    to_dict = asdict
