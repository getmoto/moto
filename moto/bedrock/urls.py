"""bedrock base URL and path."""
from .responses import BedrockResponse

url_bases = [
    r"https?://bedrock\.(.+)\.amazonaws\.com",
]

url_paths = {
    "{0}/.*$": BedrockResponse.dispatch,
}
