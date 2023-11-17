import json
import pytest
import unittest

from copy import deepcopy
import moto.server as server
from moto import mock_eks, settings
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
from moto.eks.exceptions import ResourceInUseException, ResourceNotFoundException
from moto.eks.models import (
    CLUSTER_EXISTS_MSG,
    CLUSTER_IN_USE_MSG,
    CLUSTER_NOT_FOUND_MSG,
    NODEGROUP_EXISTS_MSG,
    NODEGROUP_NOT_FOUND_MSG,
)
from moto.eks.responses import DEFAULT_MAX_RESULTS, DEFAULT_NEXT_TOKEN
from tests.test_eks.test_eks import all_arn_values_should_be_valid
from tests.test_eks.test_eks_constants import (
    AddonAttributes,
    ClusterAttributes,
    DEFAULT_ENCODING,
    DEFAULT_HTTP_HEADERS,
    DEFAULT_REGION,
    Endpoints,
    FargateProfileAttributes,
    HttpHeaders,
    NodegroupAttributes,
    NODEROLE_ARN_KEY,
    NODEROLE_ARN_VALUE,
    PARTITIONS,
    RegExTemplates,
    ResponseAttributes,
    ROLE_ARN_KEY,
    ROLE_ARN_VALUE,
    SERVICE,
    StatusCodes,
    SUBNETS_KEY,
    SUBNETS_VALUE,
)

"""
Test the different server responses
"""

NAME_LIST = ["foo", "bar", "baz", "qux"]


class TestCluster:
    cluster_name = "example_cluster"
    data = {ClusterAttributes.NAME: cluster_name, ROLE_ARN_KEY: ROLE_ARN_VALUE}
    endpoint = Endpoints.CREATE_CLUSTER
    expected_arn_values = [
        PARTITIONS,
        DEFAULT_REGION,
        ACCOUNT_ID,
        cluster_name,
    ]


class TestNodegroup:
    cluster_name = TestCluster.cluster_name
    nodegroup_name = "example_nodegroup"
    data = {
        ClusterAttributes.CLUSTER_NAME: cluster_name,
        NodegroupAttributes.NODEGROUP_NAME: nodegroup_name,
        NODEROLE_ARN_KEY: NODEROLE_ARN_VALUE,
        SUBNETS_KEY: SUBNETS_VALUE,
    }
    endpoint = Endpoints.CREATE_NODEGROUP.format(clusterName=cluster_name)
    expected_arn_values = [
        PARTITIONS,
        DEFAULT_REGION,
        ACCOUNT_ID,
        cluster_name,
        nodegroup_name,
        None,
    ]


@pytest.fixture(autouse=True, name="test_client")
def fixture_test_client():
    if settings.TEST_SERVER_MODE:
        raise unittest.SkipTest("No point in testing this in ServerMode")
    backend = server.create_backend_app(service=SERVICE)
    yield backend.test_client()


@pytest.fixture(scope="function", name="create_cluster")
def fixtue_create_cluster(test_client):
    def create_and_verify_cluster(client, name):
        """Creates one valid cluster and verifies return status code 200."""
        data = deepcopy(TestCluster.data)
        data.update(name=name)
        response = client.post(
            TestCluster.endpoint, data=json.dumps(data), headers=DEFAULT_HTTP_HEADERS
        )
        assert response.status_code == StatusCodes.OK

        return json.loads(response.data.decode(DEFAULT_ENCODING))[
            ResponseAttributes.CLUSTER
        ]

    def _execute(name=TestCluster.cluster_name):
        return create_and_verify_cluster(test_client, name=name)

    yield _execute


@pytest.fixture(scope="function", autouse=True, name="create_nodegroup")
def fixture_create_nodegroup(test_client):
    def create_and_verify_nodegroup(client, name):
        """Creates one valid nodegroup and verifies return status code 200."""
        data = deepcopy(TestNodegroup.data)
        data.update(nodegroupName=name)
        response = client.post(
            TestNodegroup.endpoint, data=json.dumps(data), headers=DEFAULT_HTTP_HEADERS
        )
        assert response.status_code == StatusCodes.OK

        return json.loads(response.data.decode(DEFAULT_ENCODING))[
            ResponseAttributes.NODEGROUP
        ]

    def _execute(name=TestNodegroup.nodegroup_name):
        return create_and_verify_nodegroup(test_client, name=name)

    yield _execute


@mock_eks
def test_eks_create_single_cluster(create_cluster):
    result_cluster = create_cluster()

    assert result_cluster[ClusterAttributes.NAME] == TestCluster.cluster_name
    all_arn_values_should_be_valid(
        expected_arn_values=TestCluster.expected_arn_values,
        pattern=RegExTemplates.CLUSTER_ARN,
        arn_under_test=result_cluster[ClusterAttributes.ARN],
    )


@mock_eks
def test_eks_create_multiple_clusters_with_same_name(test_client, create_cluster):
    create_cluster()
    expected_exception = ResourceInUseException
    expected_msg = CLUSTER_EXISTS_MSG.format(clusterName=TestCluster.cluster_name)
    expected_data = {
        ClusterAttributes.CLUSTER_NAME: TestCluster.cluster_name,
        NodegroupAttributes.NODEGROUP_NAME: None,
        AddonAttributes.ADDON_NAME: None,
        ResponseAttributes.MESSAGE: expected_msg,
    }

    response = test_client.post(
        TestCluster.endpoint,
        data=json.dumps(TestCluster.data),
        headers=DEFAULT_HTTP_HEADERS,
    )

    should_return_expected_exception(response, expected_exception, expected_data)


@mock_eks
def test_eks_create_nodegroup_without_cluster(test_client):
    expected_exception = ResourceNotFoundException
    expected_msg = CLUSTER_NOT_FOUND_MSG.format(clusterName=TestCluster.cluster_name)
    expected_data = {
        ClusterAttributes.CLUSTER_NAME: None,
        NodegroupAttributes.NODEGROUP_NAME: None,
        FargateProfileAttributes.FARGATE_PROFILE_NAME: None,
        AddonAttributes.ADDON_NAME: None,
        ResponseAttributes.MESSAGE: expected_msg,
    }
    endpoint = Endpoints.CREATE_NODEGROUP.format(clusterName=TestCluster.cluster_name)

    response = test_client.post(
        endpoint, data=json.dumps(TestNodegroup.data), headers=DEFAULT_HTTP_HEADERS
    )

    should_return_expected_exception(response, expected_exception, expected_data)


@mock_eks
def test_eks_create_nodegroup_on_existing_cluster(create_cluster, create_nodegroup):
    create_cluster()
    result_data = create_nodegroup()

    assert (
        result_data[NodegroupAttributes.NODEGROUP_NAME] == TestNodegroup.nodegroup_name
    )
    all_arn_values_should_be_valid(
        expected_arn_values=TestNodegroup.expected_arn_values,
        pattern=RegExTemplates.NODEGROUP_ARN,
        arn_under_test=result_data[NodegroupAttributes.ARN],
    )


@mock_eks
def test_eks_create_multiple_nodegroups_with_same_name(
    test_client, create_cluster, create_nodegroup
):
    create_cluster()
    create_nodegroup()
    expected_exception = ResourceInUseException
    expected_msg = NODEGROUP_EXISTS_MSG.format(
        clusterName=TestNodegroup.cluster_name,
        nodegroupName=TestNodegroup.nodegroup_name,
    )
    expected_data = {
        ClusterAttributes.CLUSTER_NAME: TestNodegroup.cluster_name,
        NodegroupAttributes.NODEGROUP_NAME: TestNodegroup.nodegroup_name,
        AddonAttributes.ADDON_NAME: None,
        ResponseAttributes.MESSAGE: expected_msg,
    }

    response = test_client.post(
        TestNodegroup.endpoint,
        data=json.dumps(TestNodegroup.data),
        headers=DEFAULT_HTTP_HEADERS,
    )

    should_return_expected_exception(response, expected_exception, expected_data)


@mock_eks
def test_eks_list_clusters(test_client, create_cluster):
    [create_cluster(name) for name in NAME_LIST]

    response = test_client.get(
        Endpoints.LIST_CLUSTERS.format(
            maxResults=DEFAULT_MAX_RESULTS, nextToken=DEFAULT_NEXT_TOKEN
        )
    )
    result_data = json.loads(response.data.decode(DEFAULT_ENCODING))[
        ResponseAttributes.CLUSTERS
    ]

    assert response.status_code == StatusCodes.OK
    assert len(result_data) == len(NAME_LIST)
    assert sorted(result_data) == sorted(NAME_LIST)


@mock_eks
def test_eks_list_nodegroups(test_client, create_cluster, create_nodegroup):
    create_cluster()
    [create_nodegroup(name) for name in NAME_LIST]

    response = test_client.get(
        Endpoints.LIST_NODEGROUPS.format(
            clusterName=TestCluster.cluster_name,
            maxResults=DEFAULT_MAX_RESULTS,
            nextToken=DEFAULT_NEXT_TOKEN,
        )
    )
    result_data = json.loads(response.data.decode(DEFAULT_ENCODING))[
        ResponseAttributes.NODEGROUPS
    ]

    assert response.status_code == StatusCodes.OK
    assert sorted(result_data) == sorted(NAME_LIST)
    assert len(result_data) == len(NAME_LIST)


@mock_eks
def test_eks_describe_existing_cluster(test_client, create_cluster):
    create_cluster()

    response = test_client.get(
        Endpoints.DESCRIBE_CLUSTER.format(clusterName=TestCluster.cluster_name)
    )
    result_data = json.loads(response.data.decode(DEFAULT_ENCODING))[
        ResponseAttributes.CLUSTER
    ]

    assert response.status_code == StatusCodes.OK
    assert result_data[ClusterAttributes.NAME] == TestCluster.cluster_name
    assert result_data[ClusterAttributes.ENCRYPTION_CONFIG] == []
    all_arn_values_should_be_valid(
        expected_arn_values=TestCluster.expected_arn_values,
        pattern=RegExTemplates.CLUSTER_ARN,
        arn_under_test=result_data[ClusterAttributes.ARN],
    )


@mock_eks
def test_eks_describe_nonexisting_cluster(test_client):
    expected_exception = ResourceNotFoundException
    expected_msg = CLUSTER_NOT_FOUND_MSG.format(clusterName=TestCluster.cluster_name)
    expected_data = {
        ClusterAttributes.CLUSTER_NAME: None,
        NodegroupAttributes.NODEGROUP_NAME: None,
        FargateProfileAttributes.FARGATE_PROFILE_NAME: None,
        AddonAttributes.ADDON_NAME: None,
        ResponseAttributes.MESSAGE: expected_msg,
    }

    response = test_client.get(
        Endpoints.DESCRIBE_CLUSTER.format(clusterName=TestCluster.cluster_name)
    )

    should_return_expected_exception(response, expected_exception, expected_data)


@mock_eks
def test_eks_describe_existing_nodegroup(test_client, create_cluster, create_nodegroup):
    create_cluster()
    create_nodegroup()

    response = test_client.get(
        Endpoints.DESCRIBE_NODEGROUP.format(
            clusterName=TestNodegroup.cluster_name,
            nodegroupName=TestNodegroup.nodegroup_name,
        )
    )
    result_data = json.loads(response.data.decode(DEFAULT_ENCODING))[
        ResponseAttributes.NODEGROUP
    ]

    assert response.status_code == StatusCodes.OK
    assert result_data[ClusterAttributes.CLUSTER_NAME] == TestNodegroup.cluster_name
    assert (
        result_data[NodegroupAttributes.NODEGROUP_NAME] == TestNodegroup.nodegroup_name
    )
    all_arn_values_should_be_valid(
        expected_arn_values=TestNodegroup.expected_arn_values,
        pattern=RegExTemplates.NODEGROUP_ARN,
        arn_under_test=result_data[NodegroupAttributes.ARN],
    )


@mock_eks
def test_eks_describe_nonexisting_nodegroup(test_client, create_cluster):
    create_cluster()
    expected_exception = ResourceNotFoundException
    expected_msg = NODEGROUP_NOT_FOUND_MSG.format(
        clusterName=TestNodegroup.cluster_name,
        nodegroupName=TestNodegroup.nodegroup_name,
    )
    expected_data = {
        ClusterAttributes.CLUSTER_NAME: TestNodegroup.cluster_name,
        NodegroupAttributes.NODEGROUP_NAME: TestNodegroup.nodegroup_name,
        FargateProfileAttributes.FARGATE_PROFILE_NAME: None,
        AddonAttributes.ADDON_NAME: None,
        ResponseAttributes.MESSAGE: expected_msg,
    }

    response = test_client.get(
        Endpoints.DESCRIBE_NODEGROUP.format(
            clusterName=TestCluster.cluster_name,
            nodegroupName=TestNodegroup.nodegroup_name,
        )
    )

    should_return_expected_exception(response, expected_exception, expected_data)


@mock_eks
def test_eks_describe_nodegroup_nonexisting_cluster(test_client):
    expected_exception = ResourceNotFoundException
    expected_msg = CLUSTER_NOT_FOUND_MSG.format(clusterName=TestNodegroup.cluster_name)
    expected_data = {
        ClusterAttributes.CLUSTER_NAME: TestNodegroup.cluster_name,
        NodegroupAttributes.NODEGROUP_NAME: TestNodegroup.nodegroup_name,
        FargateProfileAttributes.FARGATE_PROFILE_NAME: None,
        AddonAttributes.ADDON_NAME: None,
        ResponseAttributes.MESSAGE: expected_msg,
    }

    response = test_client.get(
        Endpoints.DESCRIBE_NODEGROUP.format(
            clusterName=TestCluster.cluster_name,
            nodegroupName=TestNodegroup.nodegroup_name,
        )
    )

    should_return_expected_exception(response, expected_exception, expected_data)


@mock_eks
def test_eks_delete_cluster(test_client, create_cluster):
    create_cluster()

    response = test_client.delete(
        Endpoints.DELETE_CLUSTER.format(clusterName=TestCluster.cluster_name)
    )
    result_data = json.loads(response.data.decode(DEFAULT_ENCODING))[
        ResponseAttributes.CLUSTER
    ]

    assert response.status_code == StatusCodes.OK
    assert result_data[ClusterAttributes.NAME] == TestCluster.cluster_name
    all_arn_values_should_be_valid(
        expected_arn_values=TestCluster.expected_arn_values,
        pattern=RegExTemplates.CLUSTER_ARN,
        arn_under_test=result_data[ClusterAttributes.ARN],
    )


@mock_eks
def test_eks_delete_nonexisting_cluster(test_client):
    expected_exception = ResourceNotFoundException
    expected_msg = CLUSTER_NOT_FOUND_MSG.format(clusterName=TestCluster.cluster_name)
    expected_data = {
        ClusterAttributes.CLUSTER_NAME: None,
        NodegroupAttributes.NODEGROUP_NAME: None,
        FargateProfileAttributes.FARGATE_PROFILE_NAME: None,
        AddonAttributes.ADDON_NAME: None,
        ResponseAttributes.MESSAGE: expected_msg,
    }

    response = test_client.delete(
        Endpoints.DELETE_CLUSTER.format(clusterName=TestCluster.cluster_name)
    )

    should_return_expected_exception(response, expected_exception, expected_data)


@mock_eks
def test_eks_delete_cluster_with_nodegroups(
    test_client, create_cluster, create_nodegroup
):
    create_cluster()
    create_nodegroup()
    expected_exception = ResourceInUseException
    expected_msg = CLUSTER_IN_USE_MSG.format(clusterName=TestCluster.cluster_name)
    expected_data = {
        ClusterAttributes.CLUSTER_NAME: TestCluster.cluster_name,
        NodegroupAttributes.NODEGROUP_NAME: TestNodegroup.nodegroup_name,
        AddonAttributes.ADDON_NAME: None,
        ResponseAttributes.MESSAGE: expected_msg,
    }

    response = test_client.delete(
        Endpoints.DELETE_CLUSTER.format(clusterName=TestCluster.cluster_name)
    )

    should_return_expected_exception(response, expected_exception, expected_data)


@mock_eks
def test_eks_delete_nodegroup(test_client, create_cluster, create_nodegroup):
    create_cluster()
    create_nodegroup()

    response = test_client.delete(
        Endpoints.DELETE_NODEGROUP.format(
            clusterName=TestNodegroup.cluster_name,
            nodegroupName=TestNodegroup.nodegroup_name,
        )
    )
    result_data = json.loads(response.data.decode(DEFAULT_ENCODING))[
        ResponseAttributes.NODEGROUP
    ]

    assert response.status_code == StatusCodes.OK
    assert result_data[ClusterAttributes.CLUSTER_NAME] == TestNodegroup.cluster_name
    assert (
        result_data[NodegroupAttributes.NODEGROUP_NAME] == TestNodegroup.nodegroup_name
    )
    all_arn_values_should_be_valid(
        expected_arn_values=TestNodegroup.expected_arn_values,
        pattern=RegExTemplates.NODEGROUP_ARN,
        arn_under_test=result_data[NodegroupAttributes.ARN],
    )


@mock_eks
def test_eks_delete_nonexisting_nodegroup(test_client, create_cluster):
    create_cluster()
    expected_exception = ResourceNotFoundException
    expected_msg = NODEGROUP_NOT_FOUND_MSG.format(
        clusterName=TestNodegroup.cluster_name,
        nodegroupName=TestNodegroup.nodegroup_name,
    )
    expected_data = {
        ClusterAttributes.CLUSTER_NAME: TestNodegroup.cluster_name,
        NodegroupAttributes.NODEGROUP_NAME: TestNodegroup.nodegroup_name,
        FargateProfileAttributes.FARGATE_PROFILE_NAME: None,
        AddonAttributes.ADDON_NAME: None,
        ResponseAttributes.MESSAGE: expected_msg,
    }

    response = test_client.delete(
        Endpoints.DELETE_NODEGROUP.format(
            clusterName=TestNodegroup.cluster_name,
            nodegroupName=TestNodegroup.nodegroup_name,
        )
    )

    should_return_expected_exception(response, expected_exception, expected_data)


@mock_eks
def test_eks_delete_nodegroup_nonexisting_cluster(test_client):
    expected_exception = ResourceNotFoundException
    expected_msg = CLUSTER_NOT_FOUND_MSG.format(
        clusterName=TestNodegroup.cluster_name,
        nodegroupName=TestNodegroup.nodegroup_name,
    )
    expected_data = {
        ClusterAttributes.CLUSTER_NAME: None,
        NodegroupAttributes.NODEGROUP_NAME: None,
        FargateProfileAttributes.FARGATE_PROFILE_NAME: None,
        AddonAttributes.ADDON_NAME: None,
        ResponseAttributes.MESSAGE: expected_msg,
    }

    response = test_client.delete(
        Endpoints.DELETE_NODEGROUP.format(
            clusterName=TestNodegroup.cluster_name,
            nodegroupName=TestNodegroup.nodegroup_name,
        )
    )

    should_return_expected_exception(response, expected_exception, expected_data)


def should_return_expected_exception(response, expected_exception, expected_data):
    result_data = json.loads(response.data.decode(DEFAULT_ENCODING))

    assert response.status_code == expected_exception.STATUS
    assert response.headers.get(HttpHeaders.ErrorType) == expected_exception.TYPE
    assert result_data == expected_data
