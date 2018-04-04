from __future__ import unicode_literals

import datetime
import json

import boto.cognito.identity

from moto.compat import OrderedDict
from moto.core import BaseBackend, BaseModel
from moto.core.utils import iso_8601_datetime_with_milliseconds

from .utils import get_random_identity_id


class CognitoIdentity(BaseModel):

    def __init__(self, region, identity_pool_name, **kwargs):
        self.identity_pool_name = identity_pool_name
        self.allow_unauthenticated_identities = kwargs.get('allow_unauthenticated_identities', '')
        self.supported_login_providers = kwargs.get('supported_login_providers', {})
        self.developer_provider_name = kwargs.get('developer_provider_name', '')
        self.open_id_connect_provider_arns = kwargs.get('open_id_connect_provider_arns', [])
        self.cognito_identity_providers = kwargs.get('cognito_identity_providers', [])
        self.saml_provider_arns = kwargs.get('saml_provider_arns', [])

        self.identity_pool_id = get_random_identity_id(region)
        self.creation_time = datetime.datetime.utcnow()


class CognitoIdentityBackend(BaseBackend):

    def __init__(self, region):
        super(CognitoIdentityBackend, self).__init__()
        self.region = region
        self.identity_pools = OrderedDict()

    def reset(self):
        region = self.region
        self.__dict__ = {}
        self.__init__(region)

    def create_identity_pool(self, identity_pool_name, allow_unauthenticated_identities,
        supported_login_providers, developer_provider_name, open_id_connect_provider_arns,
            cognito_identity_providers, saml_provider_arns):

        new_identity = CognitoIdentity(self.region, identity_pool_name,
            allow_unauthenticated_identities=allow_unauthenticated_identities,
            supported_login_providers=supported_login_providers,
            developer_provider_name=developer_provider_name,
            open_id_connect_provider_arns=open_id_connect_provider_arns,
            cognito_identity_providers=cognito_identity_providers,
            saml_provider_arns=saml_provider_arns)
        self.identity_pools[new_identity.identity_pool_id] = new_identity

        response = json.dumps({
            'IdentityPoolId': new_identity.identity_pool_id,
            'IdentityPoolName': new_identity.identity_pool_name,
            'AllowUnauthenticatedIdentities': new_identity.allow_unauthenticated_identities,
            'SupportedLoginProviders': new_identity.supported_login_providers,
            'DeveloperProviderName': new_identity.developer_provider_name,
            'OpenIdConnectProviderARNs': new_identity.open_id_connect_provider_arns,
            'CognitoIdentityProviders': new_identity.cognito_identity_providers,
            'SamlProviderARNs': new_identity.saml_provider_arns
        })

        return response

    def get_id(self):
        identity_id = {'IdentityId': get_random_identity_id(self.region)}
        return json.dumps(identity_id)

    def get_credentials_for_identity(self, identity_id):
        duration = 90
        now = datetime.datetime.utcnow()
        expiration = now + datetime.timedelta(seconds=duration)
        expiration_str = str(iso_8601_datetime_with_milliseconds(expiration))
        response = json.dumps(
            {
                "Credentials":
                {
                    "AccessKeyId": "TESTACCESSKEY12345",
                    "Expiration": expiration_str,
                    "SecretKey": "ABCSECRETKEY",
                    "SessionToken": "ABC12345"
                },
                "IdentityId": identity_id
            })
        return response

    def get_open_id_token_for_developer_identity(self, identity_id):
        response = json.dumps(
            {
                "IdentityId": identity_id,
                "Token": get_random_identity_id(self.region)
            })
        return response


cognitoidentity_backends = {}
for region in boto.cognito.identity.regions():
    cognitoidentity_backends[region.name] = CognitoIdentityBackend(region.name)
