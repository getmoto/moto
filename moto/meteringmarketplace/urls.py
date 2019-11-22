from __future__ import unicode_literals
from .responses import MarketplaceMeteringResponse

url_bases = ["https?://marketplacemetering.(.+).amazonaws.com"]

url_paths = {"{0}/$": MarketplaceMeteringResponse.dispatch}
