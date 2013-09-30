import datetime
from moto.core import BaseBackend
from moto.core.utils import iso_8601_datetime


class Token(object):
    def __init__(self, duration):
        now = datetime.datetime.now()
        self.expiration = now + datetime.timedelta(seconds=duration)

    @property
    def expiration_ISO8601(self):
        return iso_8601_datetime(self.expiration)


class AssumedRole(object):
    def __init__(self, role_session_name, role_arn, policy, duration, external_id):
        self.session_name = role_session_name
        self.arn = role_arn
        self.policy = policy
        now = datetime.datetime.now()
        self.expiration = now + datetime.timedelta(seconds=duration)
        self.external_id = external_id

    @property
    def expiration_ISO8601(self):
        return iso_8601_datetime(self.expiration)


class STSBackend(BaseBackend):
    def get_session_token(self, duration):
        token = Token(duration=duration)
        return token

    def assume_role(self, **kwargs):
        role = AssumedRole(**kwargs)
        return role

sts_backend = STSBackend()
