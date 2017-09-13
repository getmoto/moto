from __future__ import unicode_literals
from .responses import LambdaResponse

url_bases = [
    "https?://lambda.(.+).amazonaws.com",
]

response = LambdaResponse()

url_paths = {
    '{0}/(?P<api_version>[^/]+)/functions/?$': response.root,
    r'{0}/(?P<api_version>[^/]+)/functions/(?P<function_name>[\w_-]+)/?$': response.function,
    r'{0}/(?P<api_version>[^/]+)/functions/(?P<function_name>[\w_-]+)/invocations/?$': response.invoke,
    r'{0}/(?P<api_version>[^/]+)/tags/(?P<resource_arn>.+)': response.tag
}
