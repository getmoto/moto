from .responses import QueueResponse, QueuesResponse

base_url = "https://(.*).amazonaws.com"
#base_url2 = "https://sqs.us-east-1.amazonaws.com"


urls = {
    '{0}/$'.format(base_url): QueuesResponse().dispatch,
    '{0}/(\d+)/(.*)$'.format(base_url): QueueResponse().dispatch,
}
