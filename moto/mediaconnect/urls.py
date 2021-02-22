from __future__ import unicode_literals
from .responses import MediaConnectResponse

url_bases = [
    "https?://mediaconnect.(.+).amazonaws.com",
]


response = MediaConnectResponse()


url_paths = {
    "{0}/v1/flows": response.dispatch,
}
