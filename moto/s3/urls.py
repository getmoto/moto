from .responses import S3ResponseInstance

url_bases = [
    "https?://(?P<bucket_name>[a-zA-Z0-9\-_.]*)\.?s3.amazonaws.com"
]

url_paths = {
    '{0}/$': S3ResponseInstance.bucket_response,
    '{0}/(?P<key_name>[a-zA-Z0-9\-_.]+)': S3ResponseInstance.key_response,
}
