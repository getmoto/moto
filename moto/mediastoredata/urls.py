from __future__ import unicode_literals

from .responses import MediaStoreDataResponse

url_bases = [
    "https?://data.mediastore.(.+).amazonaws.com",
]

response = MediaStoreDataResponse()

url_paths = {"{0}/$": response.dispatch, "{0}/(?P<Path>[^/.]+)$": response.dispatch}
