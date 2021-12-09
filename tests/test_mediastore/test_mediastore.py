import boto3
import pytest
import sure  # noqa # pylint: disable=unused-import
from botocore.exceptions import ClientError

from moto import mock_mediastore

region = "eu-west-1"


@mock_mediastore
def test_create_container_succeeds():
    client = boto3.client("mediastore", region_name=region)
    response = client.create_container(
        ContainerName="Awesome container!", Tags=[{"Key": "customer"}]
    )
    container = response["Container"]
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    container["ARN"].should.equal(
        "arn:aws:mediastore:container:{}".format(container["Name"])
    )
    container["Name"].should.equal("Awesome container!")
    container["Status"].should.equal("CREATING")


@mock_mediastore
def test_describe_container_succeeds():
    client = boto3.client("mediastore", region_name=region)
    create_response = client.create_container(
        ContainerName="Awesome container!", Tags=[{"Key": "customer"}]
    )
    container_name = create_response["Container"]["Name"]
    response = client.describe_container(ContainerName=container_name)
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    container = response["Container"]
    container["ARN"].should.equal(
        "arn:aws:mediastore:container:{}".format(container["Name"])
    )
    container["Name"].should.equal("Awesome container!")
    container["Status"].should.equal("ACTIVE")


@mock_mediastore
def test_list_containers_succeeds():
    client = boto3.client("mediastore", region_name=region)
    client.create_container(
        ContainerName="Awesome container!", Tags=[{"Key": "customer"}]
    )
    list_response = client.list_containers(NextToken="next-token", MaxResults=123)
    containers_list = list_response["Containers"]
    len(containers_list).should.equal(1)
    client.create_container(
        ContainerName="Awesome container2!", Tags=[{"Key": "customer"}]
    )
    list_response = client.list_containers(NextToken="next-token", MaxResults=123)
    containers_list = list_response["Containers"]
    len(containers_list).should.equal(2)


@mock_mediastore
def test_describe_container_raises_error_if_container_does_not_exist():
    client = boto3.client("mediastore", region_name=region)
    with pytest.raises(ClientError) as ex:
        client.describe_container(ContainerName="container-name")
    ex.value.response["Error"]["Code"].should.equal("ResourceNotFoundException")


@mock_mediastore
def test_put_lifecycle_policy_succeeds():
    client = boto3.client("mediastore", region_name=region)
    container_response = client.create_container(
        ContainerName="container-name", Tags=[{"Key": "customer"}]
    )
    container = container_response["Container"]
    client.put_lifecycle_policy(
        ContainerName=container["Name"], LifecyclePolicy="lifecycle-policy"
    )
    response = client.get_lifecycle_policy(ContainerName=container["Name"])
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    response["LifecyclePolicy"].should.equal("lifecycle-policy")


@mock_mediastore
def test_put_lifecycle_policy_raises_error_if_container_does_not_exist():
    client = boto3.client("mediastore", region_name=region)
    with pytest.raises(ClientError) as ex:
        client.put_lifecycle_policy(
            ContainerName="container-name", LifecyclePolicy="lifecycle-policy"
        )
    ex.value.response["Error"]["Code"].should.equal("ResourceNotFoundException")


@mock_mediastore
def test_get_lifecycle_policy_raises_error_if_container_does_not_exist():
    client = boto3.client("mediastore", region_name=region)
    with pytest.raises(ClientError) as ex:
        client.get_lifecycle_policy(ContainerName="container-name")
    ex.value.response["Error"]["Code"].should.equal("ResourceNotFoundException")


@mock_mediastore
def test_get_lifecycle_policy_raises_error_if_container_does_not_have_lifecycle_policy():
    client = boto3.client("mediastore", region_name=region)
    client.create_container(ContainerName="container-name", Tags=[{"Key": "customer"}])
    with pytest.raises(ClientError) as ex:
        client.get_lifecycle_policy(ContainerName="container-name")
    ex.value.response["Error"]["Code"].should.equal("PolicyNotFoundException")


@mock_mediastore
def test_put_container_policy_succeeds():
    client = boto3.client("mediastore", region_name=region)
    container_response = client.create_container(
        ContainerName="container-name", Tags=[{"Key": "customer"}]
    )
    container = container_response["Container"]
    response = client.put_container_policy(
        ContainerName=container["Name"], Policy="container-policy"
    )
    response = client.get_container_policy(ContainerName=container["Name"])
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    response["Policy"].should.equal("container-policy")


@mock_mediastore
def test_put_container_policy_raises_error_if_container_does_not_exist():
    client = boto3.client("mediastore", region_name=region)
    with pytest.raises(ClientError) as ex:
        client.put_container_policy(
            ContainerName="container-name", Policy="container-policy"
        )
    ex.value.response["Error"]["Code"].should.equal("ResourceNotFoundException")


@mock_mediastore
def test_get_container_policy_raises_error_if_container_does_not_exist():
    client = boto3.client("mediastore", region_name=region)
    with pytest.raises(ClientError) as ex:
        client.get_container_policy(ContainerName="container-name")
    ex.value.response["Error"]["Code"].should.equal("ResourceNotFoundException")


@mock_mediastore
def test_get_container_policy_raises_error_if_container_does_not_have_container_policy():
    client = boto3.client("mediastore", region_name=region)
    client.create_container(ContainerName="container-name", Tags=[{"Key": "customer"}])
    with pytest.raises(ClientError) as ex:
        client.get_container_policy(ContainerName="container-name")
    ex.value.response["Error"]["Code"].should.equal("PolicyNotFoundException")


@mock_mediastore
def test_put_metric_policy_succeeds():
    client = boto3.client("mediastore", region_name=region)
    container_response = client.create_container(
        ContainerName="container-name", Tags=[{"Key": "customer"}]
    )
    container = container_response["Container"]
    response = client.put_metric_policy(
        ContainerName=container["Name"],
        MetricPolicy={"ContainerLevelMetrics": "ENABLED"},
    )
    response = client.get_metric_policy(ContainerName=container["Name"])
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    response["MetricPolicy"].should.equal({"ContainerLevelMetrics": "ENABLED"})


@mock_mediastore
def test_put_metric_policy_raises_error_if_container_does_not_exist():
    client = boto3.client("mediastore", region_name=region)
    with pytest.raises(ClientError) as ex:
        client.put_metric_policy(
            ContainerName="container-name",
            MetricPolicy={"ContainerLevelMetrics": "ENABLED"},
        )
    ex.value.response["Error"]["Code"].should.equal("ResourceNotFoundException")


@mock_mediastore
def test_get_metric_policy_raises_error_if_container_does_not_exist():
    client = boto3.client("mediastore", region_name=region)
    with pytest.raises(ClientError) as ex:
        client.get_metric_policy(ContainerName="container-name")
    ex.value.response["Error"]["Code"].should.equal("ResourceNotFoundException")


@mock_mediastore
def test_get_metric_policy_raises_error_if_container_does_not_have_metric_policy():
    client = boto3.client("mediastore", region_name=region)
    client.create_container(ContainerName="container-name", Tags=[{"Key": "customer"}])
    with pytest.raises(ClientError) as ex:
        client.get_metric_policy(ContainerName="container-name")
    ex.value.response["Error"]["Code"].should.equal("PolicyNotFoundException")


@mock_mediastore
def test_list_tags_for_resource():
    client = boto3.client("mediastore", region_name=region)
    tags = [{"Key": "customer"}]

    create_response = client.create_container(
        ContainerName="Awesome container!", Tags=tags
    )
    container = create_response["Container"]
    response = client.list_tags_for_resource(Resource=container["Name"])
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    response["Tags"].should.equal(tags)


@mock_mediastore
def test_list_tags_for_resource_return_none_if_no_tags():
    client = boto3.client("mediastore", region_name=region)

    create_response = client.create_container(ContainerName="Awesome container!")
    container = create_response["Container"]
    response = client.list_tags_for_resource(Resource=container["Name"])
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    response.get("Tags").should.equal(None)


@mock_mediastore
def test_list_tags_for_resource_return_error_for_unknown_resource():
    client = boto3.client("mediastore", region_name=region)
    with pytest.raises(ClientError) as ex:
        client.list_tags_for_resource(Resource="not_existing")
    ex.value.response["Error"]["Code"].should.equal("ContainerNotFoundException")


@mock_mediastore
def test_delete_container():
    client = boto3.client("mediastore", region_name=region)
    container_name = "Awesome container!"
    create_response = client.create_container(ContainerName=container_name)
    container = create_response["Container"]
    response = client.delete_container(ContainerName=container["Name"])
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    containers = client.list_containers(NextToken="next-token")["Containers"]
    container_exists = any(d["Name"] == container_name for d in containers)
    container_exists.should.equal(False)


@mock_mediastore
def test_delete_container_raise_error_if_container_not_found():
    client = boto3.client("mediastore", region_name=region)
    client.create_container(ContainerName="Awesome container!")

    with pytest.raises(ClientError) as ex:
        client.delete_container(ContainerName="notAvailable")
    ex.value.response["Error"]["Code"].should.equal("ContainerNotFoundException")
