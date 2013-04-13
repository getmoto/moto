from .responses import handler

url_bases = [
    "https?://dynamodb.(.+).amazonaws.com",
    "https?://sts.amazonaws.com",
]

url_paths = {
    "{0}/": handler,
}
