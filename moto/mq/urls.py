"""mq base URL and path."""
from .responses import MQResponse

url_bases = [
    r"https?://mq\.(.+)\.amazonaws\.com",
]


url_paths = {
    "{0}/v1/brokers/(?P<broker_id>[^/]+)$": MQResponse.method_dispatch(
        MQResponse.broker
    ),
    "{0}/v1/brokers/(?P<broker_id>[^/]+)/reboot$": MQResponse.method_dispatch(
        MQResponse.reboot
    ),
    "{0}/v1/brokers/(?P<broker_id>[^/]+)/users$": MQResponse.method_dispatch(
        MQResponse.users
    ),
    "{0}/v1/brokers/(?P<broker_id>[^/]+)/users/(?P<user_name>[^/]+)$": MQResponse.method_dispatch(
        MQResponse.user
    ),
    "{0}/v1/brokers$": MQResponse.method_dispatch(MQResponse.brokers),
    "{0}/v1/configurations$": MQResponse.method_dispatch(MQResponse.configurations),
    "{0}/v1/configurations/(?P<config_id>[^/]+)$": MQResponse.method_dispatch(
        MQResponse.configuration
    ),
    "{0}/v1/configurations/(?P<config_id>[^/]+)/revisions/(?P<revision_id>[^/]+)$": MQResponse.method_dispatch(
        MQResponse.configuration_revision
    ),
    "{0}/v1/tags/(?P<resource_arn>[^/]+)$": MQResponse.method_dispatch(MQResponse.tags),
}
