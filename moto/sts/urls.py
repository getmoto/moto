from __future__ import unicode_literals
from .responses import TokenResponse

url_bases = [r"https?://sts\.(.*)amazonaws\.com(|.cn)"]

url_paths = {"{0}/$": TokenResponse.dispatch}
