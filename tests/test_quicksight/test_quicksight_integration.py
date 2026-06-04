import boto3

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID


@mock_aws
def test_get_tag_and_untag_resources_quicksight_data_sources():
    client = boto3.client("quicksight", region_name="us-east-1")
    rtapi = boto3.client("resourcegroupstaggingapi", region_name="us-east-1")

    source_arn = client.create_data_source(
        AwsAccountId=ACCOUNT_ID,
        DataSourceId="ds1",
        Name="TestDataSource",
        Type="ATHENA",
        DataSourceParameters={"AthenaParameters": {"WorkGroup": "primary"}},
        Tags=[{"Key": "Test", "Value": "1"}],
    )["Arn"]

    # GetResources returns the data source
    resp = rtapi.get_resources(ResourceTypeFilters=["quicksight:data_sources"])
    assert len(resp["ResourceTagMappingList"]) == 1
    assert resp["ResourceTagMappingList"][0]["ResourceARN"] == source_arn
    assert resp["ResourceTagMappingList"][0]["Tags"] == [{"Key": "Test", "Value": "1"}]

    # Add a tag through the Resource Groups Tagging API
    failed = rtapi.tag_resources(ResourceARNList=[source_arn], Tags={"Test2": "2"})
    assert failed["FailedResourcesMap"] == {}

    resp = rtapi.get_resources(
        ResourceTypeFilters=["quicksight:data_sources"],
        TagFilters=[{"Key": "Test2", "Values": ["2"]}],
    )
    assert len(resp["ResourceTagMappingList"]) == 1
    assert resp["ResourceTagMappingList"][0]["ResourceARN"] == source_arn

    # Remove the original tag through the Resource Groups Tagging API
    failed = rtapi.untag_resources(ResourceARNList=[source_arn], TagKeys=["Test"])
    assert failed["FailedResourcesMap"] == {}

    resp = rtapi.get_resources(ResourceTypeFilters=["quicksight:data_sources"])
    assert resp["ResourceTagMappingList"][0]["Tags"] == [{"Key": "Test2", "Value": "2"}]


@mock_aws
def test_get_tag_and_untag_resources_quicksight_dashboards():
    client = boto3.client("quicksight", region_name="us-east-1")
    rtapi = boto3.client("resourcegroupstaggingapi", region_name="us-east-1")

    dash_arn = client.create_dashboard(
        AwsAccountId=ACCOUNT_ID,
        DashboardId="dash1",
        Name="TestDashboard",
        SourceEntity={
            "SourceTemplate": {
                "DataSetReferences": [
                    {
                        "DataSetPlaceholder": "placeholder",
                        "DataSetArn": f"arn:aws:quicksight:us-east-1:{ACCOUNT_ID}:dataset/ds1",
                    }
                ],
                "Arn": f"arn:aws:quicksight:us-east-1:{ACCOUNT_ID}:template/template1",
            }
        },
        Tags=[{"Key": "Test", "Value": "1"}],
    )["Arn"]

    # GetResources returns the dashboard
    resp = rtapi.get_resources(ResourceTypeFilters=["quicksight:dashboards"])
    assert len(resp["ResourceTagMappingList"]) == 1
    assert resp["ResourceTagMappingList"][0]["ResourceARN"] == dash_arn
    assert resp["ResourceTagMappingList"][0]["Tags"] == [{"Key": "Test", "Value": "1"}]

    # Add a tag through the Resource Groups Tagging API
    failed = rtapi.tag_resources(ResourceARNList=[dash_arn], Tags={"Test2": "2"})
    assert failed["FailedResourcesMap"] == {}

    resp = rtapi.get_resources(
        ResourceTypeFilters=["quicksight:dashboards"],
        TagFilters=[{"Key": "Test2", "Values": ["2"]}],
    )
    assert len(resp["ResourceTagMappingList"]) == 1
    assert resp["ResourceTagMappingList"][0]["ResourceARN"] == dash_arn

    # Remove the original tag through the Resource Groups Tagging API
    failed = rtapi.untag_resources(ResourceARNList=[dash_arn], TagKeys=["Test"])
    assert failed["FailedResourcesMap"] == {}

    resp = rtapi.get_resources(ResourceTypeFilters=["quicksight:dashboards"])
    assert resp["ResourceTagMappingList"][0]["Tags"] == [{"Key": "Test2", "Value": "2"}]


@mock_aws
def test_get_tag_and_untag_resources_quicksight_users():
    client = boto3.client("quicksight", region_name="us-east-1")
    rtapi = boto3.client("resourcegroupstaggingapi", region_name="us-east-1")

    user_arn = client.register_user(
        AwsAccountId=ACCOUNT_ID,
        Namespace="default",
        Email="user@example.com",
        IdentityType="QUICKSIGHT",
        UserName="testuser",
        UserRole="READER",
        Tags=[{"Key": "Test", "Value": "1"}],
    )["User"]["Arn"]

    # GetResources returns the user
    resp = rtapi.get_resources(ResourceTypeFilters=["quicksight:users"])
    assert len(resp["ResourceTagMappingList"]) == 1
    assert resp["ResourceTagMappingList"][0]["ResourceARN"] == user_arn
    assert resp["ResourceTagMappingList"][0]["Tags"] == [{"Key": "Test", "Value": "1"}]

    # Add a tag through the Resource Groups Tagging API
    failed = rtapi.tag_resources(ResourceARNList=[user_arn], Tags={"Test2": "2"})
    assert failed["FailedResourcesMap"] == {}

    resp = rtapi.get_resources(
        ResourceTypeFilters=["quicksight:users"],
        TagFilters=[{"Key": "Test2", "Values": ["2"]}],
    )
    assert len(resp["ResourceTagMappingList"]) == 1
    assert resp["ResourceTagMappingList"][0]["ResourceARN"] == user_arn

    # Remove the original tag through the Resource Groups Tagging API
    failed = rtapi.untag_resources(ResourceARNList=[user_arn], TagKeys=["Test"])
    assert failed["FailedResourcesMap"] == {}

    resp = rtapi.get_resources(ResourceTypeFilters=["quicksight:users"])
    assert resp["ResourceTagMappingList"][0]["Tags"] == [{"Key": "Test2", "Value": "2"}]
