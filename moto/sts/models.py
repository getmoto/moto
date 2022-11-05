from base64 import b64decode
import datetime
import re
import xmltodict
from moto.core import BaseBackend, BaseModel
from moto.core.utils import iso_8601_datetime_with_milliseconds, BackendDict
from moto.iam import iam_backends
from moto.sts.utils import (
    random_session_token,
    DEFAULT_STS_SESSION_DURATION,
    random_assumed_role_id,
)
from typing import Mapping


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
    def __init__(
        self,
        account_id,
        access_key,
        role_session_name,
        role_arn,
        policy,
        duration,
        external_id,
    ):
        self.account_id = account_id
        self.session_name = role_session_name
        self.role_arn = role_arn
        self.policy = policy
        now = datetime.datetime.utcnow()
        self.expiration = now + datetime.timedelta(seconds=duration)
        self.external_id = external_id
        self.access_key = access_key
        self.access_key_id = access_key.access_key_id
        self.secret_access_key = access_key.secret_access_key
        self.session_token = random_session_token()

    @property
    def expiration_ISO8601(self):
        return iso_8601_datetime_with_milliseconds(self.expiration)

    @property
    def user_id(self):
        iam_backend = iam_backends[self.account_id]["global"]
        try:
            role_id = iam_backend.get_role_by_arn(arn=self.role_arn).id
        except Exception:
            role_id = "AROA" + random_assumed_role_id()
        return role_id + ":" + self.session_name

    @property
    def arn(self):
        return (
            "arn:aws:sts::{account_id}:assumed-role/{role_name}/{session_name}".format(
                account_id=self.account_id,
                role_name=self.role_arn.split("/")[-1],
                session_name=self.session_name,
            )
        )


class STSBackend(BaseBackend):
    def __init__(self, region_name, account_id):
        super().__init__(region_name, account_id)
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

    def assume_role(self, role_session_name, role_arn, policy, duration, external_id):
        """
        Assume an IAM Role. Note that the role does not need to exist. The ARN can point to another account, providing an opportunity to switch accounts.
        """
        account_id, access_key = self._create_access_key(role=role_arn)
        role = AssumedRole(
            account_id,
            access_key,
            role_session_name,
            role_arn,
            policy,
            duration,
            external_id,
        )
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

        target_role = None
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
            if attribute["@Name"] == "https://aws.amazon.com/SAML/Attributes/Role":
                target_role = attribute["saml|AttributeValue"]["#text"].split(",")[0]

        if "duration" not in kwargs:
            kwargs["duration"] = DEFAULT_STS_SESSION_DURATION

        account_id, access_key = self._create_access_key(role=target_role)
        kwargs["account_id"] = account_id
        kwargs["access_key"] = access_key

        kwargs["external_id"] = None
        kwargs["policy"] = None
        role = AssumedRole(**kwargs)
        self.assumed_roles.append(role)
        return role

    def get_caller_identity(self, access_key_id):
        assumed_role = self.get_assumed_role_from_access_key(access_key_id)
        if assumed_role:
            return assumed_role.user_id, assumed_role.arn, assumed_role.account_id

        iam_backend = iam_backends[self.account_id]["global"]
        user = iam_backend.get_user_from_access_key_id(access_key_id)
        if user:
            return user.id, user.arn, user.account_id

        # Default values in case the request does not use valid credentials generated by moto
        user_id = "AKIAIOSFODNN7EXAMPLE"
        arn = f"arn:aws:sts::{self.account_id}:user/moto"
        return user_id, arn, self.account_id

    def _create_access_key(self, role):
        account_id_match = re.search(r"arn:aws:iam::([0-9]+).+", role)
        if account_id_match:
            account_id = account_id_match.group(1)
        else:
            account_id = self.account_id
        iam_backend = iam_backends[account_id]["global"]
        return account_id, iam_backend.create_temp_access_key()


sts_backends: Mapping[str, STSBackend] = BackendDict(
    STSBackend, "sts", use_boto3_regions=False, additional_regions=["global"]
)
