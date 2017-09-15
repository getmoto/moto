from __future__ import unicode_literals
from .responses import LambdaResponse

url_bases = [
    "https?://lambda.(.+).amazonaws.com",
]

response = LambdaResponse()

url_paths = {
    '{0}/(?P<api_version>[^/]+)/functions/?$': response.root,
    '{0}/(?P<api_version>[^/]+)/functions/(?P<function_name>[\w_-]+)/?$': response.function,
    '{0}/(?P<api_version>[^/]+)/functions/(?P<function_name>[\w_-]+)/invocations/?$': response.invoke,
    '{0}/(?P<api_version>[^/]+)/functions/(?P<function_name>[\w_-]+)/invoke-async/?$': response.invoke_async,
    '{0}/(?P<api_version>[^/]+)/tags/(?P<resource_arn>.+)': response.tag,
    '{0}/(?P<api_version>[^/]+)/functions/(?P<function_name>[\w_-]+)/policy(/.*)?$': response.policy
}
