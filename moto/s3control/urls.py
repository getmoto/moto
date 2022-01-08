"""s3control base URL and path."""
from .responses import S3ControlResponse

url_bases = [
    r"https?://([0-9]+)\.s3-control\.(.+)\.amazonaws\.com",
]


url_paths = {
    "{0}/v20180820/configuration/publicAccessBlock$": S3ControlResponse.public_access_block,
}
