from __future__ import unicode_literals
import datetime
from moto.core import BaseBackend, BaseModel
from moto.core.utils import iso_8601_datetime_with_milliseconds


class Token(BaseModel):

    def __init__(self, duration, name=None, policy=None):
        now = datetime.datetime.utcnow()
        self.expiration = now + datetime.timedelta(seconds=duration)
        self.name = name
        self.policy = None

    @property
    def expiration_ISO8601(self):
        return iso_8601_datetime_with_milliseconds(self.expiration)


class AssumedRole(BaseModel):

    def __init__(self, role_session_name, role_arn, policy, duration, external_id):
        self.session_name = role_session_name
        self.arn = role_arn
        self.policy = policy
        now = datetime.datetime.utcnow()
        self.expiration = now + datetime.timedelta(seconds=duration)
        self.external_id = external_id

    @property
    def expiration_ISO8601(self):
        return iso_8601_datetime_with_milliseconds(self.expiration)


class STSBackend(BaseBackend):

    def get_session_token(self, duration):
        token = Token(duration=duration)
        return token

    def get_federation_token(self, name, duration, policy):
        token = Token(duration=duration, name=name, policy=policy)
        return token

    def assume_role(self, **kwargs):
        role = AssumedRole(**kwargs)
        return role


sts_backend = STSBackend()
