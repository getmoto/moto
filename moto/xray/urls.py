from __future__ import unicode_literals
from .responses import XRayResponse

url_bases = [
    "https?://xray.(.+).amazonaws.com",
]

url_paths = {
    '{0}/.+$': XRayResponse.dispatch,
}
