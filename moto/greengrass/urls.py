from .responses import GreengrassResponse

url_bases = [
    r"https?://greengrass\.(.+)\.amazonaws.com",
]

url_paths = {
    "{0}/greengrass/definition/cores$": GreengrassResponse.method_dispatch(
        GreengrassResponse.core_definitions
    ),
    "{0}/greengrass/definition/cores/(?P<definition_id>[^/]+)/?$": GreengrassResponse.method_dispatch(
        GreengrassResponse.core_definition
    ),
    "{0}/greengrass/definition/cores/(?P<definition_id>[^/]+)/versions$": GreengrassResponse.method_dispatch(
        GreengrassResponse.core_definition_versions
    ),
    "{0}/greengrass/definition/cores/(?P<definition_id>[^/]+)/versions/(?P<definition_version_id>[^/]+)/?$": GreengrassResponse.method_dispatch(
        GreengrassResponse.core_definition_version
    ),
    "{0}/greengrass/definition/devices$": GreengrassResponse.method_dispatch(
        GreengrassResponse.device_definitions
    ),
    "{0}/greengrass/definition/devices/(?P<definition_id>[^/]+)/?$": GreengrassResponse.method_dispatch(
        GreengrassResponse.device_definition
    ),
    "{0}/greengrass/definition/devices/(?P<definition_id>[^/]+)/versions$": GreengrassResponse.method_dispatch(
        GreengrassResponse.device_definition_versions
    ),
    "{0}/greengrass/definition/devices/(?P<definition_id>[^/]+)/versions/(?P<definition_version_id>[^/]+)/?$": GreengrassResponse.method_dispatch(
        GreengrassResponse.device_definition_version
    ),
    "{0}/greengrass/definition/functions$": GreengrassResponse.method_dispatch(
        GreengrassResponse.function_definitions
    ),
    "{0}/greengrass/definition/functions/(?P<definition_id>[^/]+)/?$": GreengrassResponse.method_dispatch(
        GreengrassResponse.function_definition
    ),
    "{0}/greengrass/definition/functions/(?P<definition_id>[^/]+)/versions$": GreengrassResponse.method_dispatch(
        GreengrassResponse.function_definition_versions
    ),
    "{0}/greengrass/definition/functions/(?P<definition_id>[^/]+)/versions/(?P<definition_version_id>[^/]+)/?$": GreengrassResponse.method_dispatch(
        GreengrassResponse.function_definition_version
    ),
    "{0}/greengrass/definition/resources$": GreengrassResponse.method_dispatch(
        GreengrassResponse.resource_definitions
    ),
    "{0}/greengrass/definition/resources/(?P<definition_id>[^/]+)/?$": GreengrassResponse.method_dispatch(
        GreengrassResponse.resource_definition
    ),
    "{0}/greengrass/definition/resources/(?P<definition_id>[^/]+)/versions$": GreengrassResponse.method_dispatch(
        GreengrassResponse.resource_definition_versions
    ),
    "{0}/greengrass/definition/subscriptions$": GreengrassResponse.method_dispatch(
        GreengrassResponse.subscription_definitions
    ),
    "{0}/greengrass/definition/subscriptions/(?P<definition_id>[^/]+)/?$": GreengrassResponse.method_dispatch(
        GreengrassResponse.subscription_definition
    ),
    "{0}/greengrass/definition/subscriptions/(?P<definition_id>[^/]+)/versions$": GreengrassResponse.method_dispatch(
        GreengrassResponse.subscription_definition_versions
    ),
    "{0}/greengrass/definition/subscriptions/(?P<definition_id>[^/]+)/versions/(?P<definition_version_id>[^/]+)/?$": GreengrassResponse.method_dispatch(
        GreengrassResponse.subscription_definition_version
    ),
    "{0}/greengrass/definition/resources/(?P<definition_id>[^/]+)/versions/(?P<definition_version_id>[^/]+)/?$": GreengrassResponse.method_dispatch(
        GreengrassResponse.resource_definition_version
    ),
    "{0}/greengrass/groups$": GreengrassResponse.method_dispatch(
        GreengrassResponse.groups
    ),
    "{0}/greengrass/groups/(?P<group_id>[^/]+)/?$": GreengrassResponse.method_dispatch(
        GreengrassResponse.group
    ),
    "{0}/greengrass/groups/(?P<group_id>[^/]+)/role$": GreengrassResponse.method_dispatch(
        GreengrassResponse.role
    ),
    "{0}/greengrass/groups/(?P<group_id>[^/]+)/versions$": GreengrassResponse.method_dispatch(
        GreengrassResponse.group_versions
    ),
    "{0}/greengrass/groups/(?P<group_id>[^/]+)/deployments$": GreengrassResponse.method_dispatch(
        GreengrassResponse.deployments
    ),
    "{0}/greengrass/groups/(?P<group_id>[^/]+)/deployments/\\$reset$": GreengrassResponse.method_dispatch(
        GreengrassResponse.deployments_reset
    ),
    "{0}/greengrass/groups/(?P<group_id>[^/]+)/deployments/(?P<group_version_id>[^/]+)/status$": GreengrassResponse.method_dispatch(
        GreengrassResponse.deployment_satus
    ),
    "{0}/greengrass/groups/(?P<group_id>[^/]+)/versions/(?P<group_version_id>[^/]+)/?$": GreengrassResponse.method_dispatch(
        GreengrassResponse.group_version
    ),
}
