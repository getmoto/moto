from __future__ import unicode_literals
from .responses import MotoResponse

url_bases = [
    "https?://motointernal.(.+).amazonaws.com",
]

url_paths = {
    # double curly braces because the `format()` method is called on the strings
    '{0}/rpc/reflect/(?P<method_path>.+)$': MotoResponse.dynamic_invoke,
}
