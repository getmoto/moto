from __future__ import unicode_literals
from .responses import ELBV2Response

url_bases = [
    "https?://elasticloadbalancing.(.+).amazonaws.com",
]

url_paths = {
    '{0}/$': ELBV2Response.dispatch,
}
