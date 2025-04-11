"""codedeploy base URL and path."""

from .responses import CodeDeployResponse

url_bases = [
    r"https?://codedeploy\.(.+)\.amazonaws\.com",
]

url_paths = {
    "{0}/$": CodeDeployResponse.dispatch,
}
