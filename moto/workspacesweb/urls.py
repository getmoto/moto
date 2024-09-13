"""workspacesweb base URL and path."""

from .responses import WorkSpacesWebResponse

url_bases = [
    r"https?://workspaces-web\.(.+)\.amazonaws\.com",
]

url_paths = {
    "{0}/browserSettings$": WorkSpacesWebResponse.dispatch,
    "{0}/networkSettings$": WorkSpacesWebResponse.dispatch,
    "{0}/portals$": WorkSpacesWebResponse.dispatch,
    "{0}/browserSettings/(?P<browserSettingsArn>[^/]+)$": WorkSpacesWebResponse.dispatch,
    "{0}/networkSettings/(?P<networkSettingsArn>[^/]+)$": WorkSpacesWebResponse.dispatch,
    "{0}/portals/(?P<portalArn>[^/]+)$": WorkSpacesWebResponse.dispatch,
    "{0}/portals/(?P<portalArn>.*)/browserSettings$": WorkSpacesWebResponse.dispatch,
    "{0}/portals/(?P<portalArn>.*)/networkSettings$": WorkSpacesWebResponse.dispatch,
}
