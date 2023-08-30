from .responses import GuardDutyResponse

url_bases = [
    "https?://guardduty\\.(.+)\\.amazonaws\\.com",
]


url_paths = {
    "{0}/detector$": GuardDutyResponse.method_dispatch(GuardDutyResponse.detectors),
    "{0}/detector/(?P<detector_id>[^/]+)$": GuardDutyResponse.method_dispatch(
        GuardDutyResponse.detector
    ),
    "{0}/detector/(?P<detector_id>[^/]+)/filter$": GuardDutyResponse.method_dispatch(
        GuardDutyResponse.filters
    ),
    "{0}/detector/(?P<detector_id>[^/]+)/filter/(?P<filter_name>[^/]+)$": GuardDutyResponse.method_dispatch(
        GuardDutyResponse.filter
    ),
    "{0}/admin/enable$": GuardDutyResponse.method_dispatch(
        GuardDutyResponse.enable_organization_admin_account
    ),
    "{0}/admin$": GuardDutyResponse.method_dispatch(
        GuardDutyResponse.list_organization_admin_accounts
    ),
}
