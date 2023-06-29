"""Route53 base URL and path."""
from typing import Any
from .responses import Route53
from moto.core.common_types import TYPE_RESPONSE

url_bases = [r"https?://route53(\..+)?\.amazonaws.com"]


def tag_response1(request: Any, full_url: str, headers: Any) -> TYPE_RESPONSE:
    return Route53().list_or_change_tags_for_resource_request(
        request, full_url, headers
    )


def tag_response2(request: Any, full_url: str, headers: Any) -> TYPE_RESPONSE:
    return Route53().list_or_change_tags_for_resource_request(
        request, full_url, headers
    )


url_paths = {
    r"{0}/(?P<api_version>[\d_-]+)/hostedzone$": Route53().list_or_create_hostzone_response,
    r"{0}/(?P<api_version>[\d_-]+)/hostedzone/(?P<zone_id>[^/]+)$": Route53().get_or_delete_hostzone_response,
    r"{0}/(?P<api_version>[\d_-]+)/hostedzone/(?P<zone_id>[^/]+)/rrset$": Route53().rrset_response,
    r"{0}/(?P<api_version>[\d_-]+)/hostedzone/(?P<zone_id>[^/]+)/rrset/$": Route53().rrset_response,
    r"{0}/(?P<api_version>[\d_-]+)/hostedzone/(?P<zone_id>[^/]+)/dnssec$": Route53().get_dnssec_response,
    r"{0}/(?P<api_version>[\d_-]+)/hostedzone/(?P<zone_id>[^/]+)/dnssec/$": Route53().get_dnssec_response,
    r"{0}/(?P<api_version>[\d_-]+)/hostedzone/(?P<zone_id>[^/]+)/associatevpc/?$": Route53().associate_vpc_response,
    r"{0}/(?P<api_version>[\d_-]+)/hostedzone/(?P<zone_id>[^/]+)/disassociatevpc/?$": Route53().disassociate_vpc_response,
    r"{0}/(?P<api_version>[\d_-]+)/hostedzonesbyname": Route53().list_hosted_zones_by_name_response,
    r"{0}/(?P<api_version>[\d_-]+)/hostedzonesbyvpc": Route53().list_hosted_zones_by_vpc_response,
    r"{0}/(?P<api_version>[\d_-]+)/hostedzonecount": Route53().get_hosted_zone_count_response,
    r"{0}/(?P<api_version>[\d_-]+)/healthcheck$": Route53().health_check_response1,
    r"{0}/(?P<api_version>[\d_-]+)/healthcheck/(?P<health_check_id>[^/]+)$": Route53().health_check_response2,
    r"{0}/(?P<api_version>[\d_-]+)/healthcheck/(?P<health_check_id>[^/]+)/status$": Route53().health_check_status_response,
    r"{0}/(?P<api_version>[\d_-]+)/tags/healthcheck/(?P<zone_id>[^/]+)$": tag_response1,
    r"{0}/(?P<api_version>[\d_-]+)/tags/hostedzone/(?P<zone_id>[^/]+)$": tag_response2,
    r"{0}/(?P<api_version>[\d_-]+)/trafficpolicyinstances/*": Route53().not_implemented_response,
    r"{0}/(?P<api_version>[\d_-]+)/change/(?P<change_id>[^/]+)$": Route53().get_change,
    r"{0}/(?P<api_version>[\d_-]+)/queryloggingconfig$": Route53().list_or_create_query_logging_config_response,
    r"{0}/(?P<api_version>[\d_-]+)/queryloggingconfig/(?P<query_id>[^/]+)$": Route53().get_or_delete_query_logging_config_response,
    r"{0}/(?P<api_version>[\d_-]+)/delegationset$": Route53().reusable_delegation_sets,
    r"{0}/(?P<api_version>[\d_-]+)/delegationset/(?P<delegation_set_id>[^/]+)$": Route53().reusable_delegation_set,
}
