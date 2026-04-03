"""BedrockAgentCoreControl URLs."""

from .responses import BedrockAgentCoreControlResponse

url_bases = [
    r"https?://bedrock-agentcore-control\.(.+)\.amazonaws\.com",
]

url_paths = {
    "{0}/runtimes/$": BedrockAgentCoreControlResponse.dispatch,
    "{0}/runtimes/(?P<agentRuntimeId>[^/]+)/$": BedrockAgentCoreControlResponse.dispatch,
    "{0}/runtimes/(?P<agentRuntimeId>[^/]+)/versions/$": BedrockAgentCoreControlResponse.dispatch,
    "{0}/runtimes/(?P<agentRuntimeId>[^/]+)/runtime-endpoints/$": BedrockAgentCoreControlResponse.dispatch,
    "{0}/runtimes/(?P<agentRuntimeId>[^/]+)/runtime-endpoints/(?P<endpointName>[^/]+)/$": BedrockAgentCoreControlResponse.dispatch,
    "{0}/gateways/$": BedrockAgentCoreControlResponse.dispatch,
    "{0}/gateways/(?P<gatewayIdentifier>[^/]+)/$": BedrockAgentCoreControlResponse.dispatch,
    "{0}/gateways/(?P<gatewayIdentifier>[^/]+)/targets/$": BedrockAgentCoreControlResponse.dispatch,
    "{0}/gateways/(?P<gatewayIdentifier>[^/]+)/targets/(?P<targetId>[^/]+)/$": BedrockAgentCoreControlResponse.dispatch,
    "{0}/tags/(?P<resourceArn>.+)$": BedrockAgentCoreControlResponse.dispatch,
}
