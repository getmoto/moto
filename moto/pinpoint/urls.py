"""pinpoint base URL and path."""
from .responses import PinpointResponse

url_bases = [
    r"https?://pinpoint\.(.+)\.amazonaws\.com",
]


response = PinpointResponse()


url_paths = {
    "{0}/v1/apps$": response.apps,
    "{0}/v1/apps/(?P<app_id>[^/]+)$": response.app,
    "{0}/v1/apps/(?P<app_id>[^/]+)/eventstream": response.eventstream,
    "{0}/v1/apps/(?P<app_id>[^/]+)/settings$": response.app_settings,
    "{0}/v1/tags/(?P<app_arn>[^/]+)$": response.tags,
    "{0}/v1/tags/(?P<app_arn_pt_1>[^/]+)/(?P<app_arn_pt_2>[^/]+)$": response.tags,
}
