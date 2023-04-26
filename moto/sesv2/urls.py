"""sesv2 base URL and path."""
from .responses import SESV2Response

url_bases = [
    r"https?://email\.(.+)\.amazonaws\.com",
]


response = SESV2Response()


url_paths = {
    "{0}/.*$": response.dispatch,
}
