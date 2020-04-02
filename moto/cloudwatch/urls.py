from .responses import CloudWatchResponse

url_bases = ["https?://monitoring.(.+).amazonaws.com"]

url_paths = {"{0}/$": CloudWatchResponse.dispatch}
