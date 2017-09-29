from __future__ import unicode_literals
from .responses import BatchResponse

url_bases = [
    "https?://batch.(.+).amazonaws.com",
]

url_paths = {
    '{0}/v1/createcomputeenvironment$': BatchResponse.dispatch,
    '{0}/v1/describecomputeenvironments$': BatchResponse.dispatch,
}
