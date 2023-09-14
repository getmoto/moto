import boto3
from botocore.exceptions import ClientError
import pytest

from moto import mock_forecast
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID

region = "us-east-1"
account_id = None
valid_domains = [
    "RETAIL",
    "CUSTOM",
    "INVENTORY_PLANNING",
    "EC2_CAPACITY",
    "WORK_FORCE",
    "WEB_TRAFFIC",
    "METRICS",
]


@pytest.mark.parametrize("domain", valid_domains)
@mock_forecast
def test_forecast_dataset_group_create(domain):
    name = "example_dataset_group"
    client = boto3.client("forecast", region_name=region)
    response = client.create_dataset_group(DatasetGroupName=name, Domain=domain)
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert response["DatasetGroupArn"] == (
        f"arn:aws:forecast:{region}:{ACCOUNT_ID}:dataset-group/{name}"
    )


@mock_forecast
def test_forecast_dataset_group_create_invalid_domain():
    name = "example_dataset_group"
    client = boto3.client("forecast", region_name=region)
    invalid_domain = "INVALID"

    with pytest.raises(ClientError) as exc:
        client.create_dataset_group(DatasetGroupName=name, Domain=invalid_domain)
    assert exc.value.response["Error"]["Code"] == "ValidationException"
    assert exc.value.response["Error"]["Message"] == (
        f"1 validation error detected: Value '{invalid_domain}' at 'domain' "
        "failed to satisfy constraint: Member must satisfy enum value set "
        "['INVENTORY_PLANNING', 'METRICS', 'RETAIL', 'EC2_CAPACITY', "
        "'CUSTOM', 'WEB_TRAFFIC', 'WORK_FORCE']"
    )


@pytest.mark.parametrize("name", [" ", "a" * 64])
@mock_forecast
def test_forecast_dataset_group_create_invalid_name(name):
    client = boto3.client("forecast", region_name=region)

    with pytest.raises(ClientError) as exc:
        client.create_dataset_group(DatasetGroupName=name, Domain="CUSTOM")
    assert exc.value.response["Error"]["Code"] == "ValidationException"
    assert (
        f"1 validation error detected: Value '{name}' at 'datasetGroupName' "
        "failed to satisfy constraint: Member must"
    ) in exc.value.response["Error"]["Message"]


@mock_forecast
def test_forecast_dataset_group_create_duplicate_fails():
    client = boto3.client("forecast", region_name=region)
    client.create_dataset_group(DatasetGroupName="name", Domain="RETAIL")

    with pytest.raises(ClientError) as exc:
        client.create_dataset_group(DatasetGroupName="name", Domain="RETAIL")

    assert exc.value.response["Error"]["Code"] == "ResourceAlreadyExistsException"


@mock_forecast
def test_forecast_dataset_group_list_default_empty():
    client = boto3.client("forecast", region_name=region)

    resp = client.list_dataset_groups()
    assert resp["DatasetGroups"] == []


@mock_forecast
def test_forecast_dataset_group_list_some():
    client = boto3.client("forecast", region_name=region)

    client.create_dataset_group(DatasetGroupName="hello", Domain="CUSTOM")
    result = client.list_dataset_groups()

    assert len(result["DatasetGroups"]) == 1
    assert result["DatasetGroups"][0]["DatasetGroupArn"] == (
        f"arn:aws:forecast:{region}:{ACCOUNT_ID}:dataset-group/hello"
    )


@mock_forecast
def test_forecast_delete_dataset_group():
    dataset_group_name = "name"
    dataset_group_arn = (
        f"arn:aws:forecast:{region}:{ACCOUNT_ID}:dataset-group/{dataset_group_name}"
    )
    client = boto3.client("forecast", region_name=region)
    client.create_dataset_group(DatasetGroupName=dataset_group_name, Domain="CUSTOM")
    client.delete_dataset_group(DatasetGroupArn=dataset_group_arn)


@mock_forecast
def test_forecast_delete_dataset_group_missing():
    client = boto3.client("forecast", region_name=region)
    missing_dsg_arn = f"arn:aws:forecast:{region}:{ACCOUNT_ID}:dataset-group/missing"

    with pytest.raises(ClientError) as exc:
        client.delete_dataset_group(DatasetGroupArn=missing_dsg_arn)
    assert exc.value.response["Error"]["Code"] == "ResourceNotFoundException"
    assert (
        exc.value.response["Error"]["Message"] == f"No resource found {missing_dsg_arn}"
    )


@mock_forecast
def test_forecast_update_dataset_arns_empty():
    dataset_group_name = "name"
    dataset_group_arn = (
        f"arn:aws:forecast:{region}:{ACCOUNT_ID}:dataset-group/{dataset_group_name}"
    )
    client = boto3.client("forecast", region_name=region)
    client.create_dataset_group(DatasetGroupName=dataset_group_name, Domain="CUSTOM")
    client.update_dataset_group(DatasetGroupArn=dataset_group_arn, DatasetArns=[])


@mock_forecast
def test_forecast_update_dataset_group_not_found():
    client = boto3.client("forecast", region_name=region)
    dataset_group_arn = f"arn:aws:forecast:{region}:{ACCOUNT_ID}:dataset-group/test"
    with pytest.raises(ClientError) as exc:
        client.update_dataset_group(DatasetGroupArn=dataset_group_arn, DatasetArns=[])
    assert exc.value.response["Error"]["Code"] == "ResourceNotFoundException"
    assert (
        exc.value.response["Error"]["Message"]
        == f"No resource found {dataset_group_arn}"
    )


@mock_forecast
def test_describe_dataset_group():
    name = "test"
    client = boto3.client("forecast", region_name=region)
    dataset_group_arn = f"arn:aws:forecast:{region}:{ACCOUNT_ID}:dataset-group/{name}"
    client.create_dataset_group(DatasetGroupName=name, Domain="CUSTOM")
    result = client.describe_dataset_group(DatasetGroupArn=dataset_group_arn)
    assert result.get("DatasetGroupArn") == dataset_group_arn
    assert result.get("Domain") == "CUSTOM"
    assert result.get("DatasetArns") == []


@mock_forecast
def test_describe_dataset_group_missing():
    client = boto3.client("forecast", region_name=region)
    dataset_group_arn = f"arn:aws:forecast:{region}:{ACCOUNT_ID}:dataset-group/name"
    with pytest.raises(ClientError) as exc:
        client.describe_dataset_group(DatasetGroupArn=dataset_group_arn)
    assert exc.value.response["Error"]["Code"] == "ResourceNotFoundException"
    assert (
        exc.value.response["Error"]["Message"]
        == f"No resource found {dataset_group_arn}"
    )


@mock_forecast
def test_create_dataset_group_missing_datasets():
    client = boto3.client("forecast", region_name=region)
    dataset_arn = f"arn:aws:forecast:{region}:{ACCOUNT_ID}:dataset-group/name"
    with pytest.raises(ClientError) as exc:
        client.create_dataset_group(
            DatasetGroupName="name", Domain="CUSTOM", DatasetArns=[dataset_arn]
        )
    assert exc.value.response["Error"]["Code"] == "InvalidInputException"
    assert exc.value.response["Error"]["Message"] == (
        f"Dataset arns: [{dataset_arn}] are not found"
    )


@mock_forecast
def test_update_dataset_group_missing_datasets():
    name = "test"
    client = boto3.client("forecast", region_name=region)
    dataset_group_arn = f"arn:aws:forecast:{region}:{ACCOUNT_ID}:dataset-group/{name}"
    client.create_dataset_group(DatasetGroupName=name, Domain="CUSTOM")
    dataset_arn = f"arn:aws:forecast:{region}:{ACCOUNT_ID}:dataset/name"

    with pytest.raises(ClientError) as exc:
        client.update_dataset_group(
            DatasetGroupArn=dataset_group_arn, DatasetArns=[dataset_arn]
        )
    assert exc.value.response["Error"]["Code"] == "InvalidInputException"
    assert exc.value.response["Error"]["Message"] == (
        f"Dataset arns: [{dataset_arn}] are not found"
    )
