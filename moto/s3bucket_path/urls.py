from .responses import S3BucketPathResponseInstance as ro

url_bases = [
    "https?://s3.amazonaws.com"
]


def bucket_response2(*args):
    return ro.bucket_response(*args)


def bucket_response3(*args):
    return ro.bucket_response(*args)

url_paths = {
    '{0}/$': bucket_response3,
    '{0}/(?P<bucket_name>[a-zA-Z0-9\-_.]+)$': ro.bucket_response,
    '{0}/(?P<bucket_name>[a-zA-Z0-9\-_.]+)/$': bucket_response2,
    '{0}/(?P<bucket_name>[a-zA-Z0-9\-_./]+)/(?P<key_name>.+)': ro.key_response
}
