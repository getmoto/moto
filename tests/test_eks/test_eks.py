from __future__ import unicode_literals

import boto3
import sure  # noqa
from moto import mock_eks


@mock_eks
def test_list_clusters_returns_empty_by_default():
    client = boto3.client('eks')

    result = client.list_clusters()['clusters']
    result.should.be.empty
