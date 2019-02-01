from __future__ import unicode_literals
from .responses import ECRResponse

url_bases = [
    "https?://ecr.(.+).amazonaws.com",
    "https?://api.ecr.(.+).amazonaws.com",
]

url_paths = {
    '{0}/$': ECRResponse.dispatch,
}
