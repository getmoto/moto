import boto3

from moto import mock_ec2, mock_kms
from tests import EXAMPLE_AMI_ID


@mock_ec2
@mock_kms
def test_run_instance_with_encrypted_ebs():
    kms = boto3.client("kms", region_name="us-east-1")
    resp = kms.create_key(Description="my key", KeyUsage="ENCRYPT_DECRYPT")
    key_id = resp["KeyMetadata"]["Arn"]
    ec2 = boto3.client("ec2", region_name="us-east-1")
    key_name = "keypair_name"
    ec2.create_key_pair(KeyName=key_name)

    kwargs = {
        "MinCount": 1,
        "MaxCount": 1,
        "ImageId": EXAMPLE_AMI_ID,
        "KeyName": "the_key",
        "InstanceType": "t1.micro",
        "BlockDeviceMappings": [
            {
                "DeviceName": "/dev/sda2",
                "Ebs": {
                    "VolumeSize": 50,
                    "VolumeType": "gp2",
                    "Encrypted": True,
                    "KmsKeyId": key_id,
                },
            }
        ],
    }
    instance = ec2.run_instances(**kwargs)
    instance_id = instance["Instances"][0]["InstanceId"]

    instances = (
        ec2.describe_instances(InstanceIds=[instance_id])
        .get("Reservations")[0]
        .get("Instances")
    )
    volume = instances[0]["BlockDeviceMappings"][0]["Ebs"]

    volumes = ec2.describe_volumes(VolumeIds=[volume["VolumeId"]])
    assert volumes["Volumes"][0]["Size"] == 50
    assert volumes["Volumes"][0]["Encrypted"] is True
    assert volumes["Volumes"][0]["KmsKeyId"] == key_id
