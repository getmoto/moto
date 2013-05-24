from .responses import TokenResponse

url_bases = [
    "https?://sts.amazonaws.com"
]

url_paths = {
    '{0}/$': TokenResponse().dispatch,
}
