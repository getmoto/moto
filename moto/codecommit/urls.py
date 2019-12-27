from __future__ import unicode_literals
from .responses import CodeCommitResponse

url_bases = ["https?://codecommit.(.+).amazonaws.com"]

url_paths = {"{0}/$": CodeCommitResponse.dispatch}
