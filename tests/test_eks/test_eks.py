from __future__ import unicode_literals

from datetime import datetime
from random import randint

import boto3
import pytest
import sure  # noqa

from moto.eks.exceptions import ResourceNotFoundException
from moto.utilities.utils import random_string
from test_eks_constants import (
    ArnAttributes,
    ArnFormats,
    BatchCountSize,
    ClusterAttribute,
    ClusterInputs,
    MessageTemplates,
    PageCount,
    PARTITIONS,
    ResponseAttribute,
    REGION,
    SERVICE,
    STATUS,
)
from test_eks_utils import generate_clusters, is_valid_uri, region_matches_partition

from moto import mock_eks
from moto.core import ACCOUNT_ID
from moto.core.utils import iso_8601_datetime_without_milliseconds
from moto.eks.responses import DEFAULT_MAX_RESULTS


@pytest.fixture(scope="function")
def setup():
    def _execute(count=1, minimal=True):
        client = boto3.client(SERVICE)
        cluster_names = generate_clusters(client, count, minimal)
        cluster = client.describe_cluster(
            name=cluster_names if isinstance(cluster_names, str) else cluster_names[0]
        )[ClusterAttribute.CLUSTER]

        return client, cluster_names, cluster

    mock_eks().start()
    yield _execute
    mock_eks().stop()


@pytest.fixture(scope="function")
def randomNames():
    def _execute(name_list):
        name_on_list = name_off_list = name_list[randint(0, len(name_list) - 1)]
        while name_off_list in name_list:
            name_off_list = random_string()
        return name_on_list, name_off_list

    return _execute


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
    client, cluster_names, _ = setup(BatchCountSize.MEDIUM)

    result = client.list_clusters()[ResponseAttribute.CLUSTERS]

    result.should.equal(sorted(cluster_names))
    len(result).should.equal(BatchCountSize.MEDIUM)


def test_list_clusters_returns_default_max_results(setup):
    client, cluster_names, _ = setup(BatchCountSize.LARGE)

    result = client.list_clusters()[ResponseAttribute.CLUSTERS]

    len(result).should.equal(DEFAULT_MAX_RESULTS)
    result.should.equal((sorted(cluster_names))[:DEFAULT_MAX_RESULTS])


def test_list_clusters_returns_custom_max_results(setup):
    client, cluster_names, _ = setup(BatchCountSize.MEDIUM)

    result = client.list_clusters(maxResults=PageCount.LARGE)[
        ResponseAttribute.CLUSTERS
    ]

    len(result).should.equal(PageCount.LARGE)
    result.should.equal((sorted(cluster_names))[: PageCount.LARGE])


def test_list_clusters_returns_second_page_results(setup):
    client, cluster_names, _ = setup(BatchCountSize.MEDIUM)
    token = client.list_clusters(maxResults=PageCount.LARGE)[
        ResponseAttribute.NEXT_TOKEN
    ]

    result = client.list_clusters(nextToken=token)[ResponseAttribute.CLUSTERS]

    len(result).should.equal(BatchCountSize.MEDIUM - PageCount.LARGE)
    result.should.equal((sorted(cluster_names))[PageCount.LARGE :])


def test_list_clusters_returns_custom_second_page_results(setup):
    client, cluster_names, _ = setup(BatchCountSize.MEDIUM)
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


def test_create_cluster_generates_valid_cluster_arn(setup):
    client, cluster_name, test_cluster = setup()
    result_arn = test_cluster[ClusterAttribute.ARN]
    result_name = test_cluster[ClusterAttribute.NAME]

    match = ArnFormats.CLUSTER_ARN.match(result_arn)
    returned_region = match.group(ArnAttributes.REGION)
    returned_partition = match.group(ArnAttributes.PARTITION)

    match.should.be.true
    returned_partition.should.be.within(PARTITIONS)
    returned_region.should.equal(REGION)
    match.group(ArnAttributes.ACCOUNT_ID).should.equal(ACCOUNT_ID)
    match.group(ArnAttributes.CLUSTER_NAME).should.equal(result_name)
    region_matches_partition(returned_region, returned_partition).should.be.true


@pytest.mark.freeze_time
def test_create_cluster_generates_valid_cluster_created_timestamp(setup):
    client, cluster_name, test_cluster = setup()
    current_time = iso_8601_datetime_without_milliseconds(datetime.now())

    result_time = iso_8601_datetime_without_milliseconds(
        test_cluster[ClusterAttribute.CREATED_AT]
    )

    result_time.should.equal(current_time)


def test_create_cluster_generates_valid_cluster_endpoint(setup):
    client, cluster_name, test_cluster = setup()

    result_endpoint = test_cluster[ClusterAttribute.ENDPOINT]

    is_valid_uri(result_endpoint).should.be.true
    result_endpoint.should.contain(REGION)


def test_create_cluster_generates_valid_oidc_identity(setup):
    client, cluster_name, test_cluster = setup()

    result_issuer = test_cluster[ClusterAttribute.IDENTITY][ClusterAttribute.OIDC][
        ClusterAttribute.ISSUER
    ]

    is_valid_uri(result_issuer).should.be.true
    result_issuer.should.contain(REGION)


def test_create_cluster_saves_provided_parameters(setup):
    client, cluster_name, test_cluster = setup(minimal=False)
    test_list = (
        ClusterInputs.REQUIRED
        + ClusterInputs.OPTIONAL
        + [STATUS, (ClusterAttribute.NAME, cluster_name)]
    )

    for key, expected_value in test_list:
        test_cluster[key].should.equal(expected_value)


def test_describe_cluster_throws_exception_when_cluster_not_found(setup, randomNames):
    client, cluster_names, _ = setup(BatchCountSize.MEDIUM)
    _, non_existent_cluster_name = randomNames(cluster_names)

    client.describe_cluster.when.called_with(
        name=non_existent_cluster_name
    ).should.throw(
        ResourceNotFoundException,
        MessageTemplates.ClusterNotFound.format(name=non_existent_cluster_name),
    )


def test_delete_cluster_returns_deleted_cluster(setup, randomNames):
    client, cluster_names, _ = setup(BatchCountSize.MEDIUM, False)
    chosen_cluster_name, _ = randomNames(cluster_names)
    test_list = (
        ClusterInputs.REQUIRED
        + ClusterInputs.OPTIONAL
        + [(ClusterAttribute.NAME, chosen_cluster_name)]
    )

    result = client.delete_cluster(name=chosen_cluster_name)[ResponseAttribute.CLUSTER]

    for key, expected_value in test_list:
        result[key].should.equal(expected_value)


def test_delete_cluster_removes_deleted_cluster(setup, randomNames):
    client, cluster_names, _ = setup(BatchCountSize.MEDIUM, False)
    chosen_cluster_name, _ = randomNames(cluster_names)

    client.delete_cluster(name=chosen_cluster_name)
    result_cluster_list = client.list_clusters()[ResponseAttribute.CLUSTERS]

    len(result_cluster_list).should.equal(BatchCountSize.MEDIUM - 1)
    result_cluster_list.should_not.contain(chosen_cluster_name)


def test_delete_cluster_throws_exception_when_cluster_not_found(setup, randomNames):
    client, cluster_names, _ = setup(BatchCountSize.MEDIUM)
    _, non_existent_cluster_name = randomNames(cluster_names)

    client.delete_cluster.when.called_with(name=non_existent_cluster_name).should.throw(
        ResourceNotFoundException,
        MessageTemplates.ClusterNotFound.format(name=non_existent_cluster_name),
    )
    len(client.list_clusters()[ResponseAttribute.CLUSTERS]).should.equal(
        BatchCountSize.MEDIUM
    )
