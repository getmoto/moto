from .responses import DynamoDBStreamsHandler

url_bases = ["https?://streams.dynamodb.(.+).amazonaws.com"]

url_paths = {"{0}/$": DynamoDBStreamsHandler.dispatch}
