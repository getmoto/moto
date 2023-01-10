import boto3
import sure  # noqa # pylint: disable=unused-import

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
    resp["InstanceId"].should.equal(instance_id)
    resp["PasswordData"].should.equal("")

    # Ensure Windows instances
    instance_id = client.run_instances(
        ImageId=EXAMPLE_AMI_WINDOWS, MinCount=1, MaxCount=1
    )["Instances"][0]["InstanceId"]
    resp = client.get_password_data(InstanceId=instance_id)
    resp["InstanceId"].should.equal(instance_id)
    resp["PasswordData"].should.have.length_of(128)
