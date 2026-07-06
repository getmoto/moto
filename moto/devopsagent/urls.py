from .responses import DevOpsAgentResponse

url_bases = [
    r"https?://aidevops\.(.+)\.amazonaws\.com",
]

url_paths = {
    "{0}/.*$": DevOpsAgentResponse.dispatch,
}
