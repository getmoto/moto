from __future__ import unicode_literals

import datetime
import json
import re

from boto3 import Session

from collections import OrderedDict
from moto.core import BaseBackend, BaseModel
from moto.core.utils import iso_8601_datetime_with_milliseconds
from .exceptions import InvalidNameException, ResourceNotFoundError
from .utils import get_random_identity_id


class CognitoIdentity(BaseModel):
    def __init__(self, region, identity_pool_name, **kwargs):
        self.identity_pool_name = identity_pool_name

        if not re.fullmatch(r"[\w\s+=,.@-]+", identity_pool_name):
            raise InvalidNameException(identity_pool_name)

        self.allow_unauthenticated_identities = kwargs.get(
            "allow_unauthenticated_identities", ""
        )
        self.supported_login_providers = kwargs.get("supported_login_providers", {})
        self.developer_provider_name = kwargs.get("developer_provider_name", "")
        self.open_id_connect_provider_arns = kwargs.get(
            "open_id_connect_provider_arns", []
        )
        self.cognito_identity_providers = kwargs.get("cognito_identity_providers", [])
        self.saml_provider_arns = kwargs.get("saml_provider_arns", [])

        self.identity_pool_id = get_random_identity_id(region)
        self.creation_time = datetime.datetime.utcnow()

        self.tags = kwargs.get("tags") or {}

    def to_json(self):
        return json.dumps(
            {
                "IdentityPoolId": self.identity_pool_id,
                "IdentityPoolName": self.identity_pool_name,
                "AllowUnauthenticatedIdentities": self.allow_unauthenticated_identities,
                "SupportedLoginProviders": self.supported_login_providers,
                "DeveloperProviderName": self.developer_provider_name,
                "OpenIdConnectProviderARNs": self.open_id_connect_provider_arns,
                "CognitoIdentityProviders": self.cognito_identity_providers,
                "SamlProviderARNs": self.saml_provider_arns,
            }
        )


class CognitoIdentityBackend(BaseBackend):
    def __init__(self, region):
        super(CognitoIdentityBackend, self).__init__()
        self.region = region
        self.identity_pools = OrderedDict()

    def reset(self):
        region = self.region
        self.__dict__ = {}
        self.__init__(region)

    def describe_identity_pool(self, identity_pool_id):
        identity_pool = self.identity_pools.get(identity_pool_id, None)

        if not identity_pool:
            raise ResourceNotFoundError(identity_pool_id)

        response = json.dumps(
            {
                "AllowUnauthenticatedIdentities": identity_pool.allow_unauthenticated_identities,
                "CognitoIdentityProviders": identity_pool.cognito_identity_providers,
                "DeveloperProviderName": identity_pool.developer_provider_name,
                "IdentityPoolId": identity_pool.identity_pool_id,
                "IdentityPoolName": identity_pool.identity_pool_name,
                "IdentityPoolTags": identity_pool.tags,
                "OpenIdConnectProviderARNs": identity_pool.open_id_connect_provider_arns,
                "SamlProviderARNs": identity_pool.saml_provider_arns,
                "SupportedLoginProviders": identity_pool.supported_login_providers,
            }
        )

        return response

    def create_identity_pool(
        self,
        identity_pool_name,
        allow_unauthenticated_identities,
        supported_login_providers,
        developer_provider_name,
        open_id_connect_provider_arns,
        cognito_identity_providers,
        saml_provider_arns,
        tags=None,
    ):
        new_identity = CognitoIdentity(
            self.region,
            identity_pool_name,
            allow_unauthenticated_identities=allow_unauthenticated_identities,
            supported_login_providers=supported_login_providers,
            developer_provider_name=developer_provider_name,
            open_id_connect_provider_arns=open_id_connect_provider_arns,
            cognito_identity_providers=cognito_identity_providers,
            saml_provider_arns=saml_provider_arns,
            tags=tags,
        )
        self.identity_pools[new_identity.identity_pool_id] = new_identity

        response = new_identity.to_json()
        return response

    def update_identity_pool(
        self,
        identity_pool_id,
        identity_pool_name,
        allow_unauthenticated,
        allow_classic,
        login_providers,
        provider_name,
        provider_arns,
        identity_providers,
        saml_providers,
        tags=None,
    ):
        pool = self.identity_pools[identity_pool_id]
        pool.identity_pool_name = pool.identity_pool_name or identity_pool_name
        if allow_unauthenticated is not None:
            pool.allow_unauthenticated_identities = allow_unauthenticated
        if login_providers is not None:
            pool.supported_login_providers = login_providers
        if provider_name:
            pool.developer_provider_name = provider_name
        if provider_arns is not None:
            pool.open_id_connect_provider_arns = provider_arns
        if identity_providers is not None:
            pool.cognito_identity_providers = identity_providers
        if saml_providers is not None:
            pool.saml_provider_arns = saml_providers
        if tags:
            pool.tags = tags

        response = pool.to_json()
        return response

    def get_id(self):
        identity_id = {"IdentityId": get_random_identity_id(self.region)}
        return json.dumps(identity_id)

    def get_credentials_for_identity(self, identity_id):
        duration = 90
        now = datetime.datetime.utcnow()
        expiration = now + datetime.timedelta(seconds=duration)
        expiration_str = str(iso_8601_datetime_with_milliseconds(expiration))
        response = json.dumps(
            {
                "Credentials": {
                    "AccessKeyId": "TESTACCESSKEY12345",
                    "Expiration": expiration_str,
                    "SecretKey": "ABCSECRETKEY",
                    "SessionToken": "ABC12345",
                },
                "IdentityId": identity_id,
            }
        )
        return response

    def get_open_id_token_for_developer_identity(self, identity_id):
        response = json.dumps(
            {"IdentityId": identity_id, "Token": get_random_identity_id(self.region)}
        )
        return response

    def get_open_id_token(self, identity_id):
        response = json.dumps(
            {"IdentityId": identity_id, "Token": get_random_identity_id(self.region)}
        )
        return response


cognitoidentity_backends = {}
for region in Session().get_available_regions("cognito-identity"):
    cognitoidentity_backends[region] = CognitoIdentityBackend(region)
for region in Session().get_available_regions(
    "cognito-identity", partition_name="aws-us-gov"
):
    cognitoidentity_backends[region] = CognitoIdentityBackend(region)
for region in Session().get_available_regions(
    "cognito-identity", partition_name="aws-cn"
):
    cognitoidentity_backends[region] = CognitoIdentityBackend(region)
