from __future__ import unicode_literals
from .responses import Route53

url_bases = ["https?://route53(.*).amazonaws.com"]


def tag_response1(*args, **kwargs):
    return Route53().list_or_change_tags_for_resource_request(*args, **kwargs)


def tag_response2(*args, **kwargs):
    return Route53().list_or_change_tags_for_resource_request(*args, **kwargs)


url_paths = {
    r"{0}/(?P<api_version>[\d_-]+)/hostedzone$": Route53().list_or_create_hostzone_response,
    r"{0}/(?P<api_version>[\d_-]+)/hostedzone/(?P<zone_id>[^/]+)$": Route53().get_or_delete_hostzone_response,
    r"{0}/(?P<api_version>[\d_-]+)/hostedzone/(?P<zone_id>[^/]+)/rrset/?$": Route53().rrset_response,
    r"{0}/(?P<api_version>[\d_-]+)/hostedzonesbyname": Route53().list_hosted_zones_by_name_response,
    r"{0}/(?P<api_version>[\d_-]+)/healthcheck": Route53().health_check_response,
    r"{0}/(?P<api_version>[\d_-]+)/tags/healthcheck/(?P<zone_id>[^/]+)$": tag_response1,
    r"{0}/(?P<api_version>[\d_-]+)/tags/hostedzone/(?P<zone_id>[^/]+)$": tag_response2,
    r"{0}/(?P<api_version>[\d_-]+)/trafficpolicyinstances/*": Route53().not_implemented_response,
    r"{0}/(?P<api_version>[\d_-]+)/change/(?P<change_id>[^/]+)$": Route53().get_change,
}
