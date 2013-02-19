from .responses import all_buckets, bucket_response, key_response

base_url = "https://(.*).s3.amazonaws.com"

urls = {
    'https://s3.amazonaws.com/$': all_buckets,
    '{0}/$'.format(base_url): bucket_response,
    '{}/(.+)'.format(base_url): key_response,
}
