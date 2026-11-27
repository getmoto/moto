from .responses import DynamoDBStreamsHandler

url_bases = [
    r"https?://streams\.dynamodb\.(.+)\.amazonaws.com",
    r"https?://(.+)\.streams-ddb\.(.+)\.amazonaws.com",
]

url_paths = {"{0}/$": DynamoDBStreamsHandler.dispatch}
