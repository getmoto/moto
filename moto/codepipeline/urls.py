from __future__ import unicode_literals
from .responses import CodePipelineResponse

url_bases = ["https?://codepipeline.(.+).amazonaws.com"]

url_paths = {"{0}/$": CodePipelineResponse.dispatch}
