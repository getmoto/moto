"""scheduler base URL and path."""
from .responses import EventBridgeSchedulerResponse

url_bases = [
    r"https?://scheduler\.(.+)\.amazonaws\.com",
]


response = EventBridgeSchedulerResponse()


url_paths = {
    "{0}/schedules$": response.dispatch,
    "{0}/schedules/(?P<name>[^/]+)$": response.dispatch,
    "{0}/schedule-groups$": response.dispatch,
    "{0}/schedule-groups/(?P<name>[^/]+)$": response.dispatch,
    "{0}/tags/(?P<ResourceArn>.+)$": response.tags,
    "{0}/tags/arn:aws:scheduler:(?P<region_name>[^/]+):(?P<account_id>[^/]+):schedule/(?P<group_name>[^/]+)/(?P<schedule_name>[^/]+)/?$": response.tags,
}
