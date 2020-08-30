from __future__ import unicode_literals
from .responses import KinesisVideoResponse

url_bases = [
    "https?://kinesisvideo.(.+).amazonaws.com",
]


response = KinesisVideoResponse()


url_paths = {
    "{0}/.*$": response.dispatch,
}
