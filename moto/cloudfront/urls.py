"""cloudfront base URL and path."""
from .responses import CloudFrontResponse


url_bases = [
    r"https?://cloudfront\.amazonaws\.com",
]
url_paths = {
    "{0}/2020-05-31/distribution$": CloudFrontResponse.method_dispatch(
        CloudFrontResponse.distributions
    ),
    "{0}/2020-05-31/distribution/(?P<distribution_id>[^/]+)$": CloudFrontResponse.method_dispatch(
        CloudFrontResponse.individual_distribution
    ),
    "{0}/2020-05-31/distribution/(?P<distribution_id>[^/]+)/config$": CloudFrontResponse.method_dispatch(
        CloudFrontResponse.update_distribution
    ),
    "{0}/2020-05-31/distribution/(?P<distribution_id>[^/]+)/invalidation": CloudFrontResponse.method_dispatch(
        CloudFrontResponse.invalidation
    ),
    "{0}/2020-05-31/tagging$": CloudFrontResponse.method_dispatch(
        CloudFrontResponse.tags
    ),
    "{0}/2020-05-31/origin-access-control$": CloudFrontResponse.method_dispatch(
        CloudFrontResponse.origin_access_controls
    ),
    "{0}/2020-05-31/origin-access-control/(?P<oac_id>[^/]+)$": CloudFrontResponse.method_dispatch(
        CloudFrontResponse.origin_access_control
    ),
    "{0}/2020-05-31/origin-access-control/(?P<oac_id>[^/]+)/config$": CloudFrontResponse.method_dispatch(
        CloudFrontResponse.origin_access_control
    ),
}
