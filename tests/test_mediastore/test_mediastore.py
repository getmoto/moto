import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws

region = "eu-west-1"


@mock_aws
def test_create_container_succeeds():
    client = boto3.client("mediastore", region_name=region)
    response = client.create_container(
        ContainerName="Awesome container!", Tags=[{"Key": "customer"}]
    )
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

    container = response["Container"]
    assert container["ARN"] == f"arn:aws:mediastore:container:{container['Name']}"
    assert container["Name"] == "Awesome container!"
    assert container["Status"] == "CREATING"


@mock_aws
def test_describe_container_succeeds():
    client = boto3.client("mediastore", region_name=region)
    name = "Awesome container!"
    client.create_container(ContainerName=name, Tags=[{"Key": "customer"}])

    response = client.describe_container(ContainerName=name)
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

    container = response["Container"]
    assert container["ARN"] == f"arn:aws:mediastore:container:{name}"
    assert container["Name"] == name
    assert container["Status"] == "ACTIVE"


@mock_aws
def test_list_containers_succeeds():
    client = boto3.client("mediastore", region_name=region)
    name = "Awesome container!"
    client.create_container(ContainerName=name, Tags=[{"Key": "customer"}])
    containers = client.list_containers()["Containers"]
    assert len(containers) == 1

    client.create_container(ContainerName=f"{name}2", Tags=[{"Key": "customer"}])
    containers = client.list_containers()["Containers"]
    assert len(containers) == 2


@mock_aws
def test_describe_container_raises_error_if_container_does_not_exist():
    client = boto3.client("mediastore", region_name=region)
    with pytest.raises(ClientError) as ex:
        client.describe_container(ContainerName="container-name")
    assert ex.value.response["Error"]["Code"] == "ResourceNotFoundException"


@mock_aws
def test_put_lifecycle_policy_succeeds():
    client = boto3.client("mediastore", region_name=region)
    name = "container-name"
    client.create_container(ContainerName=name, Tags=[{"Key": "customer"}])

    client.put_lifecycle_policy(ContainerName=name, LifecyclePolicy="lifecycle-policy")
    response = client.get_lifecycle_policy(ContainerName=name)
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert response["LifecyclePolicy"] == "lifecycle-policy"


@mock_aws
def test_put_lifecycle_policy_raises_error_if_container_does_not_exist():
    client = boto3.client("mediastore", region_name=region)
    with pytest.raises(ClientError) as ex:
        client.put_lifecycle_policy(ContainerName="name", LifecyclePolicy="policy")
    assert ex.value.response["Error"]["Code"] == "ResourceNotFoundException"


@mock_aws
def test_get_lifecycle_policy_raises_error_if_container_does_not_exist():
    client = boto3.client("mediastore", region_name=region)
    with pytest.raises(ClientError) as ex:
        client.get_lifecycle_policy(ContainerName="container-name")
    assert ex.value.response["Error"]["Code"] == "ResourceNotFoundException"


@mock_aws
def test_get_lifecycle_policy_raises_error_if_container_does_not_have_lifecycle_policy():
    client = boto3.client("mediastore", region_name=region)
    client.create_container(ContainerName="container-name", Tags=[{"Key": "customer"}])
    with pytest.raises(ClientError) as ex:
        client.get_lifecycle_policy(ContainerName="container-name")
    assert ex.value.response["Error"]["Code"] == "PolicyNotFoundException"


@mock_aws
def test_put_container_policy_succeeds():
    client = boto3.client("mediastore", region_name=region)
    name = "container-name"
    client.create_container(ContainerName=name)

    client.put_container_policy(ContainerName=name, Policy="container-policy")
    response = client.get_container_policy(ContainerName=name)
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert response["Policy"] == "container-policy"


@mock_aws
def test_put_container_policy_raises_error_if_container_does_not_exist():
    client = boto3.client("mediastore", region_name=region)
    with pytest.raises(ClientError) as ex:
        client.put_container_policy(ContainerName="name", Policy="policy")
    assert ex.value.response["Error"]["Code"] == "ResourceNotFoundException"


@mock_aws
def test_get_container_policy_raises_error_if_container_does_not_exist():
    client = boto3.client("mediastore", region_name=region)
    with pytest.raises(ClientError) as ex:
        client.get_container_policy(ContainerName="container-name")
    assert ex.value.response["Error"]["Code"] == "ResourceNotFoundException"


@mock_aws
def test_get_container_policy_raises_error_if_container_does_not_have_container_policy():
    client = boto3.client("mediastore", region_name=region)
    client.create_container(ContainerName="container-name", Tags=[{"Key": "customer"}])
    with pytest.raises(ClientError) as ex:
        client.get_container_policy(ContainerName="container-name")
    assert ex.value.response["Error"]["Code"] == "PolicyNotFoundException"


@mock_aws
def test_put_metric_policy_succeeds():
    client = boto3.client("mediastore", region_name=region)
    name = "container-name"
    client.create_container(ContainerName=name)
    client.put_metric_policy(
        ContainerName=name,
        MetricPolicy={"ContainerLevelMetrics": "ENABLED"},
    )
    response = client.get_metric_policy(ContainerName=name)
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert response["MetricPolicy"] == {"ContainerLevelMetrics": "ENABLED"}


@mock_aws
def test_put_metric_policy_raises_error_if_container_does_not_exist():
    client = boto3.client("mediastore", region_name=region)
    with pytest.raises(ClientError) as ex:
        client.put_metric_policy(
            ContainerName="container-name",
            MetricPolicy={"ContainerLevelMetrics": "ENABLED"},
        )
    assert ex.value.response["Error"]["Code"] == "ResourceNotFoundException"


@mock_aws
def test_get_metric_policy_raises_error_if_container_does_not_exist():
    client = boto3.client("mediastore", region_name=region)
    with pytest.raises(ClientError) as ex:
        client.get_metric_policy(ContainerName="container-name")
    assert ex.value.response["Error"]["Code"] == "ResourceNotFoundException"


@mock_aws
def test_get_metric_policy_raises_error_if_container_does_not_have_metric_policy():
    client = boto3.client("mediastore", region_name=region)
    client.create_container(ContainerName="container-name", Tags=[{"Key": "customer"}])
    with pytest.raises(ClientError) as ex:
        client.get_metric_policy(ContainerName="container-name")
    assert ex.value.response["Error"]["Code"] == "PolicyNotFoundException"


@mock_aws
def test_list_tags_for_resource():
    client = boto3.client("mediastore", region_name=region)
    tags = [{"Key": "customer"}]

    name = "Awesome container!"
    client.create_container(ContainerName=name, Tags=tags)

    response = client.list_tags_for_resource(Resource=name)
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert response["Tags"] == tags


@mock_aws
def test_list_tags_for_resource_return_none_if_no_tags():
    client = boto3.client("mediastore", region_name=region)

    name = "Awesome container!"
    client.create_container(ContainerName=name)

    response = client.list_tags_for_resource(Resource=name)
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert response.get("Tags") is None


@mock_aws
def test_list_tags_for_resource_return_error_for_unknown_resource():
    client = boto3.client("mediastore", region_name=region)
    with pytest.raises(ClientError) as ex:
        client.list_tags_for_resource(Resource="not_existing")
    assert ex.value.response["Error"]["Code"] == "ContainerNotFoundException"


@mock_aws
def test_delete_container():
    client = boto3.client("mediastore", region_name=region)
    container_name = "Awesome container!"
    client.create_container(ContainerName=container_name)

    response = client.delete_container(ContainerName=container_name)
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

    containers = client.list_containers()["Containers"]
    assert not any(d["Name"] == container_name for d in containers)


@mock_aws
def test_delete_container_raise_error_if_container_not_found():
    client = boto3.client("mediastore", region_name=region)
    client.create_container(ContainerName="Awesome container!")

    with pytest.raises(ClientError) as ex:
        client.delete_container(ContainerName="notAvailable")
    assert ex.value.response["Error"]["Code"] == "ContainerNotFoundException"
