from .responses import DevOpsAgentResponse

url_bases = [
    r"https?://(.*\.)?aidevops\.(.+)\.api\.aws",
]

url_paths = {
    "{0}/.*$": DevOpsAgentResponse.dispatch,
}
