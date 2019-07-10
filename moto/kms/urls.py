from __future__ import unicode_literals
from .responses import KmsResponse

url_bases = ["https?://kms.(.+).amazonaws.com"]

url_paths = {"{0}/$": KmsResponse.dispatch}
