"""synthetics base URL and path."""

from .responses import SyntheticsResponse

url_bases = [
    r"https?://synthetics\.(.+)\.amazonaws\.com",
]

url_paths = {
    "{0}/$": SyntheticsResponse.get_health_check,
    "{0}/.*$": SyntheticsResponse.dispatch,
}
