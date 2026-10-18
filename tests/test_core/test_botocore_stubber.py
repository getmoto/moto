from time import time

from botocore.awsrequest import AWSPreparedRequest, HTTPHeaders

from moto.core.botocore_stubber import BotocoreStubber


def test_performance_for_url_with_many_dots() -> None:
    # See https://github.com/getmoto/moto/issues/8185
    request = AWSPreparedRequest(
        method="GET",
        url="https://my-bucket.s3.eu-central-1.amazonaws.com"
        "/a.1.1.1.1.1.1/b.2.2.2.2.2.2.2/c.3.3.3.3.3.3/d.4.4.4.4.4.4.4.4.4",
        headers=HTTPHeaders(),
        body=None,
        stream_output=False,
    )
    start = time()
    BotocoreStubber().process_request(request=request)
    end = time()
    # We don't care about the exact response
    # we just want to ensure matching for a URL like this doesn't take forever
    assert (end - start) < 1
