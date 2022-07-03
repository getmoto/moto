from copy import deepcopy
from unittest import SkipTest

import boto3
import mock
import pytest
import sure  # noqa # pylint: disable=unused-import
from botocore.exceptions import ClientError
from freezegun import freeze_time

from moto import mock_eks, settings
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
from moto.core.utils import iso_8601_datetime_without_milliseconds
from moto.eks.exceptions import (
    InvalidParameterException,
    InvalidRequestException,
    ResourceInUseException,
    ResourceNotFoundException,
)
from moto.eks.models import (
    CLUSTER_EXISTS_MSG,
    CLUSTER_IN_USE_MSG,
    CLUSTER_NOT_FOUND_MSG,
    CLUSTER_NOT_READY_MSG,
    FARGATE_PROFILE_EXISTS_MSG,
    FARGATE_PROFILE_NEEDS_SELECTOR_MSG,
    FARGATE_PROFILE_NOT_FOUND_MSG,
    FARGATE_PROFILE_SELECTOR_NEEDS_NAMESPACE,
    FARGATE_PROFILE_TOO_MANY_LABELS,
    LAUNCH_TEMPLATE_WITH_DISK_SIZE_MSG,
    LAUNCH_TEMPLATE_WITH_REMOTE_ACCESS_MSG,
    NODEGROUP_EXISTS_MSG,
    NODEGROUP_NOT_FOUND_MSG,
)
from moto.eks.responses import DEFAULT_MAX_RESULTS
from moto.utilities.utils import random_string

from .test_eks_constants import (
    BatchCountSize,
    ClusterAttributes,
    ClusterInputs,
    DEFAULT_NAMESPACE,
    DISK_SIZE,
    ErrorAttributes,
    FargateProfileAttributes,
    FargateProfileInputs,
    FROZEN_TIME,
    INSTANCE_TYPES,
    LAUNCH_TEMPLATE,
    MAX_FARGATE_LABELS,
    NodegroupAttributes,
    NodegroupInputs,
    PageCount,
    PARTITIONS,
    POD_EXECUTION_ROLE_ARN,
    PossibleTestResults,
    RegExTemplates,
    REGION,
    REMOTE_ACCESS,
    ResponseAttributes,
    SERVICE,
)
from .test_eks_utils import (
    attributes_to_test,
    generate_clusters,
    generate_dict,
    generate_fargate_profiles,
    generate_nodegroups,
    is_valid_uri,
    random_names,
    region_matches_partition,
)


@pytest.fixture(scope="function")
def ClusterBuilder():
    class ClusterTestDataFactory:
        def __init__(self, client, count, minimal):
            # Generate 'count' number of random Cluster objects.
            self.cluster_names = generate_clusters(client, count, minimal)

            # Get the name of the first generated Cluster.
            first_name = self.cluster_names[0]

            # Collect the output of describe_cluster() for the first Cluster.
            self.cluster_describe_output = client.describe_cluster(name=first_name)[
                ResponseAttributes.CLUSTER
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
        client = boto3.client(SERVICE, region_name=REGION)
        return client, ClusterTestDataFactory(client, count, minimal)

    yield _execute


@pytest.fixture(scope="function")
def FargateProfileBuilder(ClusterBuilder):
    class FargateProfileTestDataFactory:
        def __init__(self, client, cluster, count, minimal):
            self.cluster_name = cluster.existing_cluster_name

            # Generate 'count' number of random FargateProfile objects.
            self.fargate_profile_names = generate_fargate_profiles(
                client, self.cluster_name, count, minimal
            )

            # Get the name of the first generated profile.
            first_name = self.fargate_profile_names[0]

            # Collect the output of describe_fargate_profiles() for the first profile.
            self.fargate_describe_output = client.describe_fargate_profile(
                clusterName=self.cluster_name, fargateProfileName=first_name
            )[ResponseAttributes.FARGATE_PROFILE]

            # Pick a random profile name from the list and a name guaranteed not to be on the list.
            (
                self.existing_fargate_profile_name,
                self.nonexistent_fargate_profile_name,
            ) = random_names(self.fargate_profile_names)
            _, self.nonexistent_cluster_name = random_names(self.cluster_name)

            # Generate a list of the Fargate Profile attributes to be tested when validating results.
            self.attributes_to_test = attributes_to_test(
                FargateProfileInputs, self.existing_fargate_profile_name
            )

    def _execute(count=1, minimal=True):
        client, cluster = ClusterBuilder()
        return client, FargateProfileTestDataFactory(client, cluster, count, minimal)

    return _execute


@pytest.fixture(scope="function")
def NodegroupBuilder(ClusterBuilder):
    class NodegroupTestDataFactory:
        def __init__(self, client, cluster, count, minimal):
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
            )[ResponseAttributes.NODEGROUP]

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
        client, cluster = ClusterBuilder()
        return client, NodegroupTestDataFactory(client, cluster, count, minimal)

    return _execute


###
# This specific test does not use the fixture since
# it is intended to verify that there are no clusters
# in the list at initialization, which means the mock
# decorator must be used manually in this one case.
###


@mock_eks
def test_list_clusters_returns_empty_by_default():
    client = boto3.client(SERVICE, region_name=REGION)

    result = client.list_clusters()[ResponseAttributes.CLUSTERS]

    result.should.equal([])


@mock_eks
def test_list_tags_returns_empty_by_default(ClusterBuilder):
    client, generated_test_data = ClusterBuilder(BatchCountSize.SINGLE)
    cluster_arn = generated_test_data.cluster_describe_output[ClusterAttributes.ARN]
    result = client.list_tags_for_resource(resourceArn=cluster_arn)
    assert len(result["tags"]) == 0


@mock_eks
def test_list_tags_returns_all(ClusterBuilder):
    client, generated_test_data = ClusterBuilder(BatchCountSize.SINGLE)
    cluster_arn = generated_test_data.cluster_describe_output[ClusterAttributes.ARN]
    client.tag_resource(resourceArn=cluster_arn, tags={"key1": "val1", "key2": "val2"})
    result = client.list_tags_for_resource(resourceArn=cluster_arn)
    assert len(result["tags"]) == 2
    result.should.have.key("tags").equals({"key1": "val1", "key2": "val2"})


@mock_eks
def test_list_tags_returns_all_after_delete(ClusterBuilder):
    client, generated_test_data = ClusterBuilder(BatchCountSize.SINGLE)
    cluster_arn = generated_test_data.cluster_describe_output[ClusterAttributes.ARN]
    client.tag_resource(resourceArn=cluster_arn, tags={"key1": "val1", "key2": "val2"})
    client.untag_resource(resourceArn=cluster_arn, tagKeys=["key1"])
    result = client.list_tags_for_resource(resourceArn=cluster_arn)
    assert len(result["tags"]) == 1
    result.should.have.key("tags").equals({"key2": "val2"})


@mock_eks
def test_list_clusters_returns_sorted_cluster_names(ClusterBuilder):
    client, generated_test_data = ClusterBuilder(BatchCountSize.SMALL)
    expected_result = sorted(generated_test_data.cluster_names)

    result = client.list_clusters()[ResponseAttributes.CLUSTERS]

    assert_result_matches_expected_list(result, expected_result, BatchCountSize.SMALL)


@mock_eks
def test_list_clusters_returns_default_max_results(ClusterBuilder):
    client, generated_test_data = ClusterBuilder(BatchCountSize.LARGE)
    expected_len = DEFAULT_MAX_RESULTS
    expected_result = (sorted(generated_test_data.cluster_names))[:expected_len]

    result = client.list_clusters()[ResponseAttributes.CLUSTERS]

    assert_result_matches_expected_list(result, expected_result, expected_len)


@mock_eks
def test_list_clusters_returns_custom_max_results(ClusterBuilder):
    client, generated_test_data = ClusterBuilder(BatchCountSize.MEDIUM)
    expected_len = PageCount.LARGE
    expected_result = (sorted(generated_test_data.cluster_names))[:expected_len]

    result = client.list_clusters(maxResults=expected_len)[ResponseAttributes.CLUSTERS]

    assert_result_matches_expected_list(result, expected_result, expected_len)


@mock_eks
def test_list_clusters_returns_second_page_results(ClusterBuilder):
    client, generated_test_data = ClusterBuilder(BatchCountSize.MEDIUM)
    page1_len = PageCount.LARGE
    expected_len = BatchCountSize.MEDIUM - page1_len
    expected_result = (sorted(generated_test_data.cluster_names))[page1_len:]
    token = client.list_clusters(maxResults=page1_len)[ResponseAttributes.NEXT_TOKEN]

    result = client.list_clusters(nextToken=token)[ResponseAttributes.CLUSTERS]

    assert_result_matches_expected_list(result, expected_result, expected_len)


@mock_eks
def test_list_clusters_returns_custom_second_page_results(ClusterBuilder):
    client, generated_test_data = ClusterBuilder(BatchCountSize.MEDIUM)
    page1_len = PageCount.LARGE
    expected_len = PageCount.SMALL
    expected_result = (sorted(generated_test_data.cluster_names))[
        page1_len : page1_len + expected_len
    ]
    token = client.list_clusters(maxResults=page1_len)[ResponseAttributes.NEXT_TOKEN]

    result = client.list_clusters(maxResults=expected_len, nextToken=token)[
        ResponseAttributes.CLUSTERS
    ]

    assert_result_matches_expected_list(result, expected_result, expected_len)


@mock_eks
def test_create_cluster_throws_exception_when_cluster_exists(ClusterBuilder):
    client, generated_test_data = ClusterBuilder(BatchCountSize.SMALL)
    expected_exception = ResourceInUseException
    expected_msg = CLUSTER_EXISTS_MSG.format(
        clusterName=generated_test_data.existing_cluster_name
    )

    with pytest.raises(ClientError) as raised_exception:
        client.create_cluster(
            name=generated_test_data.existing_cluster_name,
            **dict(ClusterInputs.REQUIRED)
        )
    count_clusters_after_test = len(client.list_clusters()[ResponseAttributes.CLUSTERS])

    count_clusters_after_test.should.equal(BatchCountSize.SMALL)
    assert_expected_exception(raised_exception, expected_exception, expected_msg)


@mock_eks
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


@freeze_time(FROZEN_TIME)
@mock_eks
def test_create_cluster_generates_valid_cluster_created_timestamp(ClusterBuilder):
    _, generated_test_data = ClusterBuilder()

    result_time = iso_8601_datetime_without_milliseconds(
        generated_test_data.cluster_describe_output[ClusterAttributes.CREATED_AT]
    )

    if settings.TEST_SERVER_MODE:
        RegExTemplates.ISO8601_FORMAT.match(result_time).should.be.true
    else:
        result_time.should.equal(FROZEN_TIME)


@mock_eks
def test_create_cluster_generates_valid_cluster_endpoint(ClusterBuilder):
    _, generated_test_data = ClusterBuilder()

    result_endpoint = generated_test_data.cluster_describe_output[
        ClusterAttributes.ENDPOINT
    ]

    is_valid_uri(result_endpoint).should.be.true
    result_endpoint.should.contain(REGION)


@mock_eks
def test_create_cluster_generates_valid_oidc_identity(ClusterBuilder):
    _, generated_test_data = ClusterBuilder()

    result_issuer = generated_test_data.cluster_describe_output[
        ClusterAttributes.IDENTITY
    ][ClusterAttributes.OIDC][ClusterAttributes.ISSUER]

    is_valid_uri(result_issuer).should.be.true
    result_issuer.should.contain(REGION)


@mock_eks
def test_create_cluster_saves_provided_parameters(ClusterBuilder):
    _, generated_test_data = ClusterBuilder(minimal=False)

    for key, expected_value in generated_test_data.attributes_to_test:
        generated_test_data.cluster_describe_output[key].should.equal(expected_value)


@mock_eks
def test_describe_cluster_throws_exception_when_cluster_not_found(ClusterBuilder):
    client, generated_test_data = ClusterBuilder(BatchCountSize.SMALL)
    expected_exception = ResourceNotFoundException
    expected_msg = CLUSTER_NOT_FOUND_MSG.format(
        clusterName=generated_test_data.nonexistent_cluster_name
    )

    with pytest.raises(ClientError) as raised_exception:
        client.describe_cluster(name=generated_test_data.nonexistent_cluster_name)

    assert_expected_exception(raised_exception, expected_exception, expected_msg)


@mock_eks
def test_delete_cluster_returns_deleted_cluster(ClusterBuilder):
    client, generated_test_data = ClusterBuilder(BatchCountSize.SMALL, False)

    result = client.delete_cluster(name=generated_test_data.existing_cluster_name)[
        ResponseAttributes.CLUSTER
    ]

    for key, expected_value in generated_test_data.attributes_to_test:
        result[key].should.equal(expected_value)


@mock_eks
def test_delete_cluster_removes_deleted_cluster(ClusterBuilder):
    client, generated_test_data = ClusterBuilder(BatchCountSize.SMALL, False)

    client.delete_cluster(name=generated_test_data.existing_cluster_name)
    result_cluster_list = client.list_clusters()[ResponseAttributes.CLUSTERS]

    len(result_cluster_list).should.equal(BatchCountSize.SMALL - 1)
    result_cluster_list.should_not.contain(generated_test_data.existing_cluster_name)


@mock_eks
def test_delete_cluster_throws_exception_when_cluster_not_found(ClusterBuilder):
    client, generated_test_data = ClusterBuilder(BatchCountSize.SMALL)
    expected_exception = ResourceNotFoundException
    expected_msg = CLUSTER_NOT_FOUND_MSG.format(
        clusterName=generated_test_data.nonexistent_cluster_name
    )

    with pytest.raises(ClientError) as raised_exception:
        client.delete_cluster(name=generated_test_data.nonexistent_cluster_name)
    count_clusters_after_test = len(client.list_clusters()[ResponseAttributes.CLUSTERS])

    count_clusters_after_test.should.equal(BatchCountSize.SMALL)
    assert_expected_exception(raised_exception, expected_exception, expected_msg)


@mock_eks
def test_list_nodegroups_returns_empty_by_default(ClusterBuilder):
    client, generated_test_data = ClusterBuilder()

    result = client.list_nodegroups(
        clusterName=generated_test_data.existing_cluster_name
    )[ResponseAttributes.NODEGROUPS]

    result.should.equal([])


@mock_eks
def test_list_nodegroups_returns_sorted_nodegroup_names(NodegroupBuilder):
    client, generated_test_data = NodegroupBuilder(BatchCountSize.SMALL)
    expected_result = sorted(generated_test_data.nodegroup_names)

    result = client.list_nodegroups(clusterName=generated_test_data.cluster_name)[
        ResponseAttributes.NODEGROUPS
    ]

    assert_result_matches_expected_list(result, expected_result, BatchCountSize.SMALL)


@mock_eks
def test_list_nodegroups_returns_default_max_results(NodegroupBuilder):
    client, generated_test_data = NodegroupBuilder(BatchCountSize.LARGE)
    expected_len = DEFAULT_MAX_RESULTS
    expected_result = (sorted(generated_test_data.nodegroup_names))[:expected_len]

    result = client.list_nodegroups(clusterName=generated_test_data.cluster_name)[
        ResponseAttributes.NODEGROUPS
    ]

    assert_result_matches_expected_list(result, expected_result, expected_len)


@mock_eks
def test_list_nodegroups_returns_custom_max_results(NodegroupBuilder):
    client, generated_test_data = NodegroupBuilder(BatchCountSize.LARGE)
    expected_len = BatchCountSize.LARGE
    expected_result = (sorted(generated_test_data.nodegroup_names))[:expected_len]

    result = client.list_nodegroups(
        clusterName=generated_test_data.cluster_name, maxResults=expected_len
    )[ResponseAttributes.NODEGROUPS]

    assert_result_matches_expected_list(result, expected_result, expected_len)


@mock_eks
def test_list_nodegroups_returns_second_page_results(NodegroupBuilder):
    client, generated_test_data = NodegroupBuilder(BatchCountSize.MEDIUM)
    page1_len = PageCount.LARGE
    expected_len = BatchCountSize.MEDIUM - page1_len
    expected_result = (sorted(generated_test_data.nodegroup_names))[page1_len:]
    token = client.list_nodegroups(
        clusterName=generated_test_data.cluster_name, maxResults=page1_len
    )[ResponseAttributes.NEXT_TOKEN]

    result = client.list_nodegroups(
        clusterName=generated_test_data.cluster_name, nextToken=token
    )[ResponseAttributes.NODEGROUPS]

    assert_result_matches_expected_list(result, expected_result, expected_len)


@mock_eks
def test_list_nodegroups_returns_custom_second_page_results(NodegroupBuilder):
    client, generated_test_data = NodegroupBuilder(BatchCountSize.MEDIUM)
    page1_len = PageCount.LARGE
    expected_len = PageCount.SMALL
    expected_result = (sorted(generated_test_data.nodegroup_names))[
        page1_len : page1_len + expected_len
    ]
    token = client.list_nodegroups(
        clusterName=generated_test_data.cluster_name, maxResults=page1_len
    )[ResponseAttributes.NEXT_TOKEN]

    result = client.list_nodegroups(
        clusterName=generated_test_data.cluster_name,
        maxResults=expected_len,
        nextToken=token,
    )[ResponseAttributes.NODEGROUPS]

    assert_result_matches_expected_list(result, expected_result, expected_len)


@mock_eks
def test_create_nodegroup_throws_exception_when_cluster_not_found():
    client = boto3.client(SERVICE, region_name=REGION)
    non_existent_cluster_name = random_string()
    expected_exception = ResourceNotFoundException
    expected_msg = CLUSTER_NOT_FOUND_MSG.format(clusterName=non_existent_cluster_name)

    with pytest.raises(ClientError) as raised_exception:
        client.create_nodegroup(
            clusterName=non_existent_cluster_name,
            nodegroupName=random_string(),
            **dict(NodegroupInputs.REQUIRED)
        )

    assert_expected_exception(raised_exception, expected_exception, expected_msg)


@mock_eks
def test_create_nodegroup_throws_exception_when_nodegroup_already_exists(
    NodegroupBuilder,
):
    client, generated_test_data = NodegroupBuilder(BatchCountSize.SMALL)
    expected_exception = ResourceInUseException
    expected_msg = NODEGROUP_EXISTS_MSG.format(
        clusterName=generated_test_data.cluster_name,
        nodegroupName=generated_test_data.existing_nodegroup_name,
    )

    with pytest.raises(ClientError) as raised_exception:
        client.create_nodegroup(
            clusterName=generated_test_data.cluster_name,
            nodegroupName=generated_test_data.existing_nodegroup_name,
            **dict(NodegroupInputs.REQUIRED)
        )
    count_nodegroups_after_test = len(
        client.list_nodegroups(clusterName=generated_test_data.cluster_name)[
            ResponseAttributes.NODEGROUPS
        ]
    )

    count_nodegroups_after_test.should.equal(BatchCountSize.SMALL)
    assert_expected_exception(raised_exception, expected_exception, expected_msg)


@mock_eks
def test_create_nodegroup_throws_exception_when_cluster_not_active(NodegroupBuilder):
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Cant patch Cluster attributes in server mode.")
    client, generated_test_data = NodegroupBuilder(BatchCountSize.SMALL)
    expected_exception = InvalidRequestException
    expected_msg = CLUSTER_NOT_READY_MSG.format(
        clusterName=generated_test_data.cluster_name
    )

    with mock.patch("moto.eks.models.Cluster.isActive", return_value=False):
        with pytest.raises(ClientError) as raised_exception:
            client.create_nodegroup(
                clusterName=generated_test_data.cluster_name,
                nodegroupName=random_string(),
                **dict(NodegroupInputs.REQUIRED)
            )
    count_nodegroups_after_test = len(
        client.list_nodegroups(clusterName=generated_test_data.cluster_name)[
            ResponseAttributes.NODEGROUPS
        ]
    )

    count_nodegroups_after_test.should.equal(BatchCountSize.SMALL)
    assert_expected_exception(raised_exception, expected_exception, expected_msg)


@mock_eks
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


@freeze_time(FROZEN_TIME)
@mock_eks
def test_create_nodegroup_generates_valid_nodegroup_created_timestamp(NodegroupBuilder):
    _, generated_test_data = NodegroupBuilder()

    result_time = iso_8601_datetime_without_milliseconds(
        generated_test_data.nodegroup_describe_output[NodegroupAttributes.CREATED_AT]
    )

    if settings.TEST_SERVER_MODE:
        RegExTemplates.ISO8601_FORMAT.match(result_time).should.be.true
    else:
        result_time.should.equal(FROZEN_TIME)


@freeze_time(FROZEN_TIME)
@mock_eks
def test_create_nodegroup_generates_valid_nodegroup_modified_timestamp(
    NodegroupBuilder,
):
    _, generated_test_data = NodegroupBuilder()

    result_time = iso_8601_datetime_without_milliseconds(
        generated_test_data.nodegroup_describe_output[NodegroupAttributes.MODIFIED_AT]
    )

    if settings.TEST_SERVER_MODE:
        RegExTemplates.ISO8601_FORMAT.match(result_time).should.be.true
    else:
        result_time.should.equal(FROZEN_TIME)


@mock_eks
def test_create_nodegroup_generates_valid_autoscaling_group_name(NodegroupBuilder):
    _, generated_test_data = NodegroupBuilder()
    result_resources = generated_test_data.nodegroup_describe_output[
        NodegroupAttributes.RESOURCES
    ]

    result_asg_name = result_resources[NodegroupAttributes.AUTOSCALING_GROUPS][0][
        NodegroupAttributes.NAME
    ]

    RegExTemplates.NODEGROUP_ASG_NAME_PATTERN.match(result_asg_name).should.be.true


@mock_eks
def test_create_nodegroup_generates_valid_security_group_name(NodegroupBuilder):
    _, generated_test_data = NodegroupBuilder()
    result_resources = generated_test_data.nodegroup_describe_output[
        NodegroupAttributes.RESOURCES
    ]

    result_security_group = result_resources[NodegroupAttributes.REMOTE_ACCESS_SG]

    RegExTemplates.NODEGROUP_SECURITY_GROUP_NAME_PATTERN.match(
        result_security_group
    ).should.be.true


@mock_eks
def test_create_nodegroup_saves_provided_parameters(NodegroupBuilder):
    _, generated_test_data = NodegroupBuilder(minimal=False)

    for key, expected_value in generated_test_data.attributes_to_test:
        generated_test_data.nodegroup_describe_output[key].should.equal(expected_value)


@mock_eks
def test_describe_nodegroup_throws_exception_when_cluster_not_found(NodegroupBuilder):
    client, generated_test_data = NodegroupBuilder()
    expected_exception = ResourceNotFoundException
    expected_msg = CLUSTER_NOT_FOUND_MSG.format(
        clusterName=generated_test_data.nonexistent_cluster_name
    )

    with pytest.raises(ClientError) as raised_exception:
        client.describe_nodegroup(
            clusterName=generated_test_data.nonexistent_cluster_name,
            nodegroupName=generated_test_data.existing_nodegroup_name,
        )

    assert_expected_exception(raised_exception, expected_exception, expected_msg)


@mock_eks
def test_describe_nodegroup_throws_exception_when_nodegroup_not_found(NodegroupBuilder):
    client, generated_test_data = NodegroupBuilder()
    expected_exception = ResourceNotFoundException
    expected_msg = NODEGROUP_NOT_FOUND_MSG.format(
        nodegroupName=generated_test_data.nonexistent_nodegroup_name
    )

    with pytest.raises(ClientError) as raised_exception:
        client.describe_nodegroup(
            clusterName=generated_test_data.cluster_name,
            nodegroupName=generated_test_data.nonexistent_nodegroup_name,
        )

    assert_expected_exception(raised_exception, expected_exception, expected_msg)


@mock_eks
def test_delete_cluster_throws_exception_when_nodegroups_exist(NodegroupBuilder):
    client, generated_test_data = NodegroupBuilder()
    expected_exception = ResourceInUseException
    expected_msg = CLUSTER_IN_USE_MSG

    with pytest.raises(ClientError) as raised_exception:
        client.delete_cluster(name=generated_test_data.cluster_name)
    count_clusters_after_test = len(client.list_clusters()[ResponseAttributes.CLUSTERS])

    count_clusters_after_test.should.equal(BatchCountSize.SINGLE)
    assert_expected_exception(raised_exception, expected_exception, expected_msg)


@mock_eks
def test_delete_nodegroup_removes_deleted_nodegroup(NodegroupBuilder):
    client, generated_test_data = NodegroupBuilder(BatchCountSize.SMALL)

    client.delete_nodegroup(
        clusterName=generated_test_data.cluster_name,
        nodegroupName=generated_test_data.existing_nodegroup_name,
    )
    result = client.list_nodegroups(clusterName=generated_test_data.cluster_name)[
        ResponseAttributes.NODEGROUPS
    ]

    len(result).should.equal(BatchCountSize.SMALL - 1)
    result.should_not.contain(generated_test_data.existing_nodegroup_name)


@mock_eks
def test_delete_nodegroup_returns_deleted_nodegroup(NodegroupBuilder):
    client, generated_test_data = NodegroupBuilder(BatchCountSize.SMALL, False)

    result = client.delete_nodegroup(
        clusterName=generated_test_data.cluster_name,
        nodegroupName=generated_test_data.existing_nodegroup_name,
    )[ResponseAttributes.NODEGROUP]

    for key, expected_value in generated_test_data.attributes_to_test:
        result[key].should.equal(expected_value)


@mock_eks
def test_delete_nodegroup_throws_exception_when_cluster_not_found(NodegroupBuilder):
    client, generated_test_data = NodegroupBuilder()
    expected_exception = ResourceNotFoundException
    expected_msg = CLUSTER_NOT_FOUND_MSG.format(
        clusterName=generated_test_data.nonexistent_cluster_name
    )

    with pytest.raises(ClientError) as raised_exception:
        client.delete_nodegroup(
            clusterName=generated_test_data.nonexistent_cluster_name,
            nodegroupName=generated_test_data.existing_nodegroup_name,
        )

    assert_expected_exception(raised_exception, expected_exception, expected_msg)


@mock_eks
def test_delete_nodegroup_throws_exception_when_nodegroup_not_found(NodegroupBuilder):
    client, generated_test_data = NodegroupBuilder()
    expected_exception = ResourceNotFoundException
    expected_msg = NODEGROUP_NOT_FOUND_MSG.format(
        nodegroupName=generated_test_data.nonexistent_nodegroup_name
    )

    with pytest.raises(ClientError) as raised_exception:
        client.delete_nodegroup(
            clusterName=generated_test_data.cluster_name,
            nodegroupName=generated_test_data.nonexistent_nodegroup_name,
        )

    assert_expected_exception(raised_exception, expected_exception, expected_msg)


# If launch_template is specified, you can not specify instanceTypes, diskSize, or remoteAccess.
test_cases = [
    # Happy Paths
    (LAUNCH_TEMPLATE, None, None, None, PossibleTestResults.SUCCESS),
    (None, INSTANCE_TYPES, DISK_SIZE, REMOTE_ACCESS, PossibleTestResults.SUCCESS),
    (None, None, DISK_SIZE, REMOTE_ACCESS, PossibleTestResults.SUCCESS),
    (None, INSTANCE_TYPES, None, REMOTE_ACCESS, PossibleTestResults.SUCCESS),
    (None, INSTANCE_TYPES, DISK_SIZE, None, PossibleTestResults.SUCCESS),
    (None, INSTANCE_TYPES, None, None, PossibleTestResults.SUCCESS),
    (None, None, DISK_SIZE, None, PossibleTestResults.SUCCESS),
    (None, None, None, REMOTE_ACCESS, PossibleTestResults.SUCCESS),
    (None, None, None, None, PossibleTestResults.SUCCESS),
    # Unhappy Paths
    (LAUNCH_TEMPLATE, INSTANCE_TYPES, None, None, PossibleTestResults.FAILURE),
    (LAUNCH_TEMPLATE, None, DISK_SIZE, None, PossibleTestResults.FAILURE),
    (LAUNCH_TEMPLATE, None, None, REMOTE_ACCESS, PossibleTestResults.FAILURE),
    (LAUNCH_TEMPLATE, INSTANCE_TYPES, DISK_SIZE, None, PossibleTestResults.FAILURE),
    (LAUNCH_TEMPLATE, INSTANCE_TYPES, None, REMOTE_ACCESS, PossibleTestResults.FAILURE),
    (LAUNCH_TEMPLATE, None, DISK_SIZE, REMOTE_ACCESS, PossibleTestResults.FAILURE),
    (
        LAUNCH_TEMPLATE,
        INSTANCE_TYPES,
        DISK_SIZE,
        REMOTE_ACCESS,
        PossibleTestResults.FAILURE,
    ),
]


@pytest.mark.parametrize(
    "launch_template, instance_types, disk_size, remote_access, expected_result",
    test_cases,
)
@mock_eks
def test_create_nodegroup_handles_launch_template_combinations(
    ClusterBuilder,
    launch_template,
    instance_types,
    disk_size,
    remote_access,
    expected_result,
):
    client, generated_test_data = ClusterBuilder()
    nodegroup_name = random_string()
    expected_exception = InvalidParameterException
    expected_msg = None

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
            + [
                _
                for _ in [launch_template, instance_types, disk_size, remote_access]
                if _
            ]
        )
    )

    if expected_result == PossibleTestResults.SUCCESS:
        result = client.create_nodegroup(**test_inputs)[ResponseAttributes.NODEGROUP]

        for key, expected_value in test_inputs.items():
            result[key].should.equal(expected_value)
    else:
        if launch_template and disk_size:
            expected_msg = LAUNCH_TEMPLATE_WITH_DISK_SIZE_MSG
        elif launch_template and remote_access:
            expected_msg = LAUNCH_TEMPLATE_WITH_REMOTE_ACCESS_MSG
        # Docs say this combination throws an exception but testing shows that
        # instanceTypes overrides the launchTemplate instance values instead.
        # Leaving here for easier correction if/when that gets fixed.
        elif launch_template and instance_types:
            pass

    if expected_msg:
        with pytest.raises(ClientError) as raised_exception:
            client.create_nodegroup(**test_inputs)
        assert_expected_exception(raised_exception, expected_exception, expected_msg)


@mock_eks
def test_list_fargate_profile_returns_empty_by_default(ClusterBuilder):
    client, generated_test_data = ClusterBuilder()

    result = client.list_fargate_profiles(
        clusterName=generated_test_data.existing_cluster_name
    )[ResponseAttributes.FARGATE_PROFILE_NAMES]

    result.should.equal([])


@mock_eks
def test_list_fargate_profile_returns_sorted_fargate_profile_names(
    FargateProfileBuilder,
):
    client, generated_test_data = FargateProfileBuilder(BatchCountSize.SMALL)
    expected_result = sorted(generated_test_data.fargate_profile_names)

    result = client.list_fargate_profiles(clusterName=generated_test_data.cluster_name)[
        ResponseAttributes.FARGATE_PROFILE_NAMES
    ]

    assert_result_matches_expected_list(result, expected_result, BatchCountSize.SMALL)


@mock_eks
def test_list_fargate_profile_returns_default_max_results(FargateProfileBuilder):
    client, generated_test_data = FargateProfileBuilder(BatchCountSize.LARGE)
    expected_len = DEFAULT_MAX_RESULTS
    expected_result = (sorted(generated_test_data.fargate_profile_names))[:expected_len]

    result = client.list_fargate_profiles(clusterName=generated_test_data.cluster_name)[
        ResponseAttributes.FARGATE_PROFILE_NAMES
    ]

    assert_result_matches_expected_list(result, expected_result, expected_len)


@mock_eks
def test_list_fargate_profile_returns_custom_max_results(FargateProfileBuilder):
    client, generated_test_data = FargateProfileBuilder(BatchCountSize.LARGE)
    expected_len = BatchCountSize.LARGE
    expected_result = (sorted(generated_test_data.fargate_profile_names))[:expected_len]

    result = client.list_fargate_profiles(
        clusterName=generated_test_data.cluster_name, maxResults=expected_len
    )[ResponseAttributes.FARGATE_PROFILE_NAMES]

    assert_result_matches_expected_list(result, expected_result, expected_len)


@mock_eks
def test_list_fargate_profile_returns_second_page_results(FargateProfileBuilder):
    client, generated_test_data = FargateProfileBuilder(BatchCountSize.MEDIUM)
    page1_len = PageCount.LARGE
    expected_len = BatchCountSize.MEDIUM - page1_len
    expected_result = (sorted(generated_test_data.fargate_profile_names))[page1_len:]
    token = client.list_fargate_profiles(
        clusterName=generated_test_data.cluster_name, maxResults=page1_len
    )[ResponseAttributes.NEXT_TOKEN]

    result = client.list_fargate_profiles(
        clusterName=generated_test_data.cluster_name, nextToken=token
    )[ResponseAttributes.FARGATE_PROFILE_NAMES]

    assert_result_matches_expected_list(result, expected_result, expected_len)


@mock_eks
def test_list_fargate_profile_returns_custom_second_page_results(FargateProfileBuilder):
    client, generated_test_data = FargateProfileBuilder(BatchCountSize.MEDIUM)
    page1_len = PageCount.LARGE
    expected_len = PageCount.SMALL
    expected_result = (sorted(generated_test_data.fargate_profile_names))[
        page1_len : page1_len + expected_len
    ]
    token = client.list_fargate_profiles(
        clusterName=generated_test_data.cluster_name, maxResults=page1_len
    )[ResponseAttributes.NEXT_TOKEN]

    result = client.list_fargate_profiles(
        clusterName=generated_test_data.cluster_name,
        maxResults=expected_len,
        nextToken=token,
    )[ResponseAttributes.FARGATE_PROFILE_NAMES]

    assert_result_matches_expected_list(result, expected_result, expected_len)


@mock_eks
def test_create_fargate_profile_throws_exception_when_cluster_not_found():
    client = boto3.client(SERVICE, region_name=REGION)
    non_existent_cluster_name = random_string()
    expected_exception = ResourceNotFoundException
    expected_msg = CLUSTER_NOT_FOUND_MSG.format(clusterName=non_existent_cluster_name)

    with pytest.raises(ClientError) as raised_exception:
        client.create_fargate_profile(
            clusterName=non_existent_cluster_name,
            fargateProfileName=random_string(),
            **dict(FargateProfileInputs.REQUIRED)
        )

    assert_expected_exception(raised_exception, expected_exception, expected_msg)


@mock_eks
def test_create_fargate_profile_throws_exception_when_fargate_profile_already_exists(
    FargateProfileBuilder,
):
    client, generated_test_data = FargateProfileBuilder(BatchCountSize.SMALL)
    expected_exception = ResourceInUseException
    expected_msg = FARGATE_PROFILE_EXISTS_MSG

    with pytest.raises(ClientError) as raised_exception:
        client.create_fargate_profile(
            clusterName=generated_test_data.cluster_name,
            fargateProfileName=generated_test_data.existing_fargate_profile_name,
            **dict(FargateProfileInputs.REQUIRED)
        )
    count_profiles_after_test = len(
        client.list_fargate_profiles(clusterName=generated_test_data.cluster_name)[
            ResponseAttributes.FARGATE_PROFILE_NAMES
        ]
    )

    count_profiles_after_test.should.equal(BatchCountSize.SMALL)
    assert_expected_exception(raised_exception, expected_exception, expected_msg)


@mock_eks
def test_create_fargate_profile_throws_exception_when_cluster_not_active(
    FargateProfileBuilder,
):
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Cant patch Cluster attributes in server mode.")
    client, generated_test_data = FargateProfileBuilder(BatchCountSize.SMALL)
    expected_exception = InvalidRequestException
    expected_msg = CLUSTER_NOT_READY_MSG.format(
        clusterName=generated_test_data.cluster_name
    )

    with mock.patch("moto.eks.models.Cluster.isActive", return_value=False):
        with pytest.raises(ClientError) as raised_exception:
            client.create_fargate_profile(
                clusterName=generated_test_data.cluster_name,
                fargateProfileName=random_string(),
                **dict(FargateProfileInputs.REQUIRED)
            )
    count_fargate_profiles_after_test = len(
        client.list_fargate_profiles(clusterName=generated_test_data.cluster_name)[
            ResponseAttributes.FARGATE_PROFILE_NAMES
        ]
    )

    count_fargate_profiles_after_test.should.equal(BatchCountSize.SMALL)
    assert_expected_exception(raised_exception, expected_exception, expected_msg)


@mock_eks
def test_create_fargate_profile_generates_valid_profile_arn(FargateProfileBuilder):
    _, generated_test_data = FargateProfileBuilder()
    expected_arn_values = [
        PARTITIONS,
        REGION,
        ACCOUNT_ID,
        generated_test_data.cluster_name,
        generated_test_data.fargate_profile_names,
        None,
    ]

    all_arn_values_should_be_valid(
        expected_arn_values=expected_arn_values,
        pattern=RegExTemplates.FARGATE_PROFILE_ARN,
        arn_under_test=generated_test_data.fargate_describe_output[
            FargateProfileAttributes.ARN
        ],
    )


@freeze_time(FROZEN_TIME)
@mock_eks
def test_create_fargate_profile_generates_valid_created_timestamp(
    FargateProfileBuilder,
):
    _, generated_test_data = FargateProfileBuilder()

    result_time = iso_8601_datetime_without_milliseconds(
        generated_test_data.fargate_describe_output[FargateProfileAttributes.CREATED_AT]
    )

    if settings.TEST_SERVER_MODE:
        RegExTemplates.ISO8601_FORMAT.match(result_time).should.be.true
    else:
        result_time.should.equal(FROZEN_TIME)


@mock_eks
def test_create_fargate_profile_saves_provided_parameters(FargateProfileBuilder):
    _, generated_test_data = FargateProfileBuilder(minimal=False)

    for key, expected_value in generated_test_data.attributes_to_test:
        generated_test_data.fargate_describe_output[key].should.equal(expected_value)


@mock_eks
def test_describe_fargate_profile_throws_exception_when_cluster_not_found(
    FargateProfileBuilder,
):
    client, generated_test_data = FargateProfileBuilder()
    expected_exception = ResourceNotFoundException
    expected_msg = CLUSTER_NOT_FOUND_MSG.format(
        clusterName=generated_test_data.nonexistent_cluster_name
    )

    with pytest.raises(ClientError) as raised_exception:
        client.describe_fargate_profile(
            clusterName=generated_test_data.nonexistent_cluster_name,
            fargateProfileName=generated_test_data.existing_fargate_profile_name,
        )

    assert_expected_exception(raised_exception, expected_exception, expected_msg)


@mock_eks
def test_describe_fargate_profile_throws_exception_when_profile_not_found(
    FargateProfileBuilder,
):
    client, generated_test_data = FargateProfileBuilder()
    expected_exception = ResourceNotFoundException
    expected_msg = FARGATE_PROFILE_NOT_FOUND_MSG.format(
        fargateProfileName=generated_test_data.nonexistent_fargate_profile_name
    )

    with pytest.raises(ClientError) as raised_exception:
        client.describe_fargate_profile(
            clusterName=generated_test_data.cluster_name,
            fargateProfileName=generated_test_data.nonexistent_fargate_profile_name,
        )

    assert_expected_exception(raised_exception, expected_exception, expected_msg)


@mock_eks
def test_delete_fargate_profile_removes_deleted_fargate_profile(FargateProfileBuilder):
    client, generated_test_data = FargateProfileBuilder(BatchCountSize.SMALL)

    client.delete_fargate_profile(
        clusterName=generated_test_data.cluster_name,
        fargateProfileName=generated_test_data.existing_fargate_profile_name,
    )
    result = client.list_fargate_profiles(clusterName=generated_test_data.cluster_name)[
        ResponseAttributes.FARGATE_PROFILE_NAMES
    ]

    len(result).should.equal(BatchCountSize.SMALL - 1)
    result.should_not.contain(generated_test_data.existing_fargate_profile_name)


@mock_eks
def test_delete_fargate_profile_returns_deleted_fargate_profile(FargateProfileBuilder):
    client, generated_test_data = FargateProfileBuilder(BatchCountSize.SMALL, False)

    result = client.delete_fargate_profile(
        clusterName=generated_test_data.cluster_name,
        fargateProfileName=generated_test_data.existing_fargate_profile_name,
    )[ResponseAttributes.FARGATE_PROFILE]

    for key, expected_value in generated_test_data.attributes_to_test:
        result[key].should.equal(expected_value)


@mock_eks
def test_delete_fargate_profile_throws_exception_when_cluster_not_found(
    FargateProfileBuilder,
):
    client, generated_test_data = FargateProfileBuilder()
    expected_exception = ResourceNotFoundException
    expected_msg = CLUSTER_NOT_FOUND_MSG.format(
        clusterName=generated_test_data.nonexistent_cluster_name
    )

    with pytest.raises(ClientError) as raised_exception:
        client.delete_fargate_profile(
            clusterName=generated_test_data.nonexistent_cluster_name,
            fargateProfileName=generated_test_data.existing_fargate_profile_name,
        )

    assert_expected_exception(raised_exception, expected_exception, expected_msg)


@mock_eks
def test_delete_fargate_profile_throws_exception_when_fargate_profile_not_found(
    FargateProfileBuilder,
):
    client, generated_test_data = FargateProfileBuilder()
    expected_exception = ResourceNotFoundException
    expected_msg = FARGATE_PROFILE_NOT_FOUND_MSG.format(
        fargateProfileName=generated_test_data.nonexistent_fargate_profile_name
    )

    with pytest.raises(ClientError) as raised_exception:
        client.delete_fargate_profile(
            clusterName=generated_test_data.cluster_name,
            fargateProfileName=generated_test_data.nonexistent_fargate_profile_name,
        )

    assert_expected_exception(raised_exception, expected_exception, expected_msg)


@mock_eks
def test_create_fargate_throws_exception_when_no_selectors_provided(ClusterBuilder):
    client, generated_test_data = ClusterBuilder()
    cluster_name = generated_test_data.existing_cluster_name
    fargate_profile_name = random_string()
    expected_exception = InvalidParameterException
    expected_msg = FARGATE_PROFILE_NEEDS_SELECTOR_MSG

    test_inputs = dict(
        deepcopy(
            # Required Constants
            [POD_EXECUTION_ROLE_ARN]
            # Required Variables
            + [
                (ClusterAttributes.CLUSTER_NAME, cluster_name),
                (FargateProfileAttributes.FARGATE_PROFILE_NAME, fargate_profile_name),
            ]
        )
    )

    with pytest.raises(ClientError) as raised_exception:
        client.create_fargate_profile(**test_inputs)
    assert_expected_exception(raised_exception, expected_exception, expected_msg)


# The following Selector test cases have all been verified against the AWS API using cURL.
selector_formatting_test_cases = [
    # Format is ([Selector(s), expected_message, expected_result])
    # Happy Paths
    # Selector with a Namespace and no Labels
    (
        [{FargateProfileAttributes.NAMESPACE: DEFAULT_NAMESPACE}],
        None,
        PossibleTestResults.SUCCESS,
    ),
    # Selector with a Namespace and an empty collection of Labels
    (
        [
            {
                FargateProfileAttributes.NAMESPACE: DEFAULT_NAMESPACE,
                FargateProfileAttributes.LABELS: generate_dict("label", 0),
            }
        ],
        None,
        PossibleTestResults.SUCCESS,
    ),
    # Selector with a Namespace and one valid Label
    (
        [
            {
                FargateProfileAttributes.NAMESPACE: DEFAULT_NAMESPACE,
                FargateProfileAttributes.LABELS: generate_dict("label", 1),
            }
        ],
        None,
        PossibleTestResults.SUCCESS,
    ),
    # Selector with a Namespace and the maximum number of Labels
    (
        [
            {
                FargateProfileAttributes.NAMESPACE: DEFAULT_NAMESPACE,
                FargateProfileAttributes.LABELS: generate_dict(
                    "label", MAX_FARGATE_LABELS
                ),
            }
        ],
        None,
        PossibleTestResults.SUCCESS,
    ),
    # Two valid Selectors
    (
        [
            {FargateProfileAttributes.NAMESPACE: DEFAULT_NAMESPACE},
            {FargateProfileAttributes.NAMESPACE: DEFAULT_NAMESPACE},
        ],
        None,
        PossibleTestResults.SUCCESS,
    ),
    # Unhappy Cases
    # No Selectors provided
    ([], FARGATE_PROFILE_NEEDS_SELECTOR_MSG, PossibleTestResults.FAILURE),
    # Empty Selector / Selector without a Namespace or Labels
    ([{}], FARGATE_PROFILE_SELECTOR_NEEDS_NAMESPACE, PossibleTestResults.FAILURE),
    # Selector with labels but no Namespace
    (
        [{FargateProfileAttributes.LABELS: generate_dict("label", 1)}],
        FARGATE_PROFILE_SELECTOR_NEEDS_NAMESPACE,
        PossibleTestResults.FAILURE,
    ),
    # Selector with Namespace but too many Labels
    (
        [
            {
                FargateProfileAttributes.NAMESPACE: DEFAULT_NAMESPACE,
                FargateProfileAttributes.LABELS: generate_dict(
                    "label", MAX_FARGATE_LABELS + 1
                ),
            }
        ],
        FARGATE_PROFILE_TOO_MANY_LABELS,
        PossibleTestResults.FAILURE,
    ),
    # Valid Selector followed by Empty Selector
    (
        [{FargateProfileAttributes.NAMESPACE: DEFAULT_NAMESPACE}, {}],
        FARGATE_PROFILE_SELECTOR_NEEDS_NAMESPACE,
        PossibleTestResults.FAILURE,
    ),
    # Empty Selector followed by Valid Selector
    (
        [{}, {FargateProfileAttributes.NAMESPACE: DEFAULT_NAMESPACE}],
        FARGATE_PROFILE_SELECTOR_NEEDS_NAMESPACE,
        PossibleTestResults.FAILURE,
    ),
    # Empty Selector followed by Empty Selector
    ([{}, {}], FARGATE_PROFILE_SELECTOR_NEEDS_NAMESPACE, PossibleTestResults.FAILURE),
    # Valid Selector followed by Selector with Namespace but too many Labels
    (
        [
            {FargateProfileAttributes.NAMESPACE: DEFAULT_NAMESPACE},
            {
                FargateProfileAttributes.NAMESPACE: DEFAULT_NAMESPACE,
                FargateProfileAttributes.LABELS: generate_dict(
                    "label", MAX_FARGATE_LABELS + 1
                ),
            },
        ],
        FARGATE_PROFILE_TOO_MANY_LABELS,
        PossibleTestResults.FAILURE,
    ),
]


@pytest.mark.parametrize(
    "selectors, expected_message, expected_result", selector_formatting_test_cases
)
@mock_eks
def test_create_fargate_selectors(
    ClusterBuilder, selectors, expected_message, expected_result
):
    client, generated_test_data = ClusterBuilder()
    cluster_name = generated_test_data.existing_cluster_name
    fargate_profile_name = random_string()
    expected_exception = InvalidParameterException

    test_inputs = dict(
        deepcopy(
            # Required Constants
            [POD_EXECUTION_ROLE_ARN]
            # Required Variables
            + [
                (ClusterAttributes.CLUSTER_NAME, cluster_name),
                (FargateProfileAttributes.FARGATE_PROFILE_NAME, fargate_profile_name),
            ]
            # Test Case Values
            + [(FargateProfileAttributes.SELECTORS, selectors)]
        )
    )

    if expected_result == PossibleTestResults.SUCCESS:
        result = client.create_fargate_profile(**test_inputs)[
            ResponseAttributes.FARGATE_PROFILE
        ]
        for key, expected_value in test_inputs.items():
            result[key].should.equal(expected_value)
    else:
        with pytest.raises(ClientError) as raised_exception:
            client.create_fargate_profile(**test_inputs)
        assert_expected_exception(
            raised_exception, expected_exception, expected_message
        )


def all_arn_values_should_be_valid(expected_arn_values, pattern, arn_under_test):
    """
    Applies regex `pattern` to `arn_under_test` and asserts
    that each group matches the provided expected value.
    A list entry of None in the 'expected_arn_values' will
    assert that the value exists but not match a specific value.
    """
    findall = pattern.findall(arn_under_test)[0]
    expected_values = deepcopy(expected_arn_values)
    # findall() returns a list of matches from right to left so it must be reversed
    # in order to match the logical order of the 'expected_arn_values' list.
    for value in reversed(findall):
        expected_value = expected_values.pop()
        if expected_value:
            value.should.be.within(expected_value)
        else:
            value.shouldnt.equal(None)
    region_matches_partition(findall[1], findall[0]).should.be.true


def assert_expected_exception(raised_exception, expected_exception, expected_msg):
    error = raised_exception.value.response[ErrorAttributes.ERROR]
    error[ErrorAttributes.CODE].should.equal(expected_exception.TYPE)
    error[ErrorAttributes.MESSAGE].should.equal(expected_msg)


def assert_result_matches_expected_list(result, expected_result, expected_len):
    assert result == expected_result
    assert len(result) == expected_len


def assert_valid_selectors(ClusterBuilder, expected_msg, expected_result, selectors):
    client, generated_test_data = ClusterBuilder()
    cluster_name = generated_test_data.existing_cluster_name
    fargate_profile_name = random_string()
    expected_exception = InvalidParameterException

    test_inputs = dict(
        deepcopy(
            # Required Constants
            [POD_EXECUTION_ROLE_ARN]
            # Required Variables
            + [
                (ClusterAttributes.CLUSTER_NAME, cluster_name),
                (FargateProfileAttributes.FARGATE_PROFILE_NAME, fargate_profile_name),
            ]
            # Test Case Values
            + [(FargateProfileAttributes.SELECTORS, selectors)]
        )
    )

    if expected_result == PossibleTestResults.SUCCESS:
        result = client.create_fargate_profile(**test_inputs)[
            ResponseAttributes.FARGATE_PROFILE
        ]
        for key, expected_value in test_inputs.items():
            result[key].should.equal(expected_value)
    else:
        with pytest.raises(ClientError) as raised_exception:
            client.create_fargate_profile(**test_inputs)
        assert_expected_exception(raised_exception, expected_exception, expected_msg)
