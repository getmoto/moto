"""ivs base URL and path."""
from .responses import IVSResponse


url_bases = [
    r"https?://ivs\.(.+)\.amazonaws\.com",
]


response = IVSResponse()


url_paths = {
    "{0}/CreateChannel": response.dispatch,
    "{0}/ListChannels": response.dispatch,
    "{0}/GetChannel": response.dispatch,
    "{0}/BatchGetChannel": response.dispatch,
    "{0}/UpdateChannel": response.dispatch,
    "{0}/DeleteChannel": response.dispatch,
}
