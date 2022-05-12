from base64 import b64decode
import datetime
import xmltodict
from moto.core import BaseBackend, BaseModel
from moto.core.utils import iso_8601_datetime_with_milliseconds
from moto.core import get_account_id
from moto.sts.utils import (
    random_access_key_id,
    random_secret_access_key,
    random_session_token,
    random_assumed_role_id,
    DEFAULT_STS_SESSION_DURATION,
)


class Token(BaseModel):
    def __init__(self, duration, name=None):
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
        return (
            "arn:aws:sts::{account_id}:assumed-role/{role_name}/{session_name}".format(
                account_id=get_account_id(),
                role_name=self.role_arn.split("/")[-1],
                session_name=self.session_name,
            )
        )


class STSBackend(BaseBackend):
    def __init__(self):
        self.assumed_roles = []

    @staticmethod
    def default_vpc_endpoint_service(service_region, zones):
        """Default VPC endpoint service."""
        return BaseBackend.default_vpc_endpoint_service_factory(
            service_region, zones, "sts"
        )

    def get_session_token(self, duration):
        token = Token(duration=duration)
        return token

    def get_federation_token(self, name, duration):
        token = Token(duration=duration, name=name)
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

        namespaces = {
            "urn:oasis:names:tc:SAML:2.0:protocol": "samlp",
            "urn:oasis:names:tc:SAML:2.0:assertion": "saml",
        }
        saml_assertion = xmltodict.parse(
            saml_assertion_decoded.decode("utf-8"),
            force_cdata=True,
            process_namespaces=True,
            namespaces=namespaces,
            namespace_separator="|",
        )

        saml_assertion_attributes = saml_assertion["samlp|Response"]["saml|Assertion"][
            "saml|AttributeStatement"
        ]["saml|Attribute"]
        for attribute in saml_assertion_attributes:
            if (
                attribute["@Name"]
                == "https://aws.amazon.com/SAML/Attributes/RoleSessionName"
            ):
                kwargs["role_session_name"] = attribute["saml|AttributeValue"]["#text"]
            if (
                attribute["@Name"]
                == "https://aws.amazon.com/SAML/Attributes/SessionDuration"
            ):
                kwargs["duration"] = int(attribute["saml|AttributeValue"]["#text"])

        if "duration" not in kwargs:
            kwargs["duration"] = DEFAULT_STS_SESSION_DURATION

        kwargs["external_id"] = None
        kwargs["policy"] = None
        role = AssumedRole(**kwargs)
        self.assumed_roles.append(role)
        return role

    def get_caller_identity(self):
        # Logic resides in responses.py
        # Fake method here to make implementation coverage script aware that this method is implemented
        pass


sts_backend = STSBackend()
