"""appmesh base URL and path."""

from .responses import AppMeshResponse

url_bases = [
    r"https?://appmesh\.(.+)\.amazonaws\.com",
]

url_paths = {
    "{0}/v20190125/meshes$": AppMeshResponse.dispatch,
    "{0}/v20190125/meshes/(?P<meshName>[^/]+)$": AppMeshResponse.dispatch,
    "{0}/v20190125/tags$": AppMeshResponse.dispatch,
    "{0}/v20190125/tag$": AppMeshResponse.dispatch,
}
