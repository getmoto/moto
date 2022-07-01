"""quicksight base URL and path."""
from .responses import QuickSightResponse

url_bases = [
    r"https?://quicksight\.(.+)\.amazonaws\.com",
]


response = QuickSightResponse()


url_paths = {
    r"{0}/accounts/(?P<account_id>[\d]+)/data-sets$": response.dataset,
    r"{0}/accounts/(?P<account_id>[\d]+)/data-sets/(?P<datasetid>[^/.]+)/ingestions/(?P<ingestionid>[^/.]+)$": response.ingestion,
    r"{0}/accounts/(?P<account_id>[\d]+)/namespaces/(?P<namespace>[a-zA-Z0-9._-]+)/groups$": response.groups,
    r"{0}/accounts/(?P<account_id>[\d]+)/namespaces/(?P<namespace>[a-zA-Z0-9._-]+)/groups/(?P<groupname>[^/]+)$": response.group,
    r"{0}/accounts/(?P<account_id>[\d]+)/namespaces/(?P<namespace>[a-zA-Z0-9._-]+)/groups/(?P<groupname>[^/]+)/members$": response.group_members,
    r"{0}/accounts/(?P<account_id>[\d]+)/namespaces/(?P<namespace>[a-zA-Z0-9._-]+)/groups/(?P<groupname>[^/]+)/members/(?P<username>[^/]+)$": response.group_member,
    r"{0}/accounts/(?P<account_id>[\d]+)/namespaces/(?P<namespace>[a-zA-Z0-9._-]+)/users$": response.users,
    r"{0}/accounts/(?P<account_id>[\d]+)/namespaces/(?P<namespace>[a-zA-Z0-9._-]+)/users/(?P<username>[^/]+)$": response.user,
}
