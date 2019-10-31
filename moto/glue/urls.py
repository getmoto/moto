from __future__ import unicode_literals

from .responses import GlueResponse

url_bases = ["https?://glue(.*).amazonaws.com"]

url_paths = {"{0}/$": GlueResponse.dispatch}
