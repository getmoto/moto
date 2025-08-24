import boto3

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID


@mock_aws
def test_tag_data_source():
    client = boto3.client("quicksight", region_name="us-east-1")
    client.create_data_source(
        AwsAccountId=ACCOUNT_ID,
        DataSourceId="ds1",
        Name="TestDS",
        Type="ATHENA",
        DataSourceParameters={"AthenaParameters": {"WorkGroup": "primary"}},
    )
    arn = f"arn:aws:quicksight:us-east-1:{ACCOUNT_ID}:datasource/ds1"
    client.tag_resource(
        ResourceArn=arn,
        Tags=[{"Key": "env", "Value": "test"}],
    )
    tags = client.list_tags_for_resource(ResourceArn=arn)["Tags"]
    assert {"Key": "env", "Value": "test"} in tags


@mock_aws
def test_untag_data_source():
    client = boto3.client("quicksight", region_name="us-east-1")
    client.create_data_source(
        AwsAccountId=ACCOUNT_ID,
        DataSourceId="ds1",
        Name="TestDS",
        Type="ATHENA",
        DataSourceParameters={"AthenaParameters": {"WorkGroup": "primary"}},
    )
    arn = f"arn:aws:quicksight:us-east-1:{ACCOUNT_ID}:datasource/ds1"
    client.tag_resource(
        ResourceArn=arn,
        Tags=[{"Key": "env", "Value": "test"}],
    )
    tags = client.list_tags_for_resource(ResourceArn=arn)["Tags"]
    assert {"Key": "env", "Value": "test"} in tags

    client.untag_resource(
        ResourceArn=arn,
        TagKeys=["env"],
    )
    tags = client.list_tags_for_resource(ResourceArn=arn)["Tags"]
    assert {"Key": "env", "Value": "test"} not in tags


@mock_aws
def test_tag_dashboard():
    client = boto3.client("quicksight", region_name="eu-west-1")
    client.create_dashboard(
        AwsAccountId=ACCOUNT_ID,
        DashboardId="dash1",
        Name="TestDashboard",
        SourceEntity={
            "SourceTemplate": {
                "DataSetReferences": [
                    {
                        "DataSetPlaceholder": "placeholder",
                        "DataSetArn": f"arn:aws:quicksight:eu-west-1:{ACCOUNT_ID}:dataset/ds1",
                    }
                ],
                "Arn": f"arn:aws:quicksight:us-east-1:{ACCOUNT_ID}:template/template1",
            }
        },
    )
    arn = f"arn:aws:quicksight:us-east-1:{ACCOUNT_ID}:dashboard/dash1"
    client.tag_resource(
        ResourceArn=arn,
        Tags=[{"Key": "team", "Value": "analytics"}],
    )
    tags = client.list_tags_for_resource(ResourceArn=arn)["Tags"]
    assert {"Key": "team", "Value": "analytics"} in tags


@mock_aws
def test_untag_dashboard():
    client = boto3.client("quicksight", region_name="eu-west-1")
    client.create_dashboard(
        AwsAccountId=ACCOUNT_ID,
        DashboardId="dash1",
        Name="TestDashboard",
        SourceEntity={
            "SourceTemplate": {
                "DataSetReferences": [
                    {
                        "DataSetPlaceholder": "placeholder",
                        "DataSetArn": f"arn:aws:quicksight:eu-west-1:{ACCOUNT_ID}:dataset/ds1",
                    }
                ],
                "Arn": f"arn:aws:quicksight:us-east-1:{ACCOUNT_ID}:template/template1",
            }
        },
    )
    arn = f"arn:aws:quicksight:us-east-1:{ACCOUNT_ID}:dashboard/dash1"
    client.tag_resource(
        ResourceArn=arn,
        Tags=[{"Key": "team", "Value": "analytics"}],
    )
    tags = client.list_tags_for_resource(ResourceArn=arn)["Tags"]
    assert {"Key": "team", "Value": "analytics"} in tags

    client.untag_resource(
        ResourceArn=arn,
        TagKeys=["team"],
    )
    tags = client.list_tags_for_resource(ResourceArn=arn)["Tags"]
    assert {"Key": "team", "Value": "analytics"} not in tags


@mock_aws
def test_tag_dataset():
    client = boto3.client("quicksight", region_name="us-west-2")
    client.create_data_set(
        AwsAccountId=ACCOUNT_ID,
        DataSetId="ds1",
        Name="TestDataSet",
        PhysicalTableMap={
            "table1": {
                "RelationalTable": {
                    "DataSourceArn": f"arn:aws:quicksight:us-west-1:{ACCOUNT_ID}:datasource/ds1",
                    "Schema": "public",
                    "Name": "table1",
                    "InputColumns": [
                        {"Name": "col1", "Type": "STRING"},
                    ],
                }
            }
        },
        ImportMode="SPICE",
    )
    arn = f"arn:aws:quicksight:us-west-2:{ACCOUNT_ID}:dataset/ds1"
    client.tag_resource(
        ResourceArn=arn,
        Tags=[{"Key": "project", "Value": "tagging"}],
    )
    tags = client.list_tags_for_resource(ResourceArn=arn)["Tags"]
    assert {"Key": "project", "Value": "tagging"} in tags


@mock_aws
def test_untag_dataset():
    client = boto3.client("quicksight", region_name="us-west-2")
    client.create_data_set(
        AwsAccountId=ACCOUNT_ID,
        DataSetId="ds1",
        Name="TestDataSet",
        PhysicalTableMap={
            "table1": {
                "RelationalTable": {
                    "DataSourceArn": f"arn:aws:quicksight:us-west-1:{ACCOUNT_ID}:datasource/ds1",
                    "Schema": "public",
                    "Name": "table1",
                    "InputColumns": [
                        {"Name": "col1", "Type": "STRING"},
                    ],
                }
            }
        },
        ImportMode="SPICE",
    )
    arn = f"arn:aws:quicksight:us-west-2:{ACCOUNT_ID}:dataset/ds1"
    client.tag_resource(
        ResourceArn=arn,
        Tags=[{"Key": "project", "Value": "tagging"}],
    )
    tags = client.list_tags_for_resource(ResourceArn=arn)["Tags"]
    assert {"Key": "project", "Value": "tagging"} in tags

    client.untag_resource(
        ResourceArn=arn,
        TagKeys=["project"],
    )
    tags = client.list_tags_for_resource(ResourceArn=arn)["Tags"]
    assert {"Key": "project", "Value": "tagging"} not in tags


@mock_aws
def test_tag_user():
    client = boto3.client("quicksight", region_name="us-east-1")
    client.register_user(
        AwsAccountId=ACCOUNT_ID,
        Namespace="default",
        Email="user@example.com",
        IdentityType="QUICKSIGHT",
        UserName="testuser",
        UserRole="READER",
    )
    arn = f"arn:aws:quicksight:us-east-1:{ACCOUNT_ID}:user/default/testuser"
    client.tag_resource(
        ResourceArn=arn,
        Tags=[{"Key": "department", "Value": "admin"}],
    )
    tags = client.list_tags_for_resource(ResourceArn=arn)["Tags"]
    assert {"Key": "department", "Value": "admin"} in tags


@mock_aws
def test_untag_user():
    client = boto3.client("quicksight", region_name="us-east-1")
    client.register_user(
        AwsAccountId=ACCOUNT_ID,
        Namespace="default",
        Email="user@example.com",
        IdentityType="QUICKSIGHT",
        UserName="testuser",
        UserRole="READER",
    )
    arn = f"arn:aws:quicksight:us-east-1:{ACCOUNT_ID}:user/default/testuser"
    client.tag_resource(
        ResourceArn=arn,
        Tags=[{"Key": "department", "Value": "admin"}],
    )
    tags = client.list_tags_for_resource(ResourceArn=arn)["Tags"]
    assert {"Key": "department", "Value": "admin"} in tags

    client.untag_resource(
        ResourceArn=arn,
        TagKeys=["department"],
    )
    tags = client.list_tags_for_resource(ResourceArn=arn)["Tags"]
    assert {"Key": "department", "Value": "admin"} not in tags
