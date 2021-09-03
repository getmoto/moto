from .responses import AthenaResponse

url_bases = ["https?://athena\.(.+)\.amazonaws\.com"]

url_paths = {"{0}/$": AthenaResponse.dispatch}
