"""mq base URL and path."""
from .responses import MQResponse

url_bases = [
    r"https?://mq\.(.+)\.amazonaws\.com",
]


response = MQResponse()


url_paths = {
    "{0}/v1/brokers/(?P<broker_id>[^/]+)$": response.broker,
    "{0}/v1/brokers/(?P<broker_id>[^/]+)/reboot$": response.reboot,
    "{0}/v1/brokers/(?P<broker_id>[^/]+)/users$": response.users,
    "{0}/v1/brokers/(?P<broker_id>[^/]+)/users/(?P<user_name>[^/]+)$": response.user,
    "{0}/v1/brokers$": response.brokers,
    "{0}/v1/configurations$": response.configurations,
    "{0}/v1/configurations/(?P<config_id>[^/]+)$": response.configuration,
    "{0}/v1/configurations/(?P<config_id>[^/]+)/revisions/(?P<revision_id>[^/]+)$": response.configuration_revision,
    "{0}/v1/tags/(?P<resource_arn>[^/]+)$": response.tags,
}
