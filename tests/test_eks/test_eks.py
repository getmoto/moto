from __future__ import unicode_literals

from copy import deepcopy
from datetime import datetime

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
    NODEGROUP_NOT_FOUND_MSG,
    CLUSTER_EXISTS_MSG,
)
from moto.utilities.utils import random_string
from test_eks_constants import (
    BatchCountSize,
    ClusterAttributes,
    ClusterInputs,
    DISK_SIZE,
    INSTANCE_TYPES,
    LAUNCH_TEMPLATE,
    MethodNames,
    NodegroupAttributes,
    NodegroupInputs,
    PageCount,
    PARTITIONS,
    RegExTemplates,
    REMOTE_ACCESS,
    ResponseAttribute,
    REGION,
    SERVICE,
    TestResults,
)
from test_eks_utils import (
    attributes_to_test,
    generate_clusters,
    generate_nodegroups,
    is_valid_uri,
    random_names,
    region_matches_partition,
)

from moto import mock_eks
from moto.core import ACCOUNT_ID
from moto.core.utils import iso_8601_datetime_without_milliseconds
from moto.eks.responses import DEFAULT_MAX_RESULTS


@pytest.fixture(scope="function")
def ClusterBuilder():
    class ClusterTestDataFactory:
        def __init__(self, count, minimal):
            # Generate 'count' number of random Cluster objects.
            self.cluster_names = generate_clusters(client, count, minimal)

            # Get the name of the first generated Cluster.
            first_name = self.cluster_names[0]

            # Collect the output of describe_cluster() for the first Cluster.
            self.cluster_describe_output = client.describe_cluster(name=first_name)[
                ResponseAttribute.CLUSTER
            ]

            # Pick a random Cluster name from the list and a name guaranteed not to be on the list.
            (self.existing_cluster_name, self.nonexistent_cluster_name) = random_names(
                self.cluster_names
            )

            # Generate a list of the Cluster attributes to be tested when validating results.
            self.attributes_to_test = attributes_to_test(
                ClusterInputs, self.existing_cluster_name
            )

    def _execute(count=1, minimal=True):
        return client, ClusterTestDataFactory(count, minimal)

    mock_eks().start()
    client = boto3.client(SERVICE)
    yield _execute
    mock_eks().stop()


@pytest.fixture(scope="function")
def NodegroupBuilder(ClusterBuilder):
    class NodegroupTestDataFactory:
        def __init__(self, count, minimal):
            self.cluster_name = cluster.existing_cluster_name

            # Generate 'count' number of random Nodegroup objects.
            self.nodegroup_names = generate_nodegroups(
                client, self.cluster_name, count, minimal
            )

            # Get the name of the first generated Nodegroup.
            first_name = self.nodegroup_names[0]

            # Collect the output of describe_nodegroup() for the first Nodegroup.
            self.nodegroup_describe_output = client.describe_nodegroup(
                clusterName=self.cluster_name, nodegroupName=first_name
            )[ResponseAttribute.NODEGROUP]

            # Pick a random Nodegroup name from the list and a name guaranteed not to be on the list.
            (
                self.existing_nodegroup_name,
                self.nonexistent_nodegroup_name,
            ) = random_names(self.nodegroup_names)
            _, self.nonexistent_cluster_name = random_names(self.cluster_name)

            # Generate a list of the Nodegroup attributes to be tested when validating results.
            self.attributes_to_test = attributes_to_test(
                NodegroupInputs, self.existing_nodegroup_name
            )

    def _execute(count=1, minimal=True):
        return client, NodegroupTestDataFactory(count, minimal)

    client, cluster = ClusterBuilder()
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


def test_list_clusters_returns_sorted_cluster_names(ClusterBuilder):
    client, generated_test_data = ClusterBuilder(BatchCountSize.SMALL)

    result = client.list_clusters()[ResponseAttribute.CLUSTERS]

    result.should.equal(sorted(generated_test_data.cluster_names))
    len(result).should.equal(BatchCountSize.SMALL)


def test_list_clusters_returns_default_max_results(ClusterBuilder):
    client, generated_test_data = ClusterBuilder(BatchCountSize.LARGE)

    result = client.list_clusters()[ResponseAttribute.CLUSTERS]

    len(result).should.equal(DEFAULT_MAX_RESULTS)
    result.should.equal(
        (sorted(generated_test_data.cluster_names))[:DEFAULT_MAX_RESULTS]
    )


def test_list_clusters_returns_custom_max_results(ClusterBuilder):
    client, generated_test_data = ClusterBuilder(BatchCountSize.MEDIUM)

    result = client.list_clusters(maxResults=PageCount.LARGE)[
        ResponseAttribute.CLUSTERS
    ]

    len(result).should.equal(PageCount.LARGE)
    result.should.equal((sorted(generated_test_data.cluster_names))[: PageCount.LARGE])


def test_list_clusters_returns_second_page_results(ClusterBuilder):
    client, generated_test_data = ClusterBuilder(BatchCountSize.MEDIUM)
    token = client.list_clusters(maxResults=PageCount.LARGE)[
        ResponseAttribute.NEXT_TOKEN
    ]

    result = client.list_clusters(nextToken=token)[ResponseAttribute.CLUSTERS]

    len(result).should.equal(BatchCountSize.MEDIUM - PageCount.LARGE)
    result.should.equal((sorted(generated_test_data.cluster_names))[PageCount.LARGE :])


def test_list_clusters_returns_custom_second_page_results(ClusterBuilder):
    client, generated_test_data = ClusterBuilder(BatchCountSize.MEDIUM)
    token = client.list_clusters(maxResults=PageCount.LARGE)[
        ResponseAttribute.NEXT_TOKEN
    ]

    result = client.list_clusters(maxResults=PageCount.SMALL, nextToken=token)[
        ResponseAttribute.CLUSTERS
    ]

    len(result).should.equal(PageCount.SMALL)
    result.should.equal(
        (sorted(generated_test_data.cluster_names))[
            PageCount.LARGE : PageCount.LARGE + PageCount.SMALL
        ]
    )


def test_create_cluster_throws_exception_when_cluster_exists(ClusterBuilder):
    client, generated_test_data = ClusterBuilder(BatchCountSize.SMALL)
    expected_exception = ResourceInUseException
    expected_msg = CLUSTER_EXISTS_MSG.format(
        exception_name=expected_exception.TYPE,
        method=MethodNames.CREATE_CLUSTER,
        cluster_name=generated_test_data.existing_cluster_name,
    )

    client.create_cluster.when.called_with(
        name=generated_test_data.existing_cluster_name, **dict(ClusterInputs.REQUIRED)
    ).should.throw(expected_exception, expected_msg)
    len(client.list_clusters()[ResponseAttribute.CLUSTERS]).should.equal(
        BatchCountSize.SMALL
    )


def test_create_cluster_generates_valid_cluster_arn(ClusterBuilder):
    _, generated_test_data = ClusterBuilder()
    expected_arn_values = [
        PARTITIONS,
        REGION,
        ACCOUNT_ID,
        generated_test_data.cluster_names,
    ]

    all_arn_values_should_be_valid(
        expected_arn_values=expected_arn_values,
        pattern=RegExTemplates.CLUSTER_ARN,
        arn_under_test=generated_test_data.cluster_describe_output[
            ClusterAttributes.ARN
        ],
    )


@pytest.mark.freeze_time
def test_create_cluster_generates_valid_cluster_created_timestamp(ClusterBuilder):
    _, generated_test_data = ClusterBuilder()
    current_time = iso_8601_datetime_without_milliseconds(datetime.now())

    result_time = iso_8601_datetime_without_milliseconds(
        generated_test_data.cluster_describe_output[ClusterAttributes.CREATED_AT]
    )

    result_time.should.equal(current_time)


def test_create_cluster_generates_valid_cluster_endpoint(ClusterBuilder):
    _, generated_test_data = ClusterBuilder()

    result_endpoint = generated_test_data.cluster_describe_output[
        ClusterAttributes.ENDPOINT
    ]

    is_valid_uri(result_endpoint).should.be.true
    result_endpoint.should.contain(REGION)


def test_create_cluster_generates_valid_oidc_identity(ClusterBuilder):
    _, generated_test_data = ClusterBuilder()

    result_issuer = generated_test_data.cluster_describe_output[
        ClusterAttributes.IDENTITY
    ][ClusterAttributes.OIDC][ClusterAttributes.ISSUER]

    is_valid_uri(result_issuer).should.be.true
    result_issuer.should.contain(REGION)


def test_create_cluster_saves_provided_parameters(ClusterBuilder):
    _, generated_test_data = ClusterBuilder(minimal=False)

    for key, expected_value in generated_test_data.attributes_to_test:
        generated_test_data.cluster_describe_output[key].should.equal(expected_value)


def test_describe_cluster_throws_exception_when_cluster_not_found(ClusterBuilder):
    client, generated_test_data = ClusterBuilder(BatchCountSize.SMALL)
    expected_exception = ResourceNotFoundException
    expected_msg = CLUSTER_NOT_FOUND_MSG.format(
        exception_name=expected_exception.TYPE,
        method=MethodNames.DESCRIBE_CLUSTER,
        cluster_name=generated_test_data.nonexistent_cluster_name,
    )

    client.describe_cluster.when.called_with(
        name=generated_test_data.nonexistent_cluster_name
    ).should.throw(expected_exception, expected_msg)


def test_delete_cluster_returns_deleted_cluster(ClusterBuilder):
    client, generated_test_data = ClusterBuilder(BatchCountSize.SMALL, False)

    result = client.delete_cluster(name=generated_test_data.existing_cluster_name)[
        ResponseAttribute.CLUSTER
    ]

    for key, expected_value in generated_test_data.attributes_to_test:
        result[key].should.equal(expected_value)


def test_delete_cluster_removes_deleted_cluster(ClusterBuilder):
    client, generated_test_data = ClusterBuilder(BatchCountSize.SMALL, False)

    client.delete_cluster(name=generated_test_data.existing_cluster_name)
    result_cluster_list = client.list_clusters()[ResponseAttribute.CLUSTERS]

    len(result_cluster_list).should.equal(BatchCountSize.SMALL - 1)
    result_cluster_list.should_not.contain(generated_test_data.existing_cluster_name)


def test_delete_cluster_throws_exception_when_cluster_not_found(ClusterBuilder):
    client, generated_test_data = ClusterBuilder(BatchCountSize.SMALL)
    expected_exception = ResourceNotFoundException
    expected_msg = CLUSTER_NOT_FOUND_MSG.format(
        exception_name=expected_exception.TYPE,
        method=MethodNames.DELETE_CLUSTER,
        cluster_name=generated_test_data.nonexistent_cluster_name,
    )

    client.delete_cluster.when.called_with(
        name=generated_test_data.nonexistent_cluster_name
    ).should.throw(expected_exception, expected_msg)
    len(client.list_clusters()[ResponseAttribute.CLUSTERS]).should.equal(
        BatchCountSize.SMALL
    )


def test_list_nodegroups_returns_empty_by_default(ClusterBuilder):
    client, generated_test_data = ClusterBuilder()

    result = client.list_nodegroups(
        clusterName=generated_test_data.existing_cluster_name
    )[ResponseAttribute.NODEGROUPS]
    result.should.be.empty


def test_list_nodegroups_returns_sorted_nodegroup_names(NodegroupBuilder):
    client, generated_test_data = NodegroupBuilder(BatchCountSize.SMALL)

    result = client.list_nodegroups(clusterName=generated_test_data.cluster_name)[
        ResponseAttribute.NODEGROUPS
    ]

    result.should.equal(sorted(generated_test_data.nodegroup_names))
    len(result).should.equal(BatchCountSize.SMALL)


def test_list_nodegroups_returns_default_max_results(NodegroupBuilder):
    client, generated_test_data = NodegroupBuilder(BatchCountSize.LARGE)

    result = client.list_nodegroups(clusterName=generated_test_data.cluster_name)[
        ResponseAttribute.NODEGROUPS
    ]

    len(result).should.equal(DEFAULT_MAX_RESULTS)
    result.should.equal(
        (sorted(generated_test_data.nodegroup_names))[:DEFAULT_MAX_RESULTS]
    )


def test_list_nodegroups_returns_custom_max_results(NodegroupBuilder):
    client, generated_test_data = NodegroupBuilder(BatchCountSize.LARGE)

    result = client.list_nodegroups(
        clusterName=generated_test_data.cluster_name, maxResults=PageCount.LARGE
    )[ResponseAttribute.NODEGROUPS]

    len(result).should.equal(PageCount.LARGE)
    result.should.equal(
        (sorted(generated_test_data.nodegroup_names))[: PageCount.LARGE]
    )


def test_list_nodegroups_returns_second_page_results(NodegroupBuilder):
    client, generated_test_data = NodegroupBuilder(BatchCountSize.MEDIUM)
    token = client.list_nodegroups(
        clusterName=generated_test_data.cluster_name, maxResults=PageCount.LARGE
    )[ResponseAttribute.NEXT_TOKEN]

    result = client.list_nodegroups(
        clusterName=generated_test_data.cluster_name, nextToken=token
    )[ResponseAttribute.NODEGROUPS]

    len(result).should.equal(BatchCountSize.MEDIUM - PageCount.LARGE)
    result.should.equal(
        (sorted(generated_test_data.nodegroup_names))[PageCount.LARGE :]
    )


def test_list_nodegroups_returns_custom_second_page_results(NodegroupBuilder):
    client, generated_test_data = NodegroupBuilder(BatchCountSize.MEDIUM)
    token = client.list_nodegroups(
        clusterName=generated_test_data.cluster_name, maxResults=PageCount.LARGE
    )[ResponseAttribute.NEXT_TOKEN]

    result = client.list_nodegroups(
        clusterName=generated_test_data.cluster_name,
        maxResults=PageCount.SMALL,
        nextToken=token,
    )[ResponseAttribute.NODEGROUPS]

    len(result).should.equal(PageCount.SMALL)
    result.should.equal(
        (sorted(generated_test_data.nodegroup_names))[
            PageCount.LARGE : PageCount.LARGE + PageCount.SMALL
        ]
    )


@mock_eks
def test_create_nodegroup_throws_exception_when_cluster_not_found():
    client = boto3.client(SERVICE)
    non_existent_cluster_name = random_string()
    expected_exception = ResourceNotFoundException
    expected_msg = CLUSTER_NOT_FOUND_MSG.format(
        exception_name=expected_exception.TYPE,
        method=MethodNames.CREATE_NODEGROUP,
        cluster_name=non_existent_cluster_name,
    )

    client.create_nodegroup.when.called_with(
        clusterName=non_existent_cluster_name,
        nodegroupName=random_string(),
        **dict(NodegroupInputs.REQUIRED)
    ).should.throw(expected_exception, expected_msg)


def test_create_nodegroup_throws_exception_when_nodegroup_already_exists(
    NodegroupBuilder,
):
    client, generated_test_data = NodegroupBuilder(BatchCountSize.SMALL)
    expected_exception = ResourceInUseException
    expected_msg = NODEGROUP_EXISTS_MSG.format(
        exception_name=expected_exception.TYPE,
        method=MethodNames.CREATE_NODEGROUP,
        cluster_name=generated_test_data.cluster_name,
        nodegroup_name=generated_test_data.existing_nodegroup_name,
    )

    client.create_nodegroup.when.called_with(
        clusterName=generated_test_data.cluster_name,
        nodegroupName=generated_test_data.existing_nodegroup_name,
        **dict(NodegroupInputs.REQUIRED)
    ).should.throw(expected_exception, expected_msg)
    len(
        client.list_nodegroups(clusterName=generated_test_data.cluster_name)[
            ResponseAttribute.NODEGROUPS
        ]
    ).should.equal(BatchCountSize.SMALL)


def test_create_nodegroup_throws_exception_when_cluster_not_active(
    NodegroupBuilder, monkeypatch
):
    client, generated_test_data = NodegroupBuilder(BatchCountSize.SMALL)
    expected_exception = InvalidRequestException
    expected_msg = CLUSTER_NOT_READY_MSG.format(
        exception_name=expected_exception.TYPE,
        method=MethodNames.CREATE_NODEGROUP,
        cluster_name=generated_test_data.cluster_name,
    )

    with mock.patch("moto.eks.models.Cluster.isActive", return_value=False):
        client.create_nodegroup.when.called_with(
            clusterName=generated_test_data.cluster_name,
            nodegroupName=random_string(),
            **dict(NodegroupInputs.REQUIRED)
        ).should.throw(expected_exception, expected_msg)

    len(
        client.list_nodegroups(clusterName=generated_test_data.cluster_name)[
            ResponseAttribute.NODEGROUPS
        ]
    ).should.equal(BatchCountSize.SMALL)


def test_create_nodegroup_generates_valid_nodegroup_arn(NodegroupBuilder):
    _, generated_test_data = NodegroupBuilder()
    expected_arn_values = [
        PARTITIONS,
        REGION,
        ACCOUNT_ID,
        generated_test_data.cluster_name,
        generated_test_data.nodegroup_names,
        None,
    ]

    all_arn_values_should_be_valid(
        expected_arn_values=expected_arn_values,
        pattern=RegExTemplates.NODEGROUP_ARN,
        arn_under_test=generated_test_data.nodegroup_describe_output[
            NodegroupAttributes.ARN
        ],
    )


@pytest.mark.freeze_time
def test_create_nodegroup_generates_valid_nodegroup_created_timestamp(NodegroupBuilder):
    _, generated_test_data = NodegroupBuilder()
    current_time = iso_8601_datetime_without_milliseconds(datetime.now())

    result_time = iso_8601_datetime_without_milliseconds(
        generated_test_data.nodegroup_describe_output[NodegroupAttributes.CREATED_AT]
    )

    result_time.should.equal(current_time)


@pytest.mark.freeze_time
def test_create_nodegroup_generates_valid_nodegroup_modified_timestamp(
    NodegroupBuilder,
):
    client, generated_test_data = NodegroupBuilder()
    current_time = iso_8601_datetime_without_milliseconds(datetime.now())

    result_time = iso_8601_datetime_without_milliseconds(
        generated_test_data.nodegroup_describe_output[NodegroupAttributes.MODIFIED_AT]
    )

    result_time.should.equal(current_time)


def test_create_nodegroup_generates_valid_autoscaling_group_name(NodegroupBuilder):
    _, generated_test_data = NodegroupBuilder()
    result_resources = generated_test_data.nodegroup_describe_output[
        NodegroupAttributes.RESOURCES
    ]

    result_asg_name = result_resources[NodegroupAttributes.AUTOSCALING_GROUPS][0][
        NodegroupAttributes.NAME
    ]

    RegExTemplates.NODEGROUP_ASG_NAME_PATTERN.match(result_asg_name).should.be.true


def test_create_nodegroup_generates_valid_security_group_name(NodegroupBuilder):
    _, generated_test_data = NodegroupBuilder()
    result_resources = generated_test_data.nodegroup_describe_output[
        NodegroupAttributes.RESOURCES
    ]

    result_security_group = result_resources[NodegroupAttributes.REMOTE_ACCESS_SG]

    RegExTemplates.NODEGROUP_SECURITY_GROUP_NAME_PATTERN.match(
        result_security_group
    ).should.be.true


def test_create_nodegroup_saves_provided_parameters(NodegroupBuilder):
    _, generated_test_data = NodegroupBuilder(minimal=False)

    for key, expected_value in generated_test_data.attributes_to_test:
        generated_test_data.nodegroup_describe_output[key].should.equal(expected_value)


def test_describe_nodegroup_throws_exception_when_cluster_not_found(NodegroupBuilder):
    client, generated_test_data = NodegroupBuilder()
    expected_exception = ResourceNotFoundException
    expected_msg = CLUSTER_NOT_FOUND_MSG.format(
        exception_name=expected_exception.TYPE,
        method=MethodNames.DESCRIBE_NODEGROUP,
        cluster_name=generated_test_data.nonexistent_cluster_name,
    )

    client.describe_nodegroup.when.called_with(
        clusterName=generated_test_data.nonexistent_cluster_name,
        nodegroupName=generated_test_data.existing_nodegroup_name,
    ).should.throw(expected_exception, expected_msg)


def test_describe_nodegroup_throws_exception_when_nodegroup_not_found(NodegroupBuilder):
    client, generated_test_data = NodegroupBuilder()
    expected_exception = ResourceNotFoundException
    expected_msg = NODEGROUP_NOT_FOUND_MSG.format(
        exception_name=expected_exception.TYPE,
        method=MethodNames.DESCRIBE_NODEGROUP,
        nodegroup_name=generated_test_data.nonexistent_nodegroup_name,
    )

    client.describe_nodegroup.when.called_with(
        clusterName=generated_test_data.cluster_name,
        nodegroupName=generated_test_data.nonexistent_nodegroup_name,
    ).should.throw(expected_exception, expected_msg)


def test_delete_cluster_throws_exception_when_nodegroups_exist(NodegroupBuilder):
    client, generated_test_data = NodegroupBuilder()
    expected_exception = ResourceInUseException
    expected_msg = CLUSTER_IN_USE_MSG.format(
        exception_name=expected_exception.TYPE, method=MethodNames.DELETE_CLUSTER,
    )

    client.delete_cluster.when.called_with(
        name=generated_test_data.cluster_name
    ).should.throw(expected_exception, expected_msg)
    len(client.list_clusters()[ResponseAttribute.CLUSTERS]).should.equal(
        BatchCountSize.SINGLE
    )


def test_delete_nodegroup_removes_deleted_nodegroup(NodegroupBuilder):
    client, generated_test_data = NodegroupBuilder(BatchCountSize.SMALL)

    client.delete_nodegroup(
        clusterName=generated_test_data.cluster_name,
        nodegroupName=generated_test_data.existing_nodegroup_name,
    )
    result_nodegroup_list = client.list_nodegroups(
        clusterName=generated_test_data.cluster_name
    )[ResponseAttribute.NODEGROUPS]

    len(result_nodegroup_list).should.equal(BatchCountSize.SMALL - 1)
    result_nodegroup_list.should_not.contain(
        generated_test_data.existing_nodegroup_name
    )


def test_delete_nodegroup_returns_deleted_nodegroup(NodegroupBuilder):
    client, generated_test_data = NodegroupBuilder(BatchCountSize.SMALL, False)

    result = client.delete_nodegroup(
        clusterName=generated_test_data.cluster_name,
        nodegroupName=generated_test_data.existing_nodegroup_name,
    )[ResponseAttribute.NODEGROUP]

    for key, expected_value in generated_test_data.attributes_to_test:
        result[key].should.equal(expected_value)


def test_delete_nodegroup_throws_exception_when_cluster_not_found(NodegroupBuilder):
    client, generated_test_data = NodegroupBuilder()
    expected_exception = ResourceNotFoundException
    expected_msg = CLUSTER_NOT_FOUND_MSG.format(
        exception_name=expected_exception.TYPE,
        method=MethodNames.DELETE_NODEGROUP,
        cluster_name=generated_test_data.nonexistent_cluster_name,
    )

    client.delete_nodegroup.when.called_with(
        clusterName=generated_test_data.nonexistent_cluster_name,
        nodegroupName=generated_test_data.existing_nodegroup_name,
    ).should.throw(expected_exception, expected_msg)


def test_delete_nodegroup_throws_exception_when_nodegroup_not_found(NodegroupBuilder):
    client, generated_test_data = NodegroupBuilder()
    expected_exception = ResourceNotFoundException
    expected_msg = NODEGROUP_NOT_FOUND_MSG.format(
        exception_name=expected_exception.TYPE,
        method=MethodNames.DELETE_NODEGROUP,
        nodegroup_name=generated_test_data.nonexistent_nodegroup_name,
    )

    client.delete_nodegroup.when.called_with(
        clusterName=generated_test_data.cluster_name,
        nodegroupName=generated_test_data.nonexistent_nodegroup_name,
    ).should.throw(expected_exception, expected_msg)


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
    ClusterBuilder,
    launchTemplate,
    instanceTypes,
    diskSize,
    remoteAccess,
    expected_result,
):
    client, generated_test_data = ClusterBuilder()
    nodegroup_name = random_string()
    expected_exception = InvalidParameterException
    expected_message = None

    test_inputs = dict(
        deepcopy(
            # Required Constants
            NodegroupInputs.REQUIRED
            # Required Variables
            + [
                (
                    ClusterAttributes.CLUSTER_NAME,
                    generated_test_data.existing_cluster_name,
                ),
                (NodegroupAttributes.NODEGROUP_NAME, nodegroup_name),
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


def all_arn_values_should_be_valid(expected_arn_values, pattern, arn_under_test):
    """
    Applies regex `pattern` to `arn_under_test` and asserts
    that each group matches the provided expected value.
    A list entry of None in the 'expected_arn_values' will
    assert that the value exists but not match a specific value.
    """
    findall = pattern.findall(arn_under_test)[0]
    # findall() returns a list of matches from right to left so it must be reversed
    # in order to match the logical order of the 'expected_arn_values' list.
    for value in reversed(findall):
        expected_value = expected_arn_values.pop()
        if expected_value:
            value.should.be.within(expected_value)
        else:
            value.should.be.truthy
    region_matches_partition(findall[1], findall[0]).should.be.true
