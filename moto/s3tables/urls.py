"""s3tables base URL and path."""

from .responses import S3TablesResponse

url_bases = [
    r"https?://s3tables\.(.+)\.amazonaws\.com",
]

url_paths = {
    "{0}/buckets$": S3TablesResponse.dispatch,
    "{0}/buckets/(?P<tableBucketARN>.+)$": S3TablesResponse.dispatch,
    "{0}/buckets/(?P<tableBucketARN_pt_1>[^/]+)/(?P<tableBucketARN_pt_2>[^/]+)$": S3TablesResponse.dispatch,
    "{0}/namespaces/(?P<tableBucketARN>.+)$": S3TablesResponse.dispatch,
}
