from __future__ import unicode_literals
from .responses import EmailResponse

url_bases = [
    "https?://email.(.+).amazonaws.com"
]

url_paths = {
    '{0}/$': EmailResponse.dispatch,
}
