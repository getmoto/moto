from __future__ import unicode_literals

from copy import deepcopy
from datetime import datetime
from random import randint

import boto3
import mock
import pytest
import sure  # noqa

from moto.eks.exceptions import (
    ResourceNotFoundException,
    ResourceInUseException,
    InvalidRequestException,
    InvalidParameterException,
)
from moto.eks.models import (
    NODEGROUP_EXISTS_MSG,
    CLUSTER_NOT_READY_MSG,
    CLUSTER_NOT_FOUND_MSG,
    CLUSTER_IN_USE_MSG,
    LAUNCH_TEMPLATE_WITH_DISK_SIZE_MSG,
    LAUNCH_TEMPLATE_WITH_REMOTE_ACCESS_MSG,
)
from moto.utilities.utils import random_string
from test_eks_constants import (
    ArnAttributes,
    ArnFormats,
    BatchCountSize,
    ClusterAttribute,
    ClusterInputs,
    DISK_SIZE,
    INSTANCE_TYPES,
    LAUNCH_TEMPLATE,
    NodegroupInputs,
    PageCount,
    PARTITIONS,
    REMOTE_ACCESS,
    ResponseAttribute,
    REGION,
    SERVICE,
    STATUS,
    TestResults,
    MethodNames,
    NodegroupAttribute,
)
from test_eks_utils import (
    generate_clusters,
    is_valid_uri,
    region_matches_partition,
    generate_nodegroups,
)

from moto import mock_eks
from moto.core import ACCOUNT_ID
from moto.core.utils import iso_8601_datetime_without_milliseconds
from moto.eks.responses import DEFAULT_MAX_RESULTS


def client_setup():
    return boto3.client(SERVICE)


@pytest.fixture(scope="function")
def cluster_setup():
    def _execute(count=1, minimal=True):
        client = client_setup()
        cluster_names = generate_clusters(client, count, minimal)
        cluster = client.describe_cluster(
            name=cluster_names if isinstance(cluster_names, str) else cluster_names[0]
        )[ClusterAttribute.CLUSTER]

        return client, cluster_names, cluster

    mock_eks().start()
    yield _execute
    mock_eks().stop()


@pytest.fixture(scope="function")
def nodegroup_setup(cluster_setup):
    def _execute(count=1, minimal=True):
        client, cluster_name, _ = cluster_setup()
        nodegroup_names = generate_nodegroups(client, cluster_name, count, minimal)

        return client, cluster_name, nodegroup_names

    yield _execute


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


def test_list_clusters_returns_sorted_cluster_names(cluster_setup):
    client, cluster_names, _ = cluster_setup(BatchCountSize.MEDIUM)

    result = client.list_clusters()[ResponseAttribute.CLUSTERS]

    result.should.equal(sorted(cluster_names))
    len(result).should.equal(BatchCountSize.MEDIUM)


def test_list_clusters_returns_default_max_results(cluster_setup):
    client, cluster_names, _ = cluster_setup(BatchCountSize.LARGE)

    result = client.list_clusters()[ResponseAttribute.CLUSTERS]

    len(result).should.equal(DEFAULT_MAX_RESULTS)
    result.should.equal((sorted(cluster_names))[:DEFAULT_MAX_RESULTS])


def test_list_clusters_returns_custom_max_results(cluster_setup):
    client, cluster_names, _ = cluster_setup(BatchCountSize.MEDIUM)

    result = client.list_clusters(maxResults=PageCount.LARGE)[
        ResponseAttribute.CLUSTERS
    ]

    len(result).should.equal(PageCount.LARGE)
    result.should.equal((sorted(cluster_names))[: PageCount.LARGE])


def test_list_clusters_returns_second_page_results(cluster_setup):
    client, cluster_names, _ = cluster_setup(BatchCountSize.MEDIUM)
    token = client.list_clusters(maxResults=PageCount.LARGE)[
        ResponseAttribute.NEXT_TOKEN
    ]

    result = client.list_clusters(nextToken=token)[ResponseAttribute.CLUSTERS]

    len(result).should.equal(BatchCountSize.MEDIUM - PageCount.LARGE)
    result.should.equal((sorted(cluster_names))[PageCount.LARGE :])


def test_list_clusters_returns_custom_second_page_results(cluster_setup):
    client, cluster_names, _ = cluster_setup(BatchCountSize.MEDIUM)
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


def test_create_cluster_generates_valid_cluster_arn(cluster_setup):
    client, cluster_name, test_cluster = cluster_setup()
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
def test_create_cluster_generates_valid_cluster_created_timestamp(cluster_setup):
    client, cluster_name, test_cluster = cluster_setup()
    current_time = iso_8601_datetime_without_milliseconds(datetime.now())

    result_time = iso_8601_datetime_without_milliseconds(
        test_cluster[ClusterAttribute.CREATED_AT]
    )

    result_time.should.equal(current_time)


def test_create_cluster_generates_valid_cluster_endpoint(cluster_setup):
    client, cluster_name, test_cluster = cluster_setup()

    result_endpoint = test_cluster[ClusterAttribute.ENDPOINT]

    is_valid_uri(result_endpoint).should.be.true
    result_endpoint.should.contain(REGION)


def test_create_cluster_generates_valid_oidc_identity(cluster_setup):
    client, cluster_name, test_cluster = cluster_setup()

    result_issuer = test_cluster[ClusterAttribute.IDENTITY][ClusterAttribute.OIDC][
        ClusterAttribute.ISSUER
    ]

    is_valid_uri(result_issuer).should.be.true
    result_issuer.should.contain(REGION)


def test_create_cluster_saves_provided_parameters(cluster_setup):
    client, cluster_name, test_cluster = cluster_setup(minimal=False)
    test_list = (
        ClusterInputs.REQUIRED
        + ClusterInputs.OPTIONAL
        + [STATUS, (ClusterAttribute.NAME, cluster_name)]
    )

    for key, expected_value in test_list:
        test_cluster[key].should.equal(expected_value)


def test_describe_cluster_throws_exception_when_cluster_not_found(
    cluster_setup, randomNames
):
    client, cluster_names, _ = cluster_setup(BatchCountSize.MEDIUM)
    _, non_existent_cluster_name = randomNames(cluster_names)
    expected_exception = ResourceNotFoundException

    client.describe_cluster.when.called_with(
        name=non_existent_cluster_name
    ).should.throw(
        expected_exception,
        CLUSTER_NOT_FOUND_MSG.format(
            exception_name=expected_exception.TYPE,
            method=MethodNames.DESCRIBE_CLUSTER,
            cluster_name=non_existent_cluster_name,
        ),
    )


def test_delete_cluster_returns_deleted_cluster(cluster_setup, randomNames):
    client, cluster_names, _ = cluster_setup(BatchCountSize.MEDIUM, False)
    chosen_cluster_name, _ = randomNames(cluster_names)
    test_list = (
        ClusterInputs.REQUIRED
        + ClusterInputs.OPTIONAL
        + [(ClusterAttribute.NAME, chosen_cluster_name)]
    )

    result = client.delete_cluster(name=chosen_cluster_name)[ResponseAttribute.CLUSTER]

    for key, expected_value in test_list:
        result[key].should.equal(expected_value)


def test_delete_cluster_removes_deleted_cluster(cluster_setup, randomNames):
    client, cluster_names, _ = cluster_setup(BatchCountSize.MEDIUM, False)
    chosen_cluster_name, _ = randomNames(cluster_names)

    client.delete_cluster(name=chosen_cluster_name)
    result_cluster_list = client.list_clusters()[ResponseAttribute.CLUSTERS]

    len(result_cluster_list).should.equal(BatchCountSize.MEDIUM - 1)
    result_cluster_list.should_not.contain(chosen_cluster_name)


def test_delete_cluster_throws_exception_when_cluster_not_found(
    cluster_setup, randomNames
):
    client, cluster_names, _ = cluster_setup(BatchCountSize.MEDIUM)
    _, non_existent_cluster_name = randomNames(cluster_names)
    expected_exception = ResourceNotFoundException

    client.delete_cluster.when.called_with(name=non_existent_cluster_name).should.throw(
        expected_exception,
        CLUSTER_NOT_FOUND_MSG.format(
            exception_name=expected_exception.TYPE,
            method=MethodNames.DELETE_CLUSTER,
            cluster_name=non_existent_cluster_name,
        ),
    )
    len(client.list_clusters()[ResponseAttribute.CLUSTERS]).should.equal(
        BatchCountSize.MEDIUM
    )


def test_list_nodegroups_returns_empty_by_default(cluster_setup):
    client, cluster_name, _ = cluster_setup()

    result = client.list_nodegroups(clusterName=cluster_name)[
        ResponseAttribute.NODEGROUPS
    ]
    result.should.be.empty


def test_list_nodegroups_returns_sorted_nodegroup_names(nodegroup_setup):
    client, cluster_name, nodegroup_names = nodegroup_setup(BatchCountSize.MEDIUM)

    result = client.list_nodegroups(clusterName=cluster_name)[
        ResponseAttribute.NODEGROUPS
    ]

    result.should.equal(sorted(nodegroup_names))
    len(result).should.equal(BatchCountSize.MEDIUM)


def test_list_nodegroups_returns_default_max_results(nodegroup_setup):
    client, cluster_name, nodegroup_names = nodegroup_setup(BatchCountSize.LARGE)

    result = client.list_nodegroups(clusterName=cluster_name)[
        ResponseAttribute.NODEGROUPS
    ]

    len(result).should.equal(DEFAULT_MAX_RESULTS)
    result.should.equal((sorted(nodegroup_names))[:DEFAULT_MAX_RESULTS])


def test_list_nodegroups_returns_custom_max_results(nodegroup_setup):
    client, cluster_name, nodegroup_names = nodegroup_setup(BatchCountSize.LARGE)

    result = client.list_nodegroups(
        clusterName=cluster_name, maxResults=PageCount.LARGE
    )[ResponseAttribute.NODEGROUPS]

    len(result).should.equal(PageCount.LARGE)
    result.should.equal((sorted(nodegroup_names))[: PageCount.LARGE])


def test_list_nodegroups_returns_second_page_results(nodegroup_setup):
    client, cluster_name, nodegroup_names = nodegroup_setup(BatchCountSize.MEDIUM)
    token = client.list_nodegroups(
        clusterName=cluster_name, maxResults=PageCount.LARGE
    )[ResponseAttribute.NEXT_TOKEN]

    result = client.list_nodegroups(clusterName=cluster_name, nextToken=token)[
        ResponseAttribute.NODEGROUPS
    ]

    len(result).should.equal(BatchCountSize.MEDIUM - PageCount.LARGE)
    result.should.equal((sorted(nodegroup_names))[PageCount.LARGE :])


def test_list_nodegroups_returns_custom_second_page_results(nodegroup_setup):
    client, cluster_name, nodegroup_names = nodegroup_setup(BatchCountSize.MEDIUM)
    token = client.list_nodegroups(
        clusterName=cluster_name, maxResults=PageCount.LARGE
    )[ResponseAttribute.NEXT_TOKEN]

    result = client.list_nodegroups(
        clusterName=cluster_name, maxResults=PageCount.SMALL, nextToken=token
    )[ResponseAttribute.NODEGROUPS]

    len(result).should.equal(PageCount.SMALL)
    result.should.equal(
        (sorted(nodegroup_names))[PageCount.LARGE : PageCount.LARGE + PageCount.SMALL]
    )


@mock_eks
def test_create_nodegroup_throws_exception_when_cluster_not_found(randomNames):
    client = boto3.client(SERVICE)
    nodegroup_inputs = deepcopy(NodegroupInputs.REQUIRED)
    non_existent_cluster_name = random_string()
    nodegroup_name = random_string()
    expected_exception = ResourceNotFoundException

    client.create_nodegroup.when.called_with(
        clusterName=non_existent_cluster_name,
        nodegroupName=nodegroup_name,
        **dict(nodegroup_inputs)
    ).should.throw(
        expected_exception,
        CLUSTER_NOT_FOUND_MSG.format(
            exception_name=expected_exception.TYPE,
            method=MethodNames.CREATE_NODEGROUP,
            cluster_name=non_existent_cluster_name,
        ),
    )


def test_create_nodegroup_throws_exception_when_nodegroup_already_exists(
    nodegroup_setup, randomNames
):
    client, cluster_name, nodegroup_names = nodegroup_setup(BatchCountSize.MEDIUM)
    chosen_nodegroup_name, _ = randomNames(nodegroup_names)
    nodegroup_inputs = deepcopy(NodegroupInputs.REQUIRED)
    expected_exception = ResourceInUseException

    client.create_nodegroup.when.called_with(
        clusterName=cluster_name,
        nodegroupName=chosen_nodegroup_name,
        **dict(nodegroup_inputs)
    ).should.throw(
        expected_exception,
        NODEGROUP_EXISTS_MSG.format(
            exception_name=expected_exception.TYPE,
            method=MethodNames.CREATE_NODEGROUP,
            cluster_name=cluster_name,
            nodegroup_name=chosen_nodegroup_name,
        ),
    )
    len(
        client.list_nodegroups(clusterName=cluster_name)[ResponseAttribute.NODEGROUPS]
    ).should.equal(BatchCountSize.MEDIUM)


def test_create_nodegroup_throws_exception_when_cluster_not_active(
    nodegroup_setup, randomNames, monkeypatch
):
    client, cluster_name, nodegroup_names = nodegroup_setup(BatchCountSize.MEDIUM)
    _, new_nodegroup_name = randomNames(nodegroup_names)
    nodegroup_inputs = deepcopy(NodegroupInputs.REQUIRED)
    expected_exception = InvalidRequestException

    with mock.patch("moto.eks.models.Cluster.isActive", return_value=False):
        client.create_nodegroup.when.called_with(
            clusterName=cluster_name,
            nodegroupName=new_nodegroup_name,
            **dict(nodegroup_inputs)
        ).should.throw(
            expected_exception,
            CLUSTER_NOT_READY_MSG.format(
                exception_name=expected_exception.TYPE,
                method=MethodNames.CREATE_NODEGROUP,
                cluster_name=cluster_name,
            ),
        )

    len(
        client.list_nodegroups(clusterName=cluster_name)[ResponseAttribute.NODEGROUPS]
    ).should.equal(BatchCountSize.MEDIUM)


def test_delete_cluster_throws_exception_when_nodegroups_exist(nodegroup_setup):
    client, cluster_name, nodegroup_names = nodegroup_setup()
    expected_exception = ResourceInUseException

    client.delete_cluster.when.called_with(name=cluster_name).should.throw(
        expected_exception,
        CLUSTER_IN_USE_MSG.format(
            exception_name=expected_exception.TYPE, method=MethodNames.DELETE_CLUSTER,
        ),
    )
    len(client.list_clusters()[ResponseAttribute.CLUSTERS]).should.equal(
        BatchCountSize.SINGLE
    )


# If launch_template is specified, you can not specify instanceTypes, diskSize, or remoteAccess.
test_cases = [
    # Happy Paths
    (LAUNCH_TEMPLATE, None, None, None, TestResults.SUCCESS),
    (None, INSTANCE_TYPES, DISK_SIZE, REMOTE_ACCESS, TestResults.SUCCESS),
    (None, None, DISK_SIZE, REMOTE_ACCESS, TestResults.SUCCESS),
    (None, INSTANCE_TYPES, None, REMOTE_ACCESS, TestResults.SUCCESS),
    (None, INSTANCE_TYPES, DISK_SIZE, None, TestResults.SUCCESS),
    (None, INSTANCE_TYPES, None, None, TestResults.SUCCESS),
    (None, None, DISK_SIZE, None, TestResults.SUCCESS),
    (None, None, None, REMOTE_ACCESS, TestResults.SUCCESS),
    (None, None, None, None, TestResults.SUCCESS),
    # Unhappy Paths
    (LAUNCH_TEMPLATE, INSTANCE_TYPES, None, None, TestResults.FAILURE),
    (LAUNCH_TEMPLATE, None, DISK_SIZE, None, TestResults.FAILURE),
    (LAUNCH_TEMPLATE, None, None, REMOTE_ACCESS, TestResults.FAILURE),
    (LAUNCH_TEMPLATE, INSTANCE_TYPES, DISK_SIZE, None, TestResults.FAILURE),
    (LAUNCH_TEMPLATE, INSTANCE_TYPES, None, REMOTE_ACCESS, TestResults.FAILURE),
    (LAUNCH_TEMPLATE, None, DISK_SIZE, REMOTE_ACCESS, TestResults.FAILURE),
    (LAUNCH_TEMPLATE, INSTANCE_TYPES, DISK_SIZE, REMOTE_ACCESS, TestResults.FAILURE),
]


@pytest.mark.parametrize(
    "launchTemplate, instanceTypes, diskSize, remoteAccess, expected_result",
    test_cases,
)
def test_create_nodegroup_handles_launch_template_combinations(
    cluster_setup,
    launchTemplate,
    instanceTypes,
    diskSize,
    remoteAccess,
    expected_result,
):
    client, cluster_name, _ = cluster_setup()
    nodegroup_name = random_string()
    expected_exception = InvalidParameterException
    expected_message = None

    test_inputs = dict(
        deepcopy(
            # Required Constants
            NodegroupInputs.REQUIRED
            # Required Variables
            + [
                (ClusterAttribute.CLUSTER_NAME, cluster_name),
                (NodegroupAttribute.NAME, nodegroup_name),
            ]
            # Test Case Values
            + [_ for _ in [launchTemplate, instanceTypes, diskSize, remoteAccess] if _]
        )
    )

    if expected_result == TestResults.SUCCESS:
        result = client.create_nodegroup(**test_inputs)[ResponseAttribute.NODEGROUP]

        for key, expected_value in test_inputs.items():
            result[key].should.equal(expected_value)
    else:
        if launchTemplate and diskSize:
            expected_message = LAUNCH_TEMPLATE_WITH_DISK_SIZE_MSG.format(
                exception_name=expected_exception.TYPE,
                method=MethodNames.CREATE_NODEGROUP,
            )
        elif launchTemplate and remoteAccess:
            expected_message = LAUNCH_TEMPLATE_WITH_REMOTE_ACCESS_MSG.format(
                exception_name=expected_exception.TYPE,
                method=MethodNames.CREATE_NODEGROUP,
            )
        # Docs say this combination throws an exception but testing shows that
        # instanceTypes overrides the launchTemplate instance values instead.
        # Leaving here for easier correction if/when that gets fixed.
        elif launchTemplate and instanceTypes:
            pass

    if expected_message:
        client.create_nodegroup.when.called_with(**test_inputs).should.throw(
            expected_exception, expected_message
        )
