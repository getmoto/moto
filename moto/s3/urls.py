from .responses import bucket_response, key_response

urls = {
    '/$': bucket_response,
    '/(.+)': key_response,
}
