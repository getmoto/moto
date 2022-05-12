from moto.core.responses import BaseResponse
from .models import cognitoidentity_backends
from .utils import get_random_identity_id


class CognitoIdentityResponse(BaseResponse):
    def create_identity_pool(self):
        identity_pool_name = self._get_param("IdentityPoolName")
        allow_unauthenticated_identities = self._get_param(
            "AllowUnauthenticatedIdentities"
        )
        supported_login_providers = self._get_param("SupportedLoginProviders")
        developer_provider_name = self._get_param("DeveloperProviderName")
        open_id_connect_provider_arns = self._get_param("OpenIdConnectProviderARNs")
        cognito_identity_providers = self._get_param("CognitoIdentityProviders")
        saml_provider_arns = self._get_param("SamlProviderARNs")
        pool_tags = self._get_param("IdentityPoolTags")

        return cognitoidentity_backends[self.region].create_identity_pool(
            identity_pool_name=identity_pool_name,
            allow_unauthenticated_identities=allow_unauthenticated_identities,
            supported_login_providers=supported_login_providers,
            developer_provider_name=developer_provider_name,
            open_id_connect_provider_arns=open_id_connect_provider_arns,
            cognito_identity_providers=cognito_identity_providers,
            saml_provider_arns=saml_provider_arns,
            tags=pool_tags,
        )

    def update_identity_pool(self):
        pool_id = self._get_param("IdentityPoolId")
        pool_name = self._get_param("IdentityPoolName")
        allow_unauthenticated = self._get_bool_param("AllowUnauthenticatedIdentities")
        login_providers = self._get_param("SupportedLoginProviders")
        provider_name = self._get_param("DeveloperProviderName")
        provider_arns = self._get_param("OpenIdConnectProviderARNs")
        identity_providers = self._get_param("CognitoIdentityProviders")
        saml_providers = self._get_param("SamlProviderARNs")
        pool_tags = self._get_param("IdentityPoolTags")

        return cognitoidentity_backends[self.region].update_identity_pool(
            identity_pool_id=pool_id,
            identity_pool_name=pool_name,
            allow_unauthenticated=allow_unauthenticated,
            login_providers=login_providers,
            provider_name=provider_name,
            provider_arns=provider_arns,
            identity_providers=identity_providers,
            saml_providers=saml_providers,
            tags=pool_tags,
        )

    def get_id(self):
        return cognitoidentity_backends[self.region].get_id(
            identity_pool_id=self._get_param("IdentityPoolId")
        )

    def describe_identity_pool(self):
        return cognitoidentity_backends[self.region].describe_identity_pool(
            self._get_param("IdentityPoolId")
        )

    def get_credentials_for_identity(self):
        return cognitoidentity_backends[self.region].get_credentials_for_identity(
            self._get_param("IdentityId")
        )

    def get_open_id_token_for_developer_identity(self):
        return cognitoidentity_backends[
            self.region
        ].get_open_id_token_for_developer_identity(
            self._get_param("IdentityId") or get_random_identity_id(self.region)
        )

    def get_open_id_token(self):
        return cognitoidentity_backends[self.region].get_open_id_token(
            self._get_param("IdentityId") or get_random_identity_id(self.region)
        )

    def list_identities(self):
        return cognitoidentity_backends[self.region].list_identities(
            self._get_param("IdentityPoolId") or get_random_identity_id(self.region)
        )
