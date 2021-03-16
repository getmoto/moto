from __future__ import unicode_literals
from .responses import MediaConnectResponse

url_bases = [
    "https?://mediaconnect.(.+).amazonaws.com",
]


response = MediaConnectResponse()


url_paths = {
    "{0}/v1/flows": response.dispatch,
    "{0}/v1/flows/(?P<flowarn>[^/.]+)": response.dispatch,
    "{0}/v1/flows/start/(?P<flowarn>[^/.]+)": response.dispatch,
    "{0}/v1/flows/stop/(?P<flowarn>[^/.]+)": response.dispatch,
    "{0}/tags/(?P<resourcearn>[^/.]+)": response.dispatch,
}
