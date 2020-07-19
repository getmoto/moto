from __future__ import unicode_literals
from .responses import ResourceAccessManagerResponse

url_bases = ["https?://ram.(.+).amazonaws.com"]

url_paths = {"{0}/.*$": ResourceAccessManagerResponse.dispatch}
