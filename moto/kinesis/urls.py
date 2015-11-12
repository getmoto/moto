from __future__ import unicode_literals
from .responses import KinesisResponse

url_bases = [
    "https?://kinesis.(.+).amazonaws.com",
    "https?://firehose.(.+).amazonaws.com",
]

url_paths = {
    '{0}/$': KinesisResponse.dispatch,
}
