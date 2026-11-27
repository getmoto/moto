from .responses import BatchResponse

url_bases = [r"https?://batch\.(.+)\.amazonaws.com"]

url_paths = {
    "{0}/.*$": BatchResponse.dispatch,
}
