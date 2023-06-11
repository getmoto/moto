"""appconfig base URL and path."""
from .responses import AppConfigResponse

url_bases = [
    r"https?://appconfig\.(.+)\.amazonaws\.com",
]


response = AppConfigResponse()


url_paths = {
    "{0}/applications$": response.dispatch,
    "{0}/applications/(?P<app_id>[^/]+)$": response.dispatch,
    "{0}/applications/(?P<app_id>[^/]+)/configurationprofiles$": response.dispatch,
    "{0}/applications/(?P<app_id>[^/]+)/configurationprofiles/(?P<config_profile_id>[^/]+)$": response.dispatch,
    "{0}/applications/(?P<app_id>[^/]+)/configurationprofiles/(?P<config_profile_id>[^/]+)/hostedconfigurationversions$": response.dispatch,
    "{0}/applications/(?P<app_id>[^/]+)/configurationprofiles/(?P<config_profile_id>[^/]+)/hostedconfigurationversions/(?P<version>[^/]+)$": response.dispatch,
    "{0}/tags/(?P<app_id>.+)$": response.dispatch,
    "{0}/tags/(?P<arn_part_1>[^/]+)/(?P<app_id>[^/]+)$": response.tags,
    "{0}/tags/(?P<arn_part_1>[^/]+)/(?P<app_id>[^/]+)/configurationprofile/(?P<cp_id>[^/]+)$": response.tags,
}
