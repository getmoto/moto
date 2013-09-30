from .responses import DynamoHandler

url_bases = [
    "https?://dynamodb.(.+).amazonaws.com",
    "https?://sts.amazonaws.com",
]

url_paths = {
    "{0}/": DynamoHandler().dispatch,
}
