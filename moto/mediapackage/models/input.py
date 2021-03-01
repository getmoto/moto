from __future__ import unicode_literals

from collections import OrderedDict
from uuid import uuid4

from boto3 import Session

from moto.core import BaseModel


class Input(BaseModel):
    def __init__(self, *args, **kwargs):
        pass

    def to_dict(self):
        data = {}
        return data

    def _resolve_transient_states(self):
        pass