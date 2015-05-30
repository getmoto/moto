from __future__ import unicode_literals
from .responses import RDSResponse

url_bases = [
    "https?://rds(\..+)?.amazonaws.com",
]

url_paths = {
    '{0}/$': RDSResponse.dispatch,
}
