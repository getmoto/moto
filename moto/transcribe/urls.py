from __future__ import unicode_literals

from .responses import TranscribeResponse

url_bases = ["https?://transcribe.(.+).amazonaws.com"]

url_paths = {"{0}/$": TranscribeResponse.dispatch}
