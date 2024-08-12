"""qldb base URL and path."""

from .responses import QLDBResponse

url_bases = [
    r"https?://qldb\.(.+)\.amazonaws\.com",
]

url_paths = {
    "0/.*$": QLDBResponse.dispatch,
}
