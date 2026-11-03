from .responses import XRayResponse

url_bases = [r"https?://xray\.(.+)\.amazonaws.com"]

url_paths = {
    "{0}/.*$": XRayResponse.dispatch,
}
