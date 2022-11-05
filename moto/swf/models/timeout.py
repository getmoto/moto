from moto.core import BaseModel
from moto.core.utils import unix_time


class Timeout(BaseModel):
    def __init__(self, obj, timestamp, kind):
        self.obj = obj
        self.timestamp = timestamp
        self.kind = kind

    @property
    def reached(self):
        return unix_time() >= self.timestamp
