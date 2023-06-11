import boto3
import pytest

from botocore.exceptions import ClientError
from moto import mock_appconfig


@mock_appconfig
def test_create_configuration_profile():
    client = boto3.client("appconfig", region_name="eu-north-1")
    app_id = client.create_application(Name="testapp")["Id"]
    resp = client.create_configuration_profile(
        ApplicationId=app_id,
        Name="config_name",
        Description="desc",
        LocationUri="luri",
        RetrievalRoleArn="rrarn:rrarn:rrarn:rrarn",
        Validators=[{"Type": "JSON", "Content": "c"}],
        Type="freeform",
    )
    del resp["ResponseMetadata"]
    assert "Id" in resp
    config_profile_id = resp.pop("Id")

    expected_response = {
        "ApplicationId": app_id,
        "Name": "config_name",
        "Description": "desc",
        "LocationUri": "luri",
        "RetrievalRoleArn": "rrarn:rrarn:rrarn:rrarn",
        "Validators": [{"Type": "JSON", "Content": "c"}],
        "Type": "freeform",
    }

    assert resp == expected_response

    resp = client.get_configuration_profile(
        ApplicationId=app_id,
        ConfigurationProfileId=config_profile_id,
    )
    del resp["ResponseMetadata"]
    assert "Id" in resp
    resp.pop("Id")
    assert resp == expected_response

    profiles = client.list_configuration_profiles(ApplicationId=app_id)["Items"]
    assert profiles == [
        {
            "ApplicationId": app_id,
            "Id": config_profile_id,
            "Name": "config_name",
            "LocationUri": "luri",
            "Type": "freeform",
        }
    ]

    update = client.update_configuration_profile(
        ApplicationId=app_id,
        ConfigurationProfileId=config_profile_id,
        Name="name2",
        Description="desc2",
        RetrievalRoleArn="rrarn:rrarn:rrarn:222",
        Validators=[],
    )
    assert update["Name"] == "name2"
    assert update["RetrievalRoleArn"] == "rrarn:rrarn:rrarn:222"

    client.delete_configuration_profile(
        ApplicationId=app_id,
        ConfigurationProfileId=config_profile_id,
    )

    with pytest.raises(ClientError) as exc:
        client.get_configuration_profile(
            ApplicationId=app_id,
            ConfigurationProfileId=config_profile_id,
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"


@mock_appconfig
def test_tag_config_profile():
    client = boto3.client("appconfig", region_name="us-east-2")
    app_id = client.create_application(Name="testapp")["Id"]
    cp_id = client.create_configuration_profile(
        ApplicationId=app_id,
        Name="config_name",
        LocationUri="luri",
    )["Id"]
    cp_arn = f"arn:aws:appconfig:us-east-2:123456789012:application/{app_id}/configurationprofile/{cp_id}"

    tags = client.list_tags_for_resource(ResourceArn=cp_arn)["Tags"]
    assert tags == {}

    client.tag_resource(
        ResourceArn=cp_arn,
        Tags={"k1": "v1"},
    )

    tags = client.list_tags_for_resource(ResourceArn=cp_arn)["Tags"]
    assert tags == {"k1": "v1"}

    ####
    # Check this flow works when creating an app with tags
    app_id = client.create_application(Name="testapp")["Id"]
    cp_id = client.create_configuration_profile(
        ApplicationId=app_id,
        Name="config_name",
        LocationUri="luri",
        Tags={"k1": "v1"},
    )["Id"]
    cp_arn = f"arn:aws:appconfig:us-east-2:123456789012:application/{app_id}/configurationprofile/{cp_id}"

    tags = client.list_tags_for_resource(ResourceArn=cp_arn)["Tags"]
    assert tags == {"k1": "v1"}

    client.tag_resource(
        ResourceArn=cp_arn,
        Tags={"k2": "v2", "k3": "v3"},
    )

    tags = client.list_tags_for_resource(ResourceArn=cp_arn)["Tags"]
    assert tags == {"k1": "v1", "k2": "v2", "k3": "v3"}

    client.untag_resource(ResourceArn=cp_arn, TagKeys=["k2"])

    tags = client.list_tags_for_resource(ResourceArn=cp_arn)["Tags"]
    assert tags == {"k1": "v1", "k3": "v3"}

    client.untag_resource(ResourceArn=cp_arn, TagKeys=["k1", "k3"])

    tags = client.list_tags_for_resource(ResourceArn=cp_arn)["Tags"]
    assert tags == {}
