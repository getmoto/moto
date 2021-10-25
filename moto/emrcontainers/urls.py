"""emrcontainers base URL and path."""
from .responses import EMRContainersResponse

url_bases = [
    r"https?://emr-containers\.(.+)\.amazonaws\.com",
]


url_paths = {
    "{0}/": EMRContainersResponse.dispatch,
}
