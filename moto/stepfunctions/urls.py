from __future__ import unicode_literals
from .responses import StepFunctionResponse

url_bases = ["https?://states.(.+).amazonaws.com"]

url_paths = {"{0}/$": StepFunctionResponse.dispatch}
