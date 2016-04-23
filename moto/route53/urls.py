from __future__ import unicode_literals
from . import responses

url_bases = [
    "https://route53.amazonaws.com/201.-..-../",
]

url_paths = {
    '{0}hostedzone$': responses.list_or_create_hostzone_response,
    '{0}hostedzone/[^/]+$': responses.get_or_delete_hostzone_response,
    '{0}hostedzone/[^/]+/rrset/?$': responses.rrset_response,
    '{0}healthcheck': responses.health_check_response,
    '{0}tags|trafficpolicyinstances/*': responses.not_implemented_response,
}
