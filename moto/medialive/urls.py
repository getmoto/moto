from __future__ import unicode_literals
from .responses import MediaLiveResponse

url_bases = [
    "https?://medialive.(.+).amazonaws.com",
]


response = MediaLiveResponse()


url_paths = {
    "{0}/prod/channels": response.dispatch,
    "{0}/prod/inputs": response.dispatch,
}
