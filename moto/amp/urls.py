"""amp base URL and path."""
from .responses import PrometheusServiceResponse

url_bases = [
    r"https?://aps\.(.+)\.amazonaws\.com",
]


response = PrometheusServiceResponse()


url_paths = {
    "{0}/workspaces$": response.dispatch,
    "{0}/workspaces/(?P<workspace_id>[^/]+)$": response.dispatch,
    "{0}/workspaces/(?P<workspace_id>[^/]+)/alias$": response.dispatch,
    "{0}/workspaces/(?P<workspace_id>[^/]+)/rulegroupsnamespaces$": response.dispatch,
    "{0}/workspaces/(?P<workspace_id>[^/]+)/rulegroupsnamespaces/(?P<name>[^/]+)$": response.dispatch,
    "{0}/tags/(?P<resource_arn>[^/]+)$": response.dispatch,
    "{0}/tags/(?P<arn_prefix>[^/]+)/(?P<workspace_id>[^/]+)$": response.tags,
    "{0}/tags/(?P<arn_prefix>[^/]+)/(?P<workspace_id>[^/]+)/(?P<ns_name>[^/]+)$": response.tags,
}
