from __future__ import unicode_literals
from .responses import SimpleSystemManagerResponse

url_bases = [
    "https?://ssm.(.+).amazonaws.com",
    "https?://ssm.(.+).amazonaws.com.cn",
]

url_paths = {
    '{0}/$': SimpleSystemManagerResponse.dispatch,
}
