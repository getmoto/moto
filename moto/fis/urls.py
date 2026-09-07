"""fis base URL and path."""

from .responses import FISResponse

url_bases = [
    r"https?://fis\.(.+)\.amazonaws\.com",
]

url_paths = {
    "{0}/experimentTemplates$": FISResponse.dispatch,
    "{0}/experimentTemplates/(?P<id>.+)$": FISResponse.dispatch,
    "{0}/tags/(?P<resourceArn>.+)$": FISResponse.dispatch,
    "{0}/experiments$": FISResponse.dispatch,
    "{0}/experiments/(?P<id>.+)$": FISResponse.dispatch,
    "{0}/experimentTemplates/(?P<id>[^/]+)/targetAccountConfigurations/(?P<accountId>.+)$": FISResponse.dispatch,
    "{0}/actions/(?P<id>.+)$": FISResponse.dispatch,
    "{0}/actions$": FISResponse.dispatch,
    "{0}/experiments/(?P<id>[^/]+)/targetAccountConfigurations/(?P<accountId>.+)$": FISResponse.dispatch,
    "{0}/targetResourceTypes/(?P<resourceType>.+)$": FISResponse.dispatch,
    "{0}/experiments/(?P<id>[^/]+)/resolvedTargets$": FISResponse.dispatch,
    "{0}/experiments/(?P<id>[^/]+)/targetAccountConfigurations$": FISResponse.dispatch,
    "{0}/targetResourceTypes$": FISResponse.dispatch,
    "{0}/experimentTemplates/(?P<id>[^/]+)/targetAccountConfigurations$": FISResponse.dispatch,
}
