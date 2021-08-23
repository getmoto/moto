"""Firehose base url and path."""
from .responses import FirehoseResponse


url_bases = ["https?://firehose.(.+).amazonaws.com"]
url_paths = {"{0}/$": FirehoseResponse.dispatch}
