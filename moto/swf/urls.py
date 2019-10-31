from .responses import SWFResponse

url_bases = ["https?://swf.(.+).amazonaws.com"]

url_paths = {"{0}/$": SWFResponse.dispatch}
