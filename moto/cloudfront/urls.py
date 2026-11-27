"""cloudfront base URL and path."""

from .responses import CloudFrontResponse

url_bases = [
    r"https?://cloudfront\.amazonaws\.com",
    r"https?://cloudfront\.(.+)\.amazonaws\.com",
]
url_paths = {
    "{0}/.*$": CloudFrontResponse.dispatch,
}
