from .responses import GreengrassResponse

url_bases = [
    r"https?://greengrass\.(.+)\.amazonaws.com",
]


response = GreengrassResponse()


url_paths = {
    "{0}/greengrass/definition/cores$": response.create_core_definition,
    "{0}/greengrass/definition/cores/(?P<definition_id>[^/]+)/versions$": response.create_core_definition_version,
}
