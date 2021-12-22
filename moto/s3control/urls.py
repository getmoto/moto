"""s3control base URL and path."""
from .responses import S3ControlResponse

url_bases = [
    r"https?://(.+)\.s3-control\.(.+)\.amazonaws\.com",
]

url_paths = {
    "{0}/v20180820/configuration/publicAccessBlock$": S3ControlResponse.dispatch
}
