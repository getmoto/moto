"""connectcampaigns base URL and path."""

from .responses import ConnectCampaignServiceResponse

url_bases = [
    r"https?://connect-campaigns\.(.+)\.amazonaws\.com",
]

url_paths = {
    "{0}/campaigns$": ConnectCampaignServiceResponse.dispatch,
    "{0}/campaigns/(?P<id>[^/]+)$": ConnectCampaignServiceResponse.dispatch,
    "{0}/connect-instance/(?P<connectInstanceId>[^/]+)/config$": ConnectCampaignServiceResponse.dispatch,
    "{0}/connect-instance/(?P<connectInstanceId>[^/]+)/onboarding$": ConnectCampaignServiceResponse.dispatch,
}
