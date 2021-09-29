from __future__ import unicode_literals
from .responses import DataPipelineResponse

url_bases = [r"https?://datapipeline\.(.+)\.amazonaws\.com"]

url_paths = {"{0}/$": DataPipelineResponse.dispatch}
