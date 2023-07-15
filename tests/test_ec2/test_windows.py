import boto3

from moto import mock_ec2
from tests import EXAMPLE_AMI_WINDOWS, EXAMPLE_AMI_PARAVIRTUAL


@mock_ec2
def test_get_password_data():
    client = boto3.client("ec2", region_name="us-east-1")

    # Ensure non-windows instances return empty password data
    instance_id = client.run_instances(
        ImageId=EXAMPLE_AMI_PARAVIRTUAL, MinCount=1, MaxCount=1
    )["Instances"][0]["InstanceId"]
    resp = client.get_password_data(InstanceId=instance_id)
    assert resp["InstanceId"] == instance_id
    assert resp["PasswordData"] == ""

    # Ensure Windows instances
    instance_id = client.run_instances(
        ImageId=EXAMPLE_AMI_WINDOWS, MinCount=1, MaxCount=1
    )["Instances"][0]["InstanceId"]
    resp = client.get_password_data(InstanceId=instance_id)
    assert resp["InstanceId"] == instance_id
    assert len(resp["PasswordData"]) == 128
