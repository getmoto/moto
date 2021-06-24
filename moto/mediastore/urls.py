from __future__ import unicode_literals
from .responses import MediaStoreResponse

url_bases = [
    "https?://mediastore.(.+).amazonaws.com",
]

response = MediaStoreResponse()

url_paths = {
    "{0}/$": response.dispatch,
}
