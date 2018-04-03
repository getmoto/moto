from __future__ import unicode_literals
from .responses import CognitoIdentityResponse

url_bases = [
    "https?://cognito-identity.(.+).amazonaws.com",
]

url_paths = {
    '{0}/$': CognitoIdentityResponse.dispatch,
}
