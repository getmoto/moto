import boto3

from moto import mock_aws
from tests import EXAMPLE_AMI_ID


@mock_aws
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


@mock_aws
def test_rgtapi_tag_and_untag_resources_for_ec2_instance() -> None:
    ec2 = boto3.client("ec2", region_name="us-east-1")
    rtapi = boto3.client("resourcegroupstaggingapi", region_name="us-east-1")
    instance = ec2.run_instances(
        ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1, InstanceType="t2.micro"
    )["Instances"][0]
    instance_id = instance["InstanceId"]
    arn = f"arn:aws:ec2:us-east-1:123456789012:instance/{instance_id}"

    rtapi.tag_resources(
        ResourceARNList=[arn],
        Tags={"env": "prod", "owner": "platform"},
    )

    described = ec2.describe_instances(InstanceIds=[instance_id])["Reservations"][0][
        "Instances"
    ][0]
    by_key = {t["Key"]: t["Value"] for t in described["Tags"]}
    assert by_key["env"] == "prod"
    assert by_key["owner"] == "platform"

    rtapi.untag_resources(ResourceARNList=[arn], TagKeys=["env"])

    described = ec2.describe_instances(InstanceIds=[instance_id])["Reservations"][0][
        "Instances"
    ][0]
    keys = {t["Key"] for t in described["Tags"]}
    assert "env" not in keys
    assert "owner" in keys


@mock_aws
def test_rgtapi_tag_and_untag_resources_for_ec2_vpc() -> None:
    ec2 = boto3.client("ec2", region_name="us-east-1")
    rtapi = boto3.client("resourcegroupstaggingapi", region_name="us-east-1")
    vpc_id = ec2.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]["VpcId"]
    arn = f"arn:aws:ec2:us-east-1:123456789012:vpc/{vpc_id}"

    rtapi.tag_resources(
        ResourceARNList=[arn],
        Tags={"tier": "network", "team": "platform"},
    )

    described = ec2.describe_vpcs(VpcIds=[vpc_id])["Vpcs"][0]
    by_key = {t["Key"]: t["Value"] for t in described["Tags"]}
    assert by_key["tier"] == "network"
    assert by_key["team"] == "platform"

    rtapi.untag_resources(ResourceARNList=[arn], TagKeys=["tier", "team"])

    described = ec2.describe_vpcs(VpcIds=[vpc_id])["Vpcs"][0]
    assert "Tags" not in described or all(
        t["Key"] not in {"tier", "team"} for t in described.get("Tags", [])
    )
