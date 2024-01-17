"""backup base URL and path."""
from .responses import BackupResponse

url_bases = [
    r"https?://backup\.(.+)\.amazonaws\.com",
]


response = BackupResponse()


url_paths = {
    "{0}/.*$": response.dispatch,
}
