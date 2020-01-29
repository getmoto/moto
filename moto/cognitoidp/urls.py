from __future__ import unicode_literals
from .responses import CognitoIdpResponse, CognitoIdpJsonWebKeyResponse

url_bases = ["https?://cognito-idp.(.+).amazonaws.com"]

url_paths = {
    "{0}/$": CognitoIdpResponse.dispatch,
    "{0}/<user_pool_id>/.well-known/jwks.json$": CognitoIdpJsonWebKeyResponse().serve_json_web_key,
}
