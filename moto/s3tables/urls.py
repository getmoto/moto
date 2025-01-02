"""s3tables base URL and path."""

from .responses import S3TablesResponse

url_bases = [
    r"https?://s3tables\.(.+)\.amazonaws\.com",
]

url_paths = {
    "{0}/buckets$": S3TablesResponse.dispatch,
    "{0}/buckets/(?P<tableBucketARN>[^/]+)$": S3TablesResponse.dispatch,
}
