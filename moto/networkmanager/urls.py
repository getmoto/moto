"""networkmanager base URL and path."""

from .responses import NetworkManagerResponse

url_bases = [
    r"https?://networkmanager\.(.+)\.amazonaws\.com",
]

url_paths = {
    "0/.*$": NetworkManagerResponse.dispatch,
    "{0}/global-networks$": NetworkManagerResponse.dispatch,
    "{0}/core-networks$": NetworkManagerResponse.dispatch,
}
