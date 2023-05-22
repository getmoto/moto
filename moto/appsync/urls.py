"""appsync base URL and path."""
from .responses import AppSyncResponse

url_bases = [
    r"https?://appsync\.(.+)\.amazonaws\.com",
]


response = AppSyncResponse()


url_paths = {
    "{0}/v1/apis$": response.graph_ql,
    "{0}/v1/apis/(?P<api_id>[^/]+)$": response.graph_ql_individual,
    "{0}/v1/apis/(?P<api_id>[^/]+)/apikeys$": response.api_key,
    "{0}/v1/apis/(?P<api_id>[^/]+)/apikeys/(?P<api_key_id>[^/]+)$": response.api_key_individual,
    "{0}/v1/apis/(?P<api_id>[^/]+)/schemacreation$": response.schemacreation,
    "{0}/v1/apis/(?P<api_id>[^/]+)/schema$": response.schema,
    "{0}/v1/tags/(?P<resource_arn>.+)$": response.tags,
    "{0}/v1/tags/(?P<resource_arn_pt1>.+)/(?P<resource_arn_pt2>.+)$": response.tags,
    "{0}/v1/apis/(?P<api_id>[^/]+)/types/(?P<type_name>.+)$": response.types,
}
