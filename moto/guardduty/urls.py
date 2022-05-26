from __future__ import unicode_literals
from .responses import GuardDutyResponse

response = GuardDutyResponse()

url_bases = [
    "https?://guardduty\\.(.+)\\.amazonaws\\.com",
]


url_paths = {
    "{0}/detector$": response.detectors,
    "{0}/detector/(?P<detector_id>[^/]+)$": response.detector,
    "{0}/detector/(?P<detector_id>[^/]+)/filter$": response.filters,
    "{0}/detector/(?P<detector_id>[^/]+)/filter/(?P<filter_name>[^/]+)$": response.filter,
    "{0}/admin/enable$": response.enable_organization_admin_account,
    "{0}/admin$": response.list_organization_admin_accounts,
}
