"""pinpoint base URL and path."""
from .responses import PinpointResponse

url_bases = [
    r"https?://pinpoint\.(.+)\.amazonaws\.com",
]


url_paths = {
    "{0}/v1/apps$": PinpointResponse.method_dispatch(PinpointResponse.apps),
    "{0}/v1/apps/(?P<app_id>[^/]+)$": PinpointResponse.method_dispatch(
        PinpointResponse.app
    ),
    "{0}/v1/apps/(?P<app_id>[^/]+)/eventstream": PinpointResponse.method_dispatch(
        PinpointResponse.eventstream
    ),
    "{0}/v1/apps/(?P<app_id>[^/]+)/settings$": PinpointResponse.method_dispatch(
        PinpointResponse.app_settings
    ),
    "{0}/v1/tags/(?P<app_arn>[^/]+)$": PinpointResponse.method_dispatch(
        PinpointResponse.tags
    ),
    "{0}/v1/tags/(?P<app_arn_pt_1>[^/]+)/(?P<app_arn_pt_2>[^/]+)$": PinpointResponse.method_dispatch(
        PinpointResponse.tags
    ),
}
