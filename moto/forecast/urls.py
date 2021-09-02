from __future__ import unicode_literals

from .responses import ForecastResponse

url_bases = [r"https?://forecast\.(.+)\.amazonaws\.com"]

url_paths = {"{0}/$": ForecastResponse.dispatch}
