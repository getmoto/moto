from __future__ import unicode_literals
import datetime
from moto.core import BaseBackend, BaseModel
from moto.core.utils import iso_8601_datetime_with_milliseconds
from moto.sts.utils import random_access_key_id, random_secret_access_key, random_session_token


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
        self.access_key_id = "ASIA" + random_access_key_id()
        self.secret_access_key = random_secret_access_key()
        self.session_token = random_session_token()

    @property
    def expiration_ISO8601(self):
        return iso_8601_datetime_with_milliseconds(self.expiration)


class STSBackend(BaseBackend):

    def __init__(self):
        self.assumed_roles = []

    def get_session_token(self, duration):
        token = Token(duration=duration)
        return token

    def get_federation_token(self, name, duration, policy):
        token = Token(duration=duration, name=name, policy=policy)
        return token

    def assume_role(self, **kwargs):
        role = AssumedRole(**kwargs)
        self.assumed_roles.append(role)
        return role

    def assume_role_with_web_identity(self, **kwargs):
        return self.assume_role(**kwargs)


sts_backend = STSBackend()
