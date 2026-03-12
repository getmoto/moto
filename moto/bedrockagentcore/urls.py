# urls.py
from .responses import BedrockAgentCoreResponse

url_bases = [r"https?://bedrock-agentcore\.(.+)\.amazonaws\.com"]

url_paths = {
    "{0}/.*$": BedrockAgentCoreResponse.dispatch,
}
