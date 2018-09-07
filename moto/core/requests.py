"""
Shortcut module to mimic requests.get and requests.post
"""

from botocore.httpsession import URLLib3Session
from botocore.awsrequest import AWSRequest

_session = URLLib3Session()


def get(url):
    return _session.send(AWSRequest(method="GET", url=url).prepare())


def post(url, data=None, json=None, headers=None):
    return _session.send(AWSRequest(method="POST", url=url, data=(data or json), headers=headers).prepare())
