import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


def _create_service(client) -> str:
    operation_id = client.create_http_namespace(Name="mynamespace")["OperationId"]
    namespace_id = client.get_operation(OperationId=operation_id)["Operation"][
        "Targets"
    ]["NAMESPACE"]
    return client.create_service(Name="my service", NamespaceId=namespace_id)[
        "Service"
    ]["Id"]


@mock_aws
def test_get_service_attributes_defaults_to_empty():
    client = boto3.client("servicediscovery", region_name="eu-west-1")
    service_id = _create_service(client)

    resp = client.get_service_attributes(ServiceId=service_id)

    attrs = resp["ServiceAttributes"]
    assert attrs["ServiceArn"].endswith(f"service/{service_id}")
    assert attrs["ResourceOwner"] == ACCOUNT_ID
    assert attrs["Attributes"] == {}


@mock_aws
def test_update_and_get_service_attributes():
    client = boto3.client("servicediscovery", region_name="ap-southeast-1")
    service_id = _create_service(client)

    client.update_service_attributes(
        ServiceId=service_id,
        Attributes={"key1": "value1", "key2": "value2"},
    )

    attrs = client.get_service_attributes(ServiceId=service_id)["ServiceAttributes"]
    assert attrs["Attributes"] == {"key1": "value1", "key2": "value2"}


@mock_aws
def test_update_service_attributes_merges_existing():
    client = boto3.client("servicediscovery", region_name="ap-southeast-1")
    service_id = _create_service(client)

    client.update_service_attributes(ServiceId=service_id, Attributes={"key1": "old"})
    client.update_service_attributes(
        ServiceId=service_id, Attributes={"key1": "new", "key2": "value2"}
    )

    attrs = client.get_service_attributes(ServiceId=service_id)["ServiceAttributes"]
    assert attrs["Attributes"] == {"key1": "new", "key2": "value2"}


@mock_aws
def test_delete_service_attributes():
    client = boto3.client("servicediscovery", region_name="eu-west-1")
    service_id = _create_service(client)

    client.update_service_attributes(
        ServiceId=service_id,
        Attributes={"key1": "value1", "key2": "value2", "key3": "value3"},
    )

    # Deleting unknown keys alongside known ones is a no-op for the unknown ones
    client.delete_service_attributes(
        ServiceId=service_id, Attributes=["key1", "unknown"]
    )

    attrs = client.get_service_attributes(ServiceId=service_id)["ServiceAttributes"]
    assert attrs["Attributes"] == {"key2": "value2", "key3": "value3"}


@mock_aws
def test_update_service_attributes_limit_exceeded():
    client = boto3.client("servicediscovery", region_name="ap-southeast-1")
    service_id = _create_service(client)

    client.update_service_attributes(
        ServiceId=service_id,
        Attributes={f"key{i}": str(i) for i in range(30)},
    )

    with pytest.raises(ClientError) as exc:
        client.update_service_attributes(
            ServiceId=service_id, Attributes={"one_too_many": "value"}
        )
    assert (
        exc.value.response["Error"]["Code"] == "ServiceAttributesLimitExceededException"
    )


@mock_aws
def test_get_service_attributes_unknown_service():
    client = boto3.client("servicediscovery", region_name="ap-southeast-1")
    with pytest.raises(ClientError) as exc:
        client.get_service_attributes(ServiceId="unknown")
    assert exc.value.response["Error"]["Code"] == "ServiceNotFound"


@mock_aws
def test_update_service_attributes_unknown_service():
    client = boto3.client("servicediscovery", region_name="ap-southeast-1")
    with pytest.raises(ClientError) as exc:
        client.update_service_attributes(
            ServiceId="unknown", Attributes={"key1": "value1"}
        )
    assert exc.value.response["Error"]["Code"] == "ServiceNotFound"


@mock_aws
def test_delete_service_attributes_unknown_service():
    client = boto3.client("servicediscovery", region_name="ap-southeast-1")
    with pytest.raises(ClientError) as exc:
        client.delete_service_attributes(ServiceId="unknown", Attributes=["key1"])
    assert exc.value.response["Error"]["Code"] == "ServiceNotFound"
