from __future__ import unicode_literals
from .responses import SimpleSystemManagerResponse

url_bases = [
    "https?://ssm.(.+).amazonaws.com",
]

url_paths = {
    '{0}/$': SimpleSystemManagerResponse.dispatch,
}
