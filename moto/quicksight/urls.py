"""quicksight base URL and path."""
from .responses import QuickSightResponse

url_bases = [
    r"https?://quicksight\.(.+)\.amazonaws\.com",
]


response = QuickSightResponse()


url_paths = {
    r"{0}/accounts/(?P<account_id>[\d]+)/namespaces/(?P<namespace>[^/.]+)/groups$": response.groups,
    r"{0}/accounts/(?P<account_id>[\d]+)/namespaces/(?P<namespace>[^/.]+)/groups/(?P<groupname>[^/.]+)$": response.group,
    r"{0}/accounts/(?P<account_id>[\d]+)/namespaces/(?P<namespace>[^/.]+)/users$": response.users,
    r"{0}/accounts/(?P<account_id>[\d]+)/namespaces/(?P<namespace>[^/.]+)/users/(?P<username>[^/.]+)$": response.user,
}
