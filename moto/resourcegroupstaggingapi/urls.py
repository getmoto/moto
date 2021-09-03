from .responses import ResourceGroupsTaggingAPIResponse

url_bases = ["https?://tagging.(.+).amazonaws.com"]

url_paths = {"{0}/$": ResourceGroupsTaggingAPIResponse.dispatch}
