"""appsync base URL and path."""
from .responses import AppSyncResponse

url_bases = [
    r"https?://appsync\.(.+)\.amazonaws\.com",
]


url_paths = {
    "{0}/v1/apis$": AppSyncResponse.method_dispatch(AppSyncResponse.graph_ql),
    "{0}/v1/apis/(?P<api_id>[^/]+)$": AppSyncResponse.method_dispatch(
        AppSyncResponse.graph_ql_individual
    ),
    "{0}/v1/apis/(?P<api_id>[^/]+)/apikeys$": AppSyncResponse.method_dispatch(
        AppSyncResponse.api_key
    ),
    "{0}/v1/apis/(?P<api_id>[^/]+)/apikeys/(?P<api_key_id>[^/]+)$": AppSyncResponse.method_dispatch(
        AppSyncResponse.api_key_individual
    ),
    "{0}/v1/apis/(?P<api_id>[^/]+)/schemacreation$": AppSyncResponse.method_dispatch(
        AppSyncResponse.schemacreation
    ),
    "{0}/v1/apis/(?P<api_id>[^/]+)/schema$": AppSyncResponse.method_dispatch(
        AppSyncResponse.schema
    ),
    "{0}/v1/tags/(?P<resource_arn>.+)$": AppSyncResponse.method_dispatch(
        AppSyncResponse.tags
    ),
    "{0}/v1/tags/(?P<resource_arn_pt1>.+)/(?P<resource_arn_pt2>.+)$": AppSyncResponse.method_dispatch(
        AppSyncResponse.tags
    ),
    "{0}/v1/apis/(?P<api_id>[^/]+)/types/(?P<type_name>.+)$": AppSyncResponse.method_dispatch(
        AppSyncResponse.types
    ),
}
