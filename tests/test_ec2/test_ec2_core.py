from __future__ import unicode_literals
import requests
from moto import mock_ec2


@mock_ec2
def test_not_implemented_method():
    requests.post.when.called_with(
        "https://ec2.us-east-1.amazonaws.com/",
        data={'Action': ['foobar']}
    ).should.throw(NotImplementedError)
