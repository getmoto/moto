from .responses import bucket_response, key_response

url_bases = [
    "https?://(?P<bucket_name>[a-zA-Z0-9\-_.]*)\.?s3.amazonaws.com"
]

url_paths = {
    '{0}/$': bucket_response,
    '{0}/(?P<key_name>[a-zA-Z0-9\-_.]+)': key_response,
}
