import boto3

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID


@mock_aws
def test_create_data_source():
    client = boto3.client("quicksight", region_name="us-east-2")
    resp = client.create_data_source(
        AwsAccountId=ACCOUNT_ID,
        DataSourceId="my-test-datasource",
        Name="My Test DataSource",
        Type="ATHENA",
        DataSourceParameters={"AthenaParameters": {"WorkGroup": "primary"}},
    )

    assert resp["Arn"] == (
        f"arn:aws:quicksight:us-east-2:{ACCOUNT_ID}:datasource/my-test-datasource"
    )
    assert resp["DataSourceId"] == "my-test-datasource"
    assert resp["CreationStatus"] == "CREATION_SUCCESSFUL"
    assert resp["Status"] == 200


@mock_aws
def test_describe_data_source():
    client = boto3.client("quicksight", region_name="us-east-2")
    for i in range(3):
        client.create_data_source(
            AwsAccountId=ACCOUNT_ID,
            DataSourceId=f"my-test-datasource-{i}",
            Name=f"My Test DataSource {i}",
            Type="ATHENA",
            DataSourceParameters={"AthenaParameters": {"WorkGroup": "primary"}},
        )

    resp = client.describe_data_source(
        AwsAccountId=ACCOUNT_ID, DataSourceId="my-test-datasource-1"
    )

    ds = resp["DataSource"]

    assert ds["Arn"] == (
        f"arn:aws:quicksight:us-east-2:{ACCOUNT_ID}:datasource/my-test-datasource-1"
    )
    assert ds["DataSourceId"] == "my-test-datasource-1"
    assert ds["Name"] == "My Test DataSource 1"
    assert ds["Status"] == "CREATION_SUCCESSFUL"
    assert ds["Type"] == "ATHENA"
    assert ds["DataSourceParameters"] == {"AthenaParameters": {"WorkGroup": "primary"}}
    assert resp["Status"] == 200


@mock_aws
def test_update_data_source():
    client = boto3.client("quicksight", region_name="us-east-2")
    client.create_data_source(
        AwsAccountId=ACCOUNT_ID,
        DataSourceId="my-test-datasource",
        Name="My Test DataSource",
        Type="ATHENA",
        DataSourceParameters={"AthenaParameters": {"WorkGroup": "primary"}},
    )

    original_ds = client.describe_data_source(
        AwsAccountId=ACCOUNT_ID, DataSourceId="my-test-datasource"
    )["DataSource"]

    resp = client.update_data_source(
        AwsAccountId=ACCOUNT_ID,
        DataSourceId="my-test-datasource",
        Name="My Updated Test DataSource",
        DataSourceParameters={"AthenaParameters": {"WorkGroup": "secondary"}},
    )

    updated_ds = client.describe_data_source(
        AwsAccountId=ACCOUNT_ID, DataSourceId="my-test-datasource"
    )["DataSource"]

    assert original_ds["LastUpdatedTime"] < updated_ds["LastUpdatedTime"]
    assert resp["Arn"] == (
        f"arn:aws:quicksight:us-east-2:{ACCOUNT_ID}:datasource/my-test-datasource"
    )
    assert resp["DataSourceId"] == "my-test-datasource"
    assert resp["UpdateStatus"] == "UPDATE_SUCCESSFUL"
    assert resp["Status"] == 200


@mock_aws
def test_list_data_sources():
    client = boto3.client("quicksight", region_name="ap-southeast-1")
    for i in range(5):
        client.create_data_source(
            AwsAccountId=ACCOUNT_ID,
            DataSourceId=f"my-test-datasource-{i}",
            Name=f"My Test DataSource {i}",
            Type="ATHENA",
            DataSourceParameters={"AthenaParameters": {"WorkGroup": "primary"}},
        )

    resp = client.list_data_sources(AwsAccountId=ACCOUNT_ID)

    assert len(resp["DataSources"]) == 5
    ds = resp["DataSources"][0]
    assert "Arn" in ds
    assert "DataSourceId" in ds
    assert "Name" in ds
    assert "Type" in ds
    assert "CreatedTime" in ds
    assert "LastUpdatedTime" in ds
    assert resp["Status"] == 200


@mock_aws
def test_delete_data_source():
    client = boto3.client("quicksight", region_name="us-east-2")
    for i in range(3):
        client.create_data_source(
            AwsAccountId=ACCOUNT_ID,
            DataSourceId=f"my-test-datasource-{i}",
            Name=f"My Test DataSource {i}",
            Type="ATHENA",
            DataSourceParameters={"AthenaParameters": {"WorkGroup": "primary"}},
        )

    client.delete_data_source(
        AwsAccountId=ACCOUNT_ID, DataSourceId="my-test-datasource-1"
    )
    resp = client.list_data_sources(AwsAccountId=ACCOUNT_ID)
    assert len(resp["DataSources"]) == 2
