from __future__ import unicode_literals
from .responses import BatchResponse

url_bases = [
    "https?://batch.(.+).amazonaws.com",
]

url_paths = {
    '{0}/v1/createcomputeenvironment$': BatchResponse.dispatch,
    '{0}/v1/describecomputeenvironments$': BatchResponse.dispatch,
    '{0}/v1/deletecomputeenvironment': BatchResponse.dispatch,
    '{0}/v1/updatecomputeenvironment': BatchResponse.dispatch,
    '{0}/v1/createjobqueue': BatchResponse.dispatch,
    '{0}/v1/describejobqueues': BatchResponse.dispatch,
    '{0}/v1/updatejobqueue': BatchResponse.dispatch,
    '{0}/v1/deletejobqueue': BatchResponse.dispatch
}
