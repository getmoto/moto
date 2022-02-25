"""s3control base URL and path."""
from .responses import S3ControlResponseInstance

url_bases = [
    r"https?://([0-9]+)\.s3-control\.(.+)\.amazonaws\.com",
]


url_paths = {
    "{0}/v20180820/configuration/publicAccessBlock$": S3ControlResponseInstance.public_access_block,
    "{0}/v20180820/accesspoint/(?P<name>[\w_:%-]+)$": S3ControlResponseInstance.access_point,
    "{0}/v20180820/accesspoint/(?P<name>[\w_:%-]+)/policy$": S3ControlResponseInstance.access_point_policy,
    "{0}/v20180820/accesspoint/(?P<name>[\w_:%-]+)/policyStatus$": S3ControlResponseInstance.access_point_policy_status,
}
