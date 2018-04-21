from __future__ import unicode_literals
from .responses import DMSServiceResponse

url_bases = [
    "https?://dms.(.+).amazonaws.com",
]

url_paths = {
    '{0}/$': DMSServiceResponse.dispatch,
}
