from .responses import GreengrassResponse

url_bases = [
    r"https?://greengrass\.(.+)\.amazonaws.com",
]

response = GreengrassResponse()

url_paths = {
    "{0}/greengrass/definition/cores$": response.core_definitions,
    "{0}/greengrass/definition/cores/(?P<definition_id>[^/]+)/?$": response.core_definition,
    "{0}/greengrass/definition/cores/(?P<definition_id>[^/]+)/versions$": response.core_definition_versions,
    "{0}/greengrass/definition/cores/(?P<definition_id>[^/]+)/versions/(?P<definition_version_id>[^/]+)/?$": response.core_definition_version,
    "{0}/greengrass/definition/devices$": response.device_definitions,
    "{0}/greengrass/definition/devices/(?P<definition_id>[^/]+)/?$": response.device_definition,
    "{0}/greengrass/definition/devices/(?P<definition_id>[^/]+)/versions$": response.device_definition_versions,
    "{0}/greengrass/definition/devices/(?P<definition_id>[^/]+)/versions/(?P<definition_version_id>[^/]+)/?$": response.device_definition_version,
    "{0}/greengrass/definition/functions$": response.function_definitions,
    "{0}/greengrass/definition/functions/(?P<definition_id>[^/]+)/?$": response.function_definition,
    "{0}/greengrass/definition/functions/(?P<definition_id>[^/]+)/versions$": response.function_definition_versions,
    "{0}/greengrass/definition/functions/(?P<definition_id>[^/]+)/versions/(?P<definition_version_id>[^/]+)/?$": response.function_definition_version,
    "{0}/greengrass/definition/resources$": response.resource_definitions,
    "{0}/greengrass/definition/resources/(?P<definition_id>[^/]+)/?$": response.resource_definition,
    "{0}/greengrass/definition/resources/(?P<definition_id>[^/]+)/versions$": response.resource_definition_versions,
    "{0}/greengrass/definition/subscriptions$": response.subscription_definitions,
    "{0}/greengrass/definition/subscriptions/(?P<definition_id>[^/]+)/?$": response.subscription_definition,
    "{0}/greengrass/definition/subscriptions/(?P<definition_id>[^/]+)/versions$": response.subscription_definition_versions,
    "{0}/greengrass/definition/subscriptions/(?P<definition_id>[^/]+)/versions/(?P<definition_version_id>[^/]+)/?$": response.subscription_definition_version,
    "{0}/greengrass/definition/resources/(?P<definition_id>[^/]+)/versions/(?P<definition_version_id>[^/]+)/?$": response.resource_definition_version,
    "{0}/greengrass/groups$": response.groups,
    "{0}/greengrass/groups/(?P<group_id>[^/]+)/?$": response.group,
    "{0}/greengrass/groups/(?P<group_id>[^/]+)/role$": response.role,
    "{0}/greengrass/groups/(?P<group_id>[^/]+)/versions$": response.group_versions,
    "{0}/greengrass/groups/(?P<group_id>[^/]+)/deployments$": response.deployments,
    "{0}/greengrass/groups/(?P<group_id>[^/]+)/deployments/\\$reset$": response.deployments_reset,
    "{0}/greengrass/groups/(?P<group_id>[^/]+)/deployments/(?P<group_version_id>[^/]+)/status$": response.deployment_satus,
    "{0}/greengrass/groups/(?P<group_id>[^/]+)/versions/(?P<group_version_id>[^/]+)/?$": response.group_version,
}
