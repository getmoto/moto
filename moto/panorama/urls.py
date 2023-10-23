from .responses import PanoramaResponse

url_bases = [
    r"https?://api\.panorama\.(.+)\.amazonaws.com",
]

url_paths = {
    "{0}/$": PanoramaResponse.dispatch,
}
