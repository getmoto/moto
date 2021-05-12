from __future__ import unicode_literals

from copy import deepcopy

import boto3
import pytest
import sure  # noqa

from test_eks_constants import (
    BatchCountSize,
    ClusterAttribute,
    ClusterInputs,
    PageCount,
    ResponseAttribute,
    SERVICE,
)

from moto import mock_eks
from moto.eks.responses import DEFAULT_MAX_RESULTS
from moto.utilities.utils import random_string


@pytest.fixture(scope="function")
def setup():
    def _setup(count=1, minimal=True):
        client = boto3.client(SERVICE)
        cluster_names = _generate_clusters(client, count, minimal)

        return client, cluster_names

    mock_eks().start()
    yield _setup
    mock_eks().stop()


###
# This specific test does not use the fixture since
# it is intended to verify that there are no clusters
# in the list at initialization, which means the mock
# decorator must be used manually in this one case.
###
@mock_eks
def test_list_clusters_returns_empty_by_default():
    client = boto3.client(SERVICE)

    result = client.list_clusters()[ResponseAttribute.CLUSTERS]
    result.should.be.empty


def test_list_clusters_returns_sorted_cluster_names(setup):
    client, cluster_names = setup(BatchCountSize.MEDIUM)

    result = client.list_clusters()[ResponseAttribute.CLUSTERS]

    result.should.equal(sorted(cluster_names))


def test_list_clusters_returns_default_max_results(setup):
    client, cluster_names = setup(BatchCountSize.LARGE)

    result = client.list_clusters()[ResponseAttribute.CLUSTERS]

    len(result).should.equal(DEFAULT_MAX_RESULTS)
    result.should.equal((sorted(cluster_names))[:DEFAULT_MAX_RESULTS])


def test_list_clusters_returns_custom_max_results(setup):
    client, cluster_names = setup(BatchCountSize.MEDIUM)

    result = client.list_clusters(maxResults=PageCount.LARGE)[
        ResponseAttribute.CLUSTERS
    ]

    len(result).should.equal(PageCount.LARGE)
    result.should.equal((sorted(cluster_names))[: PageCount.LARGE])


def test_list_clusters_returns_second_page_results(setup):
    client, cluster_names = setup(BatchCountSize.MEDIUM)
    token = client.list_clusters(maxResults=PageCount.LARGE)[
        ResponseAttribute.NEXT_TOKEN
    ]

    result = client.list_clusters(nextToken=token)[ResponseAttribute.CLUSTERS]

    len(result).should.equal(BatchCountSize.MEDIUM - PageCount.LARGE)
    result.should.equal((sorted(cluster_names))[PageCount.LARGE :])


def test_list_clusters_returns_custom_second_page_results(setup):
    client, cluster_names = setup(BatchCountSize.MEDIUM)
    token = client.list_clusters(maxResults=PageCount.LARGE)[
        ResponseAttribute.NEXT_TOKEN
    ]

    result = client.list_clusters(maxResults=PageCount.SMALL, nextToken=token)[
        ResponseAttribute.CLUSTERS
    ]

    len(result).should.equal(PageCount.SMALL)
    result.should.equal(
        (sorted(cluster_names))[PageCount.LARGE : PageCount.LARGE + PageCount.SMALL]
    )


def _generate_clusters(client, num_clusters, minimal):
    input_values = deepcopy(ClusterInputs.REQUIRED)
    if not minimal:
        input_values.extend(deepcopy(ClusterInputs.OPTIONAL))

    cluster_names = [
        client.create_cluster(name=random_string(), **dict(input_values))[
            ClusterAttribute.CLUSTER
        ][ClusterAttribute.NAME]
        for _ in range(num_clusters)
    ]

    return cluster_names[0] if num_clusters == 1 else cluster_names
