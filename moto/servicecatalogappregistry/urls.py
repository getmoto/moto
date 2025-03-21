"""servicecatalogappregistry base URL and path."""

from .responses import AppRegistryResponse

url_bases = [
    r"https?://servicecatalog-appregistry\.(.+)\.amazonaws\.com",
]

url_paths = {
    "{0}/applications$": AppRegistryResponse.dispatch,
}
