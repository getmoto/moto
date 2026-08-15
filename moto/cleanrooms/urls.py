"""cleanrooms base URL and path."""

from .responses import CleanRoomsResponse

url_bases = [
    r"https?://cleanrooms\.(.+)\.amazonaws\.com",
]

url_paths = {
    "{0}/collaborations$": CleanRoomsResponse.dispatch,
    "{0}/collaborations/(?P<collaborationIdentifier>[^/]+)$": CleanRoomsResponse.dispatch,
    "{0}/collaborations/(?P<collaborationIdentifier>[^/]+)/members$": CleanRoomsResponse.dispatch,
    "{0}/memberships$": CleanRoomsResponse.dispatch,
    "{0}/memberships/(?P<membershipIdentifier>[^/]+)$": CleanRoomsResponse.dispatch,
    "{0}/configuredTables$": CleanRoomsResponse.dispatch,
    "{0}/configuredTables/(?P<configuredTableIdentifier>[^/]+)$": CleanRoomsResponse.dispatch,
    "{0}/tags/(?P<resourceArn>.+)$": CleanRoomsResponse.dispatch,
}
