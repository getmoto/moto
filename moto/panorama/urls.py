from .responses import PanoramaResponse

url_bases = [
    r"https?://panorama\.(.+)\.amazonaws.com",
]

url_paths = {
    "{0}/$": PanoramaResponse.dispatch,
    "{0}/devices$": PanoramaResponse.dispatch,
    "{0}/devices/(?P<DeviceId>[^/]+)$": PanoramaResponse.dispatch,
}
