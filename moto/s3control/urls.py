"""s3control base URL and path."""
from .responses import S3ControlResponse

url_bases = [
    r"https?://([0-9]+)\.s3-control\.(.+)\.amazonaws\.com",
]


url_paths = {
    r"{0}/v20180820/configuration/publicAccessBlock$": S3ControlResponse.method_dispatch(
        S3ControlResponse.public_access_block
    ),
    r"{0}/v20180820/accesspoint/(?P<name>[\w_:%-]+)$": S3ControlResponse.method_dispatch(
        S3ControlResponse.access_point
    ),
    r"{0}/v20180820/accesspoint/(?P<name>[\w_:%-]+)/policy$": S3ControlResponse.method_dispatch(
        S3ControlResponse.access_point_policy
    ),
    r"{0}/v20180820/accesspoint/(?P<name>[\w_:%-]+)/policyStatus$": S3ControlResponse.method_dispatch(
        S3ControlResponse.access_point_policy_status
    ),
}
