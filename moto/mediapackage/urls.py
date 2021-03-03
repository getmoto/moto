from __future__ import unicode_literals
from .responses import MediaPackageResponse

url_bases = [
    "https?://mediapackage.(.+).amazonaws.com",
]


response = MediaPackageResponse()


url_paths = {
    '{0}/.*$': response.dispatch,
    
}
