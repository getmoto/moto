"""s3vectors base URL and path."""

from .responses import S3VectorsResponse

url_bases = [
    r"https?://s3vectors\.(.+)\.api\.aws",
]

url_paths = {
    "{0}/CreateVectorBucket$": S3VectorsResponse.dispatch,
    "{0}/DeleteVectorBucket$": S3VectorsResponse.dispatch,
    "{0}/GetVectorBucket$": S3VectorsResponse.dispatch,
    "{0}/ListVectorBuckets$": S3VectorsResponse.dispatch,
}
