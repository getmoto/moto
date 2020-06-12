from __future__ import unicode_literals
from base64 import b64decode
import datetime
import xmltodict
from moto.core import BaseBackend, BaseModel
from moto.core.utils import iso_8601_datetime_with_milliseconds
from moto.core import ACCOUNT_ID
from moto.sts.utils import (
    random_access_key_id,
    random_secret_access_key,
    random_session_token,
    random_assumed_role_id,
)


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
        self.role_arn = role_arn
        self.policy = policy
        now = datetime.datetime.utcnow()
        self.expiration = now + datetime.timedelta(seconds=duration)
        self.external_id = external_id
        self.access_key_id = "ASIA" + random_access_key_id()
        self.secret_access_key = random_secret_access_key()
        self.session_token = random_session_token()
        self.assumed_role_id = "AROA" + random_assumed_role_id()

    @property
    def expiration_ISO8601(self):
        return iso_8601_datetime_with_milliseconds(self.expiration)

    @property
    def user_id(self):
        return self.assumed_role_id + ":" + self.session_name

    @property
    def arn(self):
        return "arn:aws:sts::{account_id}:assumed-role/{role_name}/{session_name}".format(
            account_id=ACCOUNT_ID,
            role_name=self.role_arn.split("/")[-1],
            session_name=self.session_name,
        )


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

    def get_assumed_role_from_access_key(self, access_key_id):
        for assumed_role in self.assumed_roles:
            if assumed_role.access_key_id == access_key_id:
                return assumed_role
        return None

    def assume_role_with_web_identity(self, **kwargs):
        return self.assume_role(**kwargs)

    def assume_role_with_saml(self, **kwargs):
        del kwargs["principal_arn"]
        saml_assertion_encoded = kwargs.pop("saml_assertion")
        saml_assertion_decoded = b64decode(saml_assertion_encoded)
        saml_assertion = xmltodict.parse(saml_assertion_decoded.decode("utf-8"))
        kwargs["duration"] = int(
            saml_assertion["samlp:Response"]["Assertion"]["AttributeStatement"][
                "Attribute"
            ][2]["AttributeValue"]
        )
        kwargs["role_session_name"] = saml_assertion["samlp:Response"]["Assertion"][
            "AttributeStatement"
        ]["Attribute"][0]["AttributeValue"]
        kwargs["external_id"] = None
        kwargs["policy"] = None
        role = AssumedRole(**kwargs)
        self.assumed_roles.append(role)
        return role


sts_backend = STSBackend()
