from __future__ import unicode_literals
from .responses import LambdaResponse

url_bases = [
    "https?://lambda.(.+).amazonaws.com",
]

url_paths = {
    # double curly braces because the `format()` method is called on the strings
    '{0}/\d{{4}}-\d{{2}}-\d{{2}}/functions/?$': LambdaResponse.root,
    '{0}/\d{{4}}-\d{{2}}-\d{{2}}/functions/(?P<function_name>[\w_-]+)/?$': LambdaResponse.function,
    '{0}/\d{{4}}-\d{{2}}-\d{{2}}/functions/(?P<function_name>[\w_-]+)/invocations?$': LambdaResponse.invoke,
}
