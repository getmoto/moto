import boto3

from moto import mock_aws
from tests import DEFAULT_ACCOUNT_ID


@mock_aws
def test_list_instances():
    ssoadmin = boto3.client("sso-admin", "us-east-1")

    # We automatically create an instance on startup
    # In AWS, this would involve some manual steps on the dashboard
    instances = ssoadmin.list_instances()["Instances"]
    assert len(instances) == 1

    assert instances[0]["CreatedDate"]
    assert instances[0]["IdentityStoreId"].startswith("d-")
    assert instances[0]["InstanceArn"].startswith("arn:aws:sso:::instance/ssoins-")
    assert instances[0]["OwnerAccountId"] == DEFAULT_ACCOUNT_ID
    assert instances[0]["Status"] == "ACTIVE"

    assert "Name" not in instances[0]


@mock_aws
def test_update_instance():
    ssoadmin = boto3.client("sso-admin", "us-east-1")

    # We automatically create an instance on startup
    # In AWS, this would involve some manual steps on the dashboard
    initial = ssoadmin.list_instances()["Instances"][0]

    ssoadmin.update_instance(InstanceArn=initial["InstanceArn"], Name="instancename")

    updated = ssoadmin.list_instances()["Instances"][0]
    assert updated["Name"] == "instancename"
    assert initial["IdentityStoreId"] == updated["IdentityStoreId"]
    assert initial["InstanceArn"] == updated["InstanceArn"]
