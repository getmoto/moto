from __future__ import unicode_literals
from .responses import CloudFormationResponse

url_bases = [r"https?://cloudformation\.(.+)\.amazonaws\.com"]

url_paths = {"{0}/$": CloudFormationResponse.dispatch}
