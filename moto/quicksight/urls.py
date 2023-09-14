"""quicksight base URL and path."""
from .responses import QuickSightResponse

url_bases = [
    r"https?://quicksight\.(.+)\.amazonaws\.com",
]


url_paths = {
    r"{0}/accounts/(?P<account_id>[\d]+)/data-sets$": QuickSightResponse.method_dispatch(
        QuickSightResponse.dataset
    ),
    r"{0}/accounts/(?P<account_id>[\d]+)/data-sets/(?P<datasetid>[^/.]+)/ingestions/(?P<ingestionid>[^/.]+)$": QuickSightResponse.method_dispatch(
        QuickSightResponse.ingestion
    ),
    r"{0}/accounts/(?P<account_id>[\d]+)/namespaces/(?P<namespace>[a-zA-Z0-9._-]+)/groups$": QuickSightResponse.method_dispatch(
        QuickSightResponse.groups
    ),
    r"{0}/accounts/(?P<account_id>[\d]+)/namespaces/(?P<namespace>[a-zA-Z0-9._-]+)/groups/(?P<groupname>[^/]+)$": QuickSightResponse.method_dispatch(
        QuickSightResponse.group
    ),
    r"{0}/accounts/(?P<account_id>[\d]+)/namespaces/(?P<namespace>[a-zA-Z0-9._-]+)/groups/(?P<groupname>[^/]+)/members$": QuickSightResponse.method_dispatch(
        QuickSightResponse.group_members
    ),
    r"{0}/accounts/(?P<account_id>[\d]+)/namespaces/(?P<namespace>[a-zA-Z0-9._-]+)/groups/(?P<groupname>[^/]+)/members/(?P<username>[^/]+)$": QuickSightResponse.method_dispatch(
        QuickSightResponse.group_member
    ),
    r"{0}/accounts/(?P<account_id>[\d]+)/namespaces/(?P<namespace>[a-zA-Z0-9._-]+)/users$": QuickSightResponse.method_dispatch(
        QuickSightResponse.users
    ),
    r"{0}/accounts/(?P<account_id>[\d]+)/namespaces/(?P<namespace>[a-zA-Z0-9._-]+)/users/(?P<username>[^/]+)$": QuickSightResponse.method_dispatch(
        QuickSightResponse.user
    ),
}
