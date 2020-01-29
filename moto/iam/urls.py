from __future__ import unicode_literals
from .responses import IamResponse

url_bases = ["https?://iam(.*).amazonaws.com"]

url_paths = {"{0}/$": IamResponse.dispatch}
