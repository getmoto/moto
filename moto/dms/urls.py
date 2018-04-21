from __future__ import unicode_literals
from .responses import DMSServiceResponse

url_bases = [
    "https?://dms.(.+).amazonaws.com",
]

url_paths = {
    '{0}/$': EC2ContainerServiceResponse.dispatch,
}
