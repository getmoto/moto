from __future__ import unicode_literals
from .responses import OrganizationsResponse

url_bases = [r"https?://organizations\.(.+)\.amazonaws\.com"]

url_paths = {"{0}/$": OrganizationsResponse.dispatch}
