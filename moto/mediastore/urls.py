from __future__ import unicode_literals
from .responses import MediaStoreResponse

url_bases = [
    "https?://mediastore.(.+).amazonaws.com",
]



url_paths = {
    '{0}/$': MediaStoreResponse.dispatch,
}
