from __future__ import unicode_literals
from .responses import BatchResponse

url_bases = [
    "https?://batch.(.+).amazonaws.com",
]

url_paths = {
    '{0}/$': BatchResponse.dispatch,
}
