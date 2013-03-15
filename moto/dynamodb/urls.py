from .responses import handler

url_bases = [
    "https?://dynamodb.us-east-1.amazonaws.com",
    "https?://sts.amazonaws.com",
]

url_paths = {
    "{0}/": handler,
}
