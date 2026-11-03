"""workspacesweb base URL and path."""

from .responses import WorkSpacesWebResponse

url_bases = [
    r"https?://workspaces-web\.(.+)\.amazonaws\.com",
]

url_paths = {
    "{0}/.*$": WorkSpacesWebResponse.dispatch,
}
