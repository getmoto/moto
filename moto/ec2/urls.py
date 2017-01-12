from __future__ import unicode_literals
from .responses import EC2Response


url_bases = [
    "https?://ec2.(.+).amazonaws.com(|.cn)",
]

url_paths = {
    '{0}/': EC2Response.dispatch,
}
