from .responses import (
    CognitoIdpJsonWebKeyResponse,
    CognitoIdpOpenIdConfigurationResponse,
    CognitoIdpResponse,
)

url_bases = [r"https?://cognito-idp\.(.+)\.amazonaws.com"]

url_paths = {
    "{0}/$": CognitoIdpResponse.dispatch,
    "{0}/(?P<user_pool_id>[^/]+)/.well-known/jwks.json$": CognitoIdpJsonWebKeyResponse.serve_json_web_key,
    "{0}/(?P<user_pool_id>[^/]+)/.well-known/openid-configuration$": CognitoIdpOpenIdConfigurationResponse.serve_openid_configuration,
}
