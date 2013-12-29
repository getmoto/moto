from .responses import QueueResponse, QueuesResponse

url_bases = [
    "https?://(.*?)(queue|sqs)(.*?).amazonaws.com"
]

url_paths = {
    '{0}/$': QueuesResponse().dispatch,
    '{0}/(?P<account_id>\d+)/(?P<queue_name>[a-zA-Z0-9\-_]+)': QueueResponse().dispatch,
}
