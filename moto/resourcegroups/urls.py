from __future__ import unicode_literals
from .responses import ResourceGroupsResponse

url_bases = [
    "https?://resource-groups(-fips)?.(.+).amazonaws.com",
]

url_paths = {
    '{0}/groups$': ResourceGroupsResponse.dispatch,
    '{0}/groups/(?P<resource_group_name>[^/]+)$': ResourceGroupsResponse.dispatch,
    '{0}/groups/(?P<resource_group_name>[^/]+)/query$': ResourceGroupsResponse.dispatch,
    '{0}/groups-list$': ResourceGroupsResponse.dispatch,
    '{0}/resources/(?P<resource_arn>[^/]+)/tags$': ResourceGroupsResponse.dispatch,
}
