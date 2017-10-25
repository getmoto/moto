from __future__ import unicode_literals
from ..elb.urls import api_version_elb_backend

url_bases = [
    "https?://elasticloadbalancing.(.+).amazonaws.com",
]

url_paths = {
    '{0}/$': api_version_elb_backend,
}
