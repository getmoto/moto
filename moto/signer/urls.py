"""signer base URL and path."""
from .responses import signerResponse

url_bases = [
    r"https?://signer\.(.+)\.amazonaws\.com",
]


response = signerResponse()


url_paths = {
    "{0}/signing-profiles/(?P<profile_name>[^/]+)$": response.dispatch,
    "{0}/signing-platforms$": response.dispatch,
}
