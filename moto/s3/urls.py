from .responses import bucket_response, key_response

url_bases = [
    "https?://(?P<bucket_name>\w*)\.?s3.amazonaws.com"
]

url_paths = {
    '{0}/$': bucket_response,
    '{0}/(?P<key_name>\w+)': key_response,
}
