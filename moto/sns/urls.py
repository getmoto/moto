from __future__ import unicode_literals
from .responses import SNSResponse

url_bases = [r"https?://sns\.(.+)\.amazonaws\.com"]

url_paths = {"{0}/$": SNSResponse.dispatch}
