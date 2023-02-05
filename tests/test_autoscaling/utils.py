import boto3
from moto import mock_ec2


@mock_ec2
def setup_networking(region_name="us-east-1"):
    ec2 = boto3.resource("ec2", region_name=region_name)
    vpc = ec2.create_vpc(CidrBlock="10.11.0.0/16")
    subnet1 = ec2.create_subnet(
        VpcId=vpc.id, CidrBlock="10.11.1.0/24", AvailabilityZone=f"{region_name}a"
    )
    subnet2 = ec2.create_subnet(
        VpcId=vpc.id, CidrBlock="10.11.2.0/24", AvailabilityZone=f"{region_name}b"
    )
    return {"vpc": vpc.id, "subnet1": subnet1.id, "subnet2": subnet2.id}


@mock_ec2
def setup_instance_with_networking(image_id, instance_type):
    mock_data = setup_networking()
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    instances = ec2.create_instances(
        ImageId=image_id,
        InstanceType=instance_type,
        MaxCount=1,
        MinCount=1,
        SubnetId=mock_data["subnet1"],
    )
    mock_data["instances"] = instances
    return mock_data
