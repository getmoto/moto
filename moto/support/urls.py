from __future__ import unicode_literals
from .responses import SupportResponse

url_bases = [
    "https?://support.(.+).amazonaws.com",
]


url_paths = {
    "{0}/$": SupportResponse.dispatch,
}
