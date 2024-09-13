"""workspacesweb base URL and path."""

from .responses import WorkSpacesWebResponse

url_bases = [
    r"https?://workspaces-web\.(.+)\.amazonaws\.com",
]

url_paths = {
    "{0}/browserSettings$": WorkSpacesWebResponse.dispatch,
    "{0}/networkSettings$": WorkSpacesWebResponse.dispatch,
    "{0}/portals$": WorkSpacesWebResponse.dispatch,
    "{0}/browserSettings/(?P<browserSettingsArn>.+)$": WorkSpacesWebResponse.browser_settings,
    "{0}/networkSettings/(?P<networkSettingsArn>.+)$": WorkSpacesWebResponse.network_settings,
    "{0}/portals/(?P<portalArn>[^/]+)portal/(?P<uuid>[^/]+)$": WorkSpacesWebResponse.portal,
    "{0}/portals/(?P<portalArn>.*)/browserSettings$": WorkSpacesWebResponse.dispatch,
    "{0}/portals/(?P<portalArn>.*)/networkSettings$": WorkSpacesWebResponse.dispatch,
}
