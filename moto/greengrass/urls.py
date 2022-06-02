from .responses import GreengrassResponse

url_bases = [
    "https?://greengrass\.(.+)\.amazonaws.com",
]


response = GreengrassResponse()


url_paths = {
    "{0}/.*$": response.dispatch,
}
