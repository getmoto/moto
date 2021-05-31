from __future__ import unicode_literals

from .responses import WafV2Handler

url_bases = [
    "https?://wafv2.(.+).amazonaws.com",
]

url_paths = {
    "{0}/": WafV2Handler.dispatch,
}
