import base64
import ipaddress
import json
import warnings
from unittest import SkipTest, mock
from uuid import uuid4

import boto3
import pytest
from botocore.exceptions import ClientError, ParamValidationError
from freezegun import freeze_time
from moto import mock_ec2, mock_iam, settings
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
from tests import EXAMPLE_AMI_ID

decode_method = base64.decodebytes


@mock_ec2
def test_add_servers():
    client = boto3.client("ec2", region_name="us-east-1")
    resp = client.run_instances(ImageId=EXAMPLE_AMI_ID, MinCount=2, MaxCount=2)
    for i in resp["Instances"]:
        assert i["ImageId"] == EXAMPLE_AMI_ID

    instances = client.describe_instances(
        InstanceIds=[i["InstanceId"] for i in resp["Instances"]]
    )["Reservations"][0]["Instances"]
    assert len(instances) == 2
    for i in instances:
        assert i["ImageId"] == EXAMPLE_AMI_ID


@freeze_time("2014-01-01 05:00:00")
@mock_ec2
def test_instance_launch_and_terminate():
    client = boto3.client("ec2", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        client.run_instances(
            ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1, DryRun=True
        )
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 412
    assert ex.value.response["Error"]["Code"] == "DryRunOperation"
    assert (
        ex.value.response["Error"]["Message"]
        == "An error occurred (DryRunOperation) when calling the RunInstances operation: Request would have succeeded, but DryRun flag is set"
    )

    reservation = client.run_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)
    assert len(reservation["Instances"]) == 1
    instance = reservation["Instances"][0]
    assert instance["State"] == {"Code": 0, "Name": "pending"}
    instance_id = instance["InstanceId"]

    reservations = client.describe_instances(InstanceIds=[instance_id])["Reservations"]
    assert len(reservations) == 1
    assert reservations[0]["ReservationId"] == reservation["ReservationId"]
    instances = reservations[0]["Instances"]
    assert len(instances) == 1
    instance = instances[0]
    assert instance["InstanceId"] == instance_id
    assert instance["State"] == {"Code": 16, "Name": "running"}
    if settings.TEST_SERVER_MODE:
        # Exact value can't be determined in ServerMode
        assert "LaunchTime" in instance
    else:
        launch_time = instance["LaunchTime"].strftime("%Y-%m-%dT%H:%M:%S.000Z")
        assert launch_time == "2014-01-01T05:00:00.000Z"
    assert instance["VpcId"] is not None
    assert instance["Placement"]["AvailabilityZone"] == "us-east-1a"

    root_device_name = instance["RootDeviceName"]
    mapping = instance["BlockDeviceMappings"][0]
    assert mapping["DeviceName"] == root_device_name
    assert mapping["Ebs"]["Status"] == "in-use"
    volume_id = mapping["Ebs"]["VolumeId"]
    assert volume_id.startswith("vol-")

    volume = client.describe_volumes(VolumeIds=[volume_id])["Volumes"][0]
    assert volume["Attachments"][0]["InstanceId"] == instance_id
    assert volume["State"] == "in-use"

    with pytest.raises(ClientError) as ex:
        client.terminate_instances(InstanceIds=[instance_id], DryRun=True)
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 412
    assert ex.value.response["Error"]["Code"] == "DryRunOperation"
    assert (
        ex.value.response["Error"]["Message"]
        == "An error occurred (DryRunOperation) when calling the TerminateInstances operation: Request would have succeeded, but DryRun flag is set"
    )

    response = client.terminate_instances(InstanceIds=[instance_id])
    assert len(response["TerminatingInstances"]) == 1
    instance = response["TerminatingInstances"][0]
    assert instance["InstanceId"] == instance_id
    assert instance["PreviousState"] == {"Code": 16, "Name": "running"}
    assert instance["CurrentState"] == {"Code": 32, "Name": "shutting-down"}

    reservations = client.describe_instances(InstanceIds=[instance_id])["Reservations"]
    instance = reservations[0]["Instances"][0]
    assert instance["State"] == {"Code": 48, "Name": "terminated"}


@mock_ec2
def test_instance_terminate_discard_volumes():
    ec2_resource = boto3.resource("ec2", "us-west-1")

    result = ec2_resource.create_instances(
        ImageId=EXAMPLE_AMI_ID,
        MinCount=1,
        MaxCount=1,
        BlockDeviceMappings=[
            {
                "DeviceName": "/dev/sda1",
                "Ebs": {"VolumeSize": 50, "DeleteOnTermination": True},
            }
        ],
    )
    instance = result[0]

    instance_volume_ids = []
    for volume in instance.volumes.all():
        instance_volume_ids.append(volume.volume_id)

    instance.terminate()
    instance.wait_until_terminated()

    all_volumes_ids = [v.id for v in list(ec2_resource.volumes.all())]
    for my_id in instance_volume_ids:
        assert my_id not in all_volumes_ids


@mock_ec2
def test_instance_terminate_keep_volumes_explicit():
    ec2_resource = boto3.resource("ec2", "us-west-1")

    result = ec2_resource.create_instances(
        ImageId=EXAMPLE_AMI_ID,
        MinCount=1,
        MaxCount=1,
        BlockDeviceMappings=[
            {
                "DeviceName": "/dev/sda1",
                "Ebs": {"VolumeSize": 50, "DeleteOnTermination": False},
            }
        ],
    )
    instance = result[0]

    instance_volume_ids = []
    for volume in instance.volumes.all():
        instance_volume_ids.append(volume.volume_id)

    instance.terminate()
    instance.wait_until_terminated()

    all_volumes_ids = [v.id for v in list(ec2_resource.volumes.all())]
    for my_id in instance_volume_ids:
        assert my_id in all_volumes_ids


@mock_ec2
def test_instance_terminate_keep_volumes_implicit():
    ec2_resource = boto3.resource("ec2", "us-west-1")

    result = ec2_resource.create_instances(
        ImageId=EXAMPLE_AMI_ID,
        MinCount=1,
        MaxCount=1,
        BlockDeviceMappings=[{"DeviceName": "/dev/sda1", "Ebs": {"VolumeSize": 50}}],
    )
    instance = result[0]

    instance_volume_ids = []
    for volume in instance.volumes.all():
        instance_volume_ids.append(volume.volume_id)

    instance.terminate()
    instance.wait_until_terminated()

    assert len(instance_volume_ids) == 1
    volume = ec2_resource.Volume(instance_volume_ids[0])
    assert volume.state == "available"


@mock_ec2
def test_instance_terminate_detach_volumes():
    ec2_resource = boto3.resource("ec2", "us-west-1")
    result = ec2_resource.create_instances(
        ImageId=EXAMPLE_AMI_ID,
        MinCount=1,
        MaxCount=1,
        BlockDeviceMappings=[
            {"DeviceName": "/dev/sda1", "Ebs": {"VolumeSize": 50}},
            {"DeviceName": "/dev/sda2", "Ebs": {"VolumeSize": 50}},
        ],
    )
    instance = result[0]
    my_volume_ids = []
    for volume in instance.volumes.all():
        my_volume_ids.append(volume.volume_id)
        response = instance.detach_volume(VolumeId=volume.volume_id)
        assert response["State"] == "detaching"

    instance.terminate()
    instance.wait_until_terminated()

    all_volumes_ids = [v.id for v in list(ec2_resource.volumes.all())]
    for my_id in my_volume_ids:
        assert my_id in all_volumes_ids


@mock_ec2
def test_instance_detach_volume_wrong_path():
    ec2_resource = boto3.resource("ec2", "us-west-1")
    result = ec2_resource.create_instances(
        ImageId=EXAMPLE_AMI_ID,
        MinCount=1,
        MaxCount=1,
        BlockDeviceMappings=[{"DeviceName": "/dev/sda1", "Ebs": {"VolumeSize": 50}}],
    )
    instance = result[0]
    for volume in instance.volumes.all():
        with pytest.raises(ClientError) as ex:
            instance.detach_volume(VolumeId=volume.volume_id, Device="/dev/sdf")

        assert ex.value.response["Error"]["Code"] == "InvalidAttachment.NotFound"
        assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
        assert (
            ex.value.response["Error"]["Message"]
            == f"The volume {volume.volume_id} is not attached to instance {instance.instance_id} as device /dev/sdf"
        )


@mock_ec2
def test_terminate_empty_instances():
    client = boto3.client("ec2", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        client.terminate_instances(InstanceIds=[])
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert ex.value.response["Error"]["Code"] == "InvalidParameterCombination"
    assert ex.value.response["Error"]["Message"] == "No instances specified"


@freeze_time("2014-01-01 05:00:00")
@mock_ec2
def test_instance_attach_volume():
    client = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    reservation = client.run_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)
    instance = ec2.Instance(reservation["Instances"][0]["InstanceId"])

    vol1 = ec2.create_volume(Size=36, AvailabilityZone="us-east-1a")
    vol1.attach_to_instance(InstanceId=instance.id, Device="/dev/sda1")
    vol2 = ec2.create_volume(Size=65, AvailabilityZone="us-east-1a")
    vol2.attach_to_instance(InstanceId=instance.id, Device="/dev/sdb1")
    vol3 = ec2.create_volume(Size=130, AvailabilityZone="us-east-1a")
    vol3.attach_to_instance(InstanceId=instance.id, Device="/dev/sdc1")

    instance.reload()

    assert len(instance.block_device_mappings) == 3
    expected_vol3_id = [
        m["Ebs"]["VolumeId"]
        for m in instance.block_device_mappings
        if m["DeviceName"] == "/dev/sdc1"
    ][0]

    expected_vol3 = ec2.Volume(expected_vol3_id)
    assert expected_vol3.attachments[0]["InstanceId"] == instance.id
    assert expected_vol3.availability_zone == "us-east-1a"
    assert expected_vol3.state == "in-use"
    if not settings.TEST_SERVER_MODE:
        # FreezeTime does not work in ServerMode
        assert expected_vol3.attachments[0]["AttachTime"] == instance.launch_time
        assert expected_vol3.create_time == instance.launch_time


@mock_ec2
def test_get_instances_by_id():
    client = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    reservation = client.run_instances(ImageId=EXAMPLE_AMI_ID, MinCount=2, MaxCount=2)
    instance1 = ec2.Instance(reservation["Instances"][0]["InstanceId"])
    instance2 = ec2.Instance(reservation["Instances"][1]["InstanceId"])

    reservations = client.describe_instances(InstanceIds=[instance1.id])["Reservations"]
    assert len(reservations) == 1
    reservation = reservations[0]
    assert len(reservation["Instances"]) == 1
    assert reservation["Instances"][0]["InstanceId"] == instance1.id

    reservations = client.describe_instances(InstanceIds=[instance1.id, instance2.id])[
        "Reservations"
    ]
    assert len(reservations) == 1
    reservation = reservations[0]
    assert len(reservation["Instances"]) == 2
    instance_ids = [instance["InstanceId"] for instance in reservation["Instances"]]
    assert set(instance_ids) == set([instance1.id, instance2.id])

    # Call describe_instances with a bad id should raise an error
    with pytest.raises(ClientError) as ex:
        client.describe_instances(InstanceIds=[instance1.id, "i-1234abcd"])
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "RequestId" in ex.value.response["ResponseMetadata"]
    assert ex.value.response["Error"]["Code"] == "InvalidInstanceID.NotFound"


@mock_ec2
def test_get_paginated_instances():
    client = boto3.client("ec2", region_name="us-east-1")
    conn = boto3.resource("ec2", "us-east-1")
    instances = []
    for i in range(12):
        instances.extend(
            conn.create_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)
        )

    resp1 = client.describe_instances(MaxResults=5)
    res1 = resp1["Reservations"]
    assert len(res1) == 5
    next_token = resp1["NextToken"]

    assert next_token is not None

    resp2 = client.describe_instances(NextToken=next_token)

    # at least 12 total - 5 from the first call but there may be more from servermode tests
    assert len(resp2["Reservations"]) >= 7

    for i in instances:
        i.terminate()


@mock_ec2
def test_describe_instances_pagination_error():
    client = boto3.client("ec2", region_name="us-east-1")

    # Call describe_instances with a bad id should raise an error
    with pytest.raises(ClientError) as ex:
        paginator = client.get_paginator("describe_instances").paginate(
            InstanceIds=["i-12345678"],
            PaginationConfig={
                "MaxItems": 9999,
                "PageSize": 100,
            },
        )
        for page in paginator:
            dir(page)

    assert ex.value.response["Error"]["Code"] == "InvalidParameterCombination"
    assert (
        ex.value.response["Error"]["Message"]
        == "The parameter instancesSet cannot be used with the parameter maxResults"
    )


@mock_ec2
def test_create_with_tags():
    ec2 = boto3.client("ec2", region_name="us-west-2")
    instances = ec2.run_instances(
        ImageId=EXAMPLE_AMI_ID,
        MinCount=1,
        MaxCount=1,
        InstanceType="t2.micro",
        TagSpecifications=[
            {
                "ResourceType": "instance",
                "Tags": [
                    {"Key": "MY_TAG1", "Value": "MY_VALUE1"},
                    {"Key": "MY_TAG2", "Value": "MY_VALUE2"},
                ],
            },
            {
                "ResourceType": "instance",
                "Tags": [{"Key": "MY_TAG3", "Value": "MY_VALUE3"}],
            },
        ],
    )
    assert "Tags" in instances["Instances"][0]
    assert len(instances["Instances"][0]["Tags"]) == 3


@mock_ec2
def test_create_with_volume_tags():
    ec2 = boto3.client("ec2", region_name="us-west-2")
    volume_tags = [
        {"Key": "MY_TAG1", "Value": "MY_VALUE1"},
        {"Key": "MY_TAG2", "Value": "MY_VALUE2"},
    ]
    instances = ec2.run_instances(
        ImageId=EXAMPLE_AMI_ID,
        MinCount=2,
        MaxCount=2,
        InstanceType="t2.micro",
        TagSpecifications=[{"ResourceType": "volume", "Tags": volume_tags}],
    ).get("Instances")
    instance_ids = [i["InstanceId"] for i in instances]
    instances = (
        ec2.describe_instances(InstanceIds=instance_ids)
        .get("Reservations")[0]
        .get("Instances")
    )
    for instance in instances:
        instance_volume = instance["BlockDeviceMappings"][0]["Ebs"]
        resp = ec2.describe_volumes(VolumeIds=[instance_volume["VolumeId"]])
        for volume in resp["Volumes"]:
            assert sorted(volume["Tags"], key=lambda i: i["Key"]) == volume_tags


@mock_ec2
def test_get_instances_filtering_by_state():
    ec2 = boto3.resource("ec2", "us-west-1")
    client = boto3.client("ec2", "us-west-1")
    reservation = ec2.create_instances(ImageId=EXAMPLE_AMI_ID, MinCount=3, MaxCount=3)
    instance1, instance2, instance3 = reservation

    client.terminate_instances(InstanceIds=[instance1.id])

    instances = retrieve_all_instances(
        client, [{"Name": "instance-state-name", "Values": ["running"]}]
    )
    instance_ids = [i["InstanceId"] for i in instances]
    # Since we terminated instance1, only instance2 and instance3 should be
    # returned
    assert instance1.id not in instance_ids
    assert instance2.id in instance_ids
    assert instance3.id in instance_ids

    reservations = client.describe_instances(
        InstanceIds=[instance2.id],
        Filters=[{"Name": "instance-state-name", "Values": ["running"]}],
    )["Reservations"]
    assert len(reservations) == 1
    instance_ids = [instance["InstanceId"] for instance in reservations[0]["Instances"]]
    assert instance_ids == [instance2.id]

    reservations = client.describe_instances(
        InstanceIds=[instance2.id],
        Filters=[{"Name": "instance-state-name", "Values": ["terminated"]}],
    )["Reservations"]
    assert reservations == []

    # get_all_reservations should still return all 3
    instances = retrieve_all_instances(client, filters=[])
    instance_ids = [i["InstanceId"] for i in instances]
    assert instance1.id in instance_ids
    assert instance2.id in instance_ids
    assert instance3.id in instance_ids

    if not settings.TEST_SERVER_MODE:
        # ServerMode will just throw a generic 500
        filters = [{"Name": "not-implemented-filter", "Values": ["foobar"]}]
        with pytest.raises(NotImplementedError):
            client.describe_instances(Filters=filters)


@mock_ec2
def test_get_instances_filtering_by_instance_id():
    ec2 = boto3.resource("ec2", "us-west-1")
    client = boto3.client("ec2", "us-west-1")
    reservation = ec2.create_instances(ImageId=EXAMPLE_AMI_ID, MinCount=3, MaxCount=3)
    instance1, instance2, _ = reservation

    def _filter(values, exists=True):
        f = [{"Name": "instance-id", "Values": values}]
        r = client.describe_instances(Filters=f)["Reservations"]
        if exists:
            assert len(r[0]["Instances"]) == len(values)
            found_ids = [i["InstanceId"] for i in r[0]["Instances"]]
            assert set(found_ids) == set(values)
        else:
            assert len(r) == 0

    _filter(values=[instance1.id])
    _filter(values=[instance1.id, instance2.id])
    _filter(values=["non-existing-id"], exists=False)


@mock_ec2
def test_get_instances_filtering_by_instance_type():
    ec2 = boto3.resource("ec2", "us-west-1")
    client = boto3.client("ec2", "us-west-1")
    instance1 = ec2.create_instances(
        ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1, InstanceType="m1.small"
    )[0]
    instance2 = ec2.create_instances(
        ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1, InstanceType="m1.small"
    )[0]
    instance3 = ec2.create_instances(
        ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1, InstanceType="t1.micro"
    )[0]

    instances = retrieve_all_instances(
        client, [{"Name": "instance-type", "Values": ["m1.small"]}]
    )
    instance_ids = [i["InstanceId"] for i in instances]
    assert instance1.id in set(instance_ids)
    assert instance2.id in set(instance_ids)

    instances = retrieve_all_instances(
        client, [{"Name": "instance-type", "Values": ["t1.micro"]}]
    )
    instance_ids = [i["InstanceId"] for i in instances]
    assert instance3.id in instance_ids

    instances = retrieve_all_instances(
        client, [{"Name": "instance-type", "Values": ["t1.micro", "m1.small"]}]
    )
    instance_ids = [i["InstanceId"] for i in instances]
    assert instance1.id in instance_ids
    assert instance2.id in instance_ids
    assert instance3.id in instance_ids

    res = client.describe_instances(
        Filters=[{"Name": "instance-type", "Values": ["bogus"]}]
    )
    assert len(res["Reservations"]) == 0


@mock_ec2
def test_get_instances_filtering_by_reason_code():
    ec2 = boto3.resource("ec2", "us-west-1")
    client = boto3.client("ec2", "us-west-1")
    reservation = ec2.create_instances(ImageId=EXAMPLE_AMI_ID, MinCount=3, MaxCount=3)
    instance1, instance2, instance3 = reservation
    instance1.stop()
    instance2.terminate()

    filters = [
        {"Name": "state-reason-code", "Values": ["Client.UserInitiatedShutdown"]}
    ]
    instances = retrieve_all_instances(client, filters)
    instance_ids = [i["InstanceId"] for i in instances]

    assert instance1.id in instance_ids
    assert instance2.id in instance_ids
    assert instance3.id not in instance_ids

    filters = [{"Name": "state-reason-code", "Values": [""]}]
    instances = retrieve_all_instances(client, filters)
    instance_ids = [i["InstanceId"] for i in instances]
    assert instance3.id in instance_ids
    assert instance1.id not in instance_ids
    assert instance2.id not in instance_ids


@mock_ec2
def test_get_instances_filtering_by_source_dest_check():
    ec2 = boto3.resource("ec2", "us-west-1")
    client = boto3.client("ec2", "us-west-1")
    reservation = ec2.create_instances(ImageId=EXAMPLE_AMI_ID, MinCount=2, MaxCount=2)
    instance1, instance2 = reservation
    client.modify_instance_attribute(
        InstanceId=instance1.id, SourceDestCheck={"Value": False}
    )

    instances_false = retrieve_all_instances(
        client, [{"Name": "source-dest-check", "Values": ["false"]}]
    )
    instances_true = retrieve_all_instances(
        client, [{"Name": "source-dest-check", "Values": ["true"]}]
    )

    assert instance1.id in [i["InstanceId"] for i in instances_false]
    assert instance2.id not in [i["InstanceId"] for i in instances_false]

    assert instance1.id not in [i["InstanceId"] for i in instances_true]
    assert instance2.id in [i["InstanceId"] for i in instances_true]


@mock_ec2
def test_get_instances_filtering_by_vpc_id():
    ec2 = boto3.resource("ec2", "us-west-1")
    client = boto3.client("ec2", "us-west-1")
    vpc1 = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    subnet1 = ec2.create_subnet(VpcId=vpc1.id, CidrBlock="10.0.0.0/27")
    reservation1 = ec2.create_instances(
        ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1, SubnetId=subnet1.id
    )
    instance1 = reservation1[0]

    vpc2 = ec2.create_vpc(CidrBlock="10.1.0.0/16")
    subnet2 = ec2.create_subnet(VpcId=vpc2.id, CidrBlock="10.1.0.0/27")
    reservation2 = ec2.create_instances(
        ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1, SubnetId=subnet2.id
    )
    instance2 = reservation2[0]

    res1 = client.describe_instances(Filters=[{"Name": "vpc-id", "Values": [vpc1.id]}])[
        "Reservations"
    ]
    assert len(res1) == 1
    assert len(res1[0]["Instances"]) == 1
    assert res1[0]["Instances"][0]["InstanceId"] == instance1.id
    assert res1[0]["Instances"][0]["VpcId"] == vpc1.id
    assert res1[0]["Instances"][0]["SubnetId"] == subnet1.id

    res2 = client.describe_instances(Filters=[{"Name": "vpc-id", "Values": [vpc2.id]}])[
        "Reservations"
    ]
    assert len(res2) == 1
    assert len(res2[0]["Instances"]) == 1
    assert res2[0]["Instances"][0]["InstanceId"] == instance2.id
    assert res2[0]["Instances"][0]["VpcId"] == vpc2.id
    assert res2[0]["Instances"][0]["SubnetId"] == subnet2.id


@mock_ec2
def test_get_instances_filtering_by_dns_name():
    ec2 = boto3.resource("ec2", "us-west-1")
    client = boto3.client("ec2", "us-west-1")
    vpc1 = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    subnet = ec2.create_subnet(VpcId=vpc1.id, CidrBlock="10.0.0.0/27")
    client.modify_subnet_attribute(
        SubnetId=subnet.id, MapPublicIpOnLaunch={"Value": True}
    )
    reservation1 = ec2.create_instances(
        ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1, SubnetId=subnet.id
    )
    instance1 = reservation1[0]

    reservation2 = ec2.create_instances(
        ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1, SubnetId=subnet.id
    )
    instance2 = reservation2[0]

    res1 = client.describe_instances(
        Filters=[{"Name": "dns-name", "Values": [instance1.public_dns_name]}]
    )["Reservations"]
    assert len(res1) == 1
    assert len(res1[0]["Instances"]) == 1
    assert res1[0]["Instances"][0]["InstanceId"] == instance1.id

    res2 = client.describe_instances(
        Filters=[{"Name": "dns-name", "Values": [instance2.public_dns_name]}]
    )["Reservations"]
    assert len(res2) == 1
    assert len(res2[0]["Instances"]) == 1
    assert res2[0]["Instances"][0]["InstanceId"] == instance2.id


@mock_ec2
def test_get_instances_filtering_by_architecture():
    ec2 = boto3.resource("ec2", region_name="us-west-1")
    client = boto3.client("ec2", region_name="us-west-1")
    ec2.create_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)

    reservations = client.describe_instances(
        Filters=[{"Name": "architecture", "Values": ["x86_64"]}]
    )["Reservations"]
    # get_all_reservations should return the instance
    assert len(reservations[0]["Instances"]) == 1


@mock_ec2
def test_get_instances_filtering_by_image_id():
    client = boto3.client("ec2", region_name="us-east-1")
    conn = boto3.resource("ec2", "us-east-1")
    conn.create_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)

    reservations = client.describe_instances(
        Filters=[{"Name": "image-id", "Values": [EXAMPLE_AMI_ID]}]
    )["Reservations"]
    assert len(reservations[0]["Instances"]) >= 1, "Should return just created instance"


@mock_ec2
def test_get_instances_filtering_by_account_id():
    client = boto3.client("ec2", region_name="us-east-1")
    conn = boto3.resource("ec2", "us-east-1")
    instance = conn.create_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)[0]

    instances = retrieve_all_instances(
        client, filters=[{"Name": "owner-id", "Values": [ACCOUNT_ID]}]
    )

    assert instance.id in [i["InstanceId"] for i in instances]


@mock_ec2
def test_get_instances_filtering_by_private_dns():
    client = boto3.client("ec2", region_name="us-east-1")
    conn = boto3.resource("ec2", "us-east-1")
    conn.create_instances(
        ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1, PrivateIpAddress="10.0.0.1"
    )
    reservations = client.describe_instances(
        Filters=[{"Name": "private-dns-name", "Values": ["ip-10-0-0-1.ec2.internal"]}]
    )["Reservations"]
    assert len(reservations[0]["Instances"]) == 1


@mock_ec2
def test_get_instances_filtering_by_ni_private_dns():
    client = boto3.client("ec2", region_name="us-west-2")
    conn = boto3.resource("ec2", "us-west-2")
    conn.create_instances(
        ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1, PrivateIpAddress="10.0.0.1"
    )
    reservations = client.describe_instances(
        Filters=[
            {
                "Name": "network-interface.private-dns-name",
                "Values": ["ip-10-0-0-1.us-west-2.compute.internal"],
            }
        ]
    )["Reservations"]
    assert len(reservations[0]["Instances"]) == 1


@mock_ec2
def test_run_instances_with_unknown_security_group():
    client = boto3.client("ec2", region_name="us-east-1")
    sg_id = f"sg-{str(uuid4())[0:6]}"
    with pytest.raises(ClientError) as exc:
        client.run_instances(
            ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1, SecurityGroupIds=[sg_id]
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidGroup.NotFound"
    assert err["Message"] == f"The security group '{sg_id}' does not exist"


@mock_ec2
def test_get_instances_filtering_by_instance_group_name():
    client = boto3.client("ec2", region_name="us-east-1")
    sec_group_name = str(uuid4())[0:6]
    client.create_security_group(Description="test", GroupName=sec_group_name)
    client.run_instances(
        ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1, SecurityGroups=[sec_group_name]
    )
    reservations = client.describe_instances(
        Filters=[{"Name": "instance.group-name", "Values": [sec_group_name]}]
    )["Reservations"]
    assert len(reservations[0]["Instances"]) == 1


@mock_ec2
def test_get_instances_filtering_by_instance_group_id():
    client = boto3.client("ec2", region_name="us-east-1")
    sec_group_name = str(uuid4())[0:6]
    create_sg = client.create_security_group(
        Description="test", GroupName=sec_group_name
    )
    group_id = create_sg["GroupId"]
    client.run_instances(
        ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1, SecurityGroups=[sec_group_name]
    )
    reservations = client.describe_instances(
        Filters=[{"Name": "instance.group-id", "Values": [group_id]}]
    )["Reservations"]
    assert len(reservations[0]["Instances"]) == 1


@mock_ec2
def test_get_instances_filtering_by_subnet_id():
    client = boto3.client("ec2", region_name="us-east-1")

    vpc_cidr = ipaddress.ip_network("192.168.42.0/24")
    subnet_cidr = ipaddress.ip_network("192.168.42.0/25")

    resp = client.create_vpc(CidrBlock=str(vpc_cidr))
    vpc_id = resp["Vpc"]["VpcId"]

    resp = client.create_subnet(CidrBlock=str(subnet_cidr), VpcId=vpc_id)
    subnet_id = resp["Subnet"]["SubnetId"]

    client.run_instances(
        ImageId=EXAMPLE_AMI_ID, MaxCount=1, MinCount=1, SubnetId=subnet_id
    )

    reservations = client.describe_instances(
        Filters=[{"Name": "subnet-id", "Values": [subnet_id]}]
    )["Reservations"]
    assert len(reservations) == 1


@mock_ec2
def test_get_instances_filtering_by_tag():
    client = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    reservation = ec2.create_instances(ImageId=EXAMPLE_AMI_ID, MinCount=3, MaxCount=3)
    instance1, instance2, instance3 = reservation

    tag1_name = str(uuid4())[0:6]
    tag1_val = str(uuid4())
    tag2_name = str(uuid4())[0:6]
    tag2_val = str(uuid4())
    tag3_name = str(uuid4())[0:6]

    instance1.create_tags(
        Tags=[
            {"Key": tag1_name, "Value": tag1_val},
            {"Key": tag2_name, "Value": tag2_val},
            {"Key": tag3_name, "Value": json.dumps(["entry1", "entry2"])},
        ]
    )
    instance2.create_tags(Tags=[{"Key": tag1_name, "Value": tag1_val}])
    instance2.create_tags(Tags=[{"Key": tag2_name, "Value": "wrong value"}])
    instance3.create_tags(Tags=[{"Key": tag2_name, "Value": tag2_val}])

    res = client.describe_instances(
        Filters=[{"Name": "tag:tag0", "Values": ["value0"]}]
    )
    # describe_instances should return no instances
    assert len(res["Reservations"]) == 0

    res = client.describe_instances(
        Filters=[{"Name": f"tag:{tag1_name}", "Values": [tag1_val]}]
    )
    # describe_instances should return both instances with this tag value
    assert len(res["Reservations"]) == 1
    assert len(res["Reservations"][0]["Instances"]) == 2
    assert res["Reservations"][0]["Instances"][0]["InstanceId"] == instance1.id
    assert res["Reservations"][0]["Instances"][1]["InstanceId"] == instance2.id

    res = client.describe_instances(
        Filters=[
            {"Name": f"tag:{tag1_name}", "Values": [tag1_val]},
            {"Name": f"tag:{tag2_name}", "Values": [tag2_val]},
        ]
    )
    # describe_instances should return the instance with both tag values
    assert len(res["Reservations"]) == 1
    assert len(res["Reservations"][0]["Instances"]) == 1
    assert res["Reservations"][0]["Instances"][0]["InstanceId"] == instance1.id

    res = client.describe_instances(
        Filters=[{"Name": f"tag:{tag2_name}", "Values": [tag2_val, "bogus"]}]
    )
    # describe_instances should return both instances with one of the
    # acceptable tag values
    assert len(res["Reservations"]) == 1
    assert len(res["Reservations"][0]["Instances"]) == 2
    assert res["Reservations"][0]["Instances"][0]["InstanceId"] == instance1.id
    assert res["Reservations"][0]["Instances"][1]["InstanceId"] == instance3.id

    # We should be able to use tags containing special characters
    res = client.describe_instances(
        Filters=[
            {"Name": f"tag:{tag3_name}", "Values": [json.dumps(["entry1", "entry2"])]}
        ]
    )
    assert len(res["Reservations"]) == 1
    assert len(res["Reservations"][0]["Instances"]) == 1
    assert res["Reservations"][0]["Instances"][0]["InstanceId"] == instance1.id


@mock_ec2
def test_get_instances_filtering_by_tag_value():
    client = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    reservation = ec2.create_instances(ImageId=EXAMPLE_AMI_ID, MinCount=3, MaxCount=3)
    instance1, instance2, instance3 = reservation

    tag1_name = str(uuid4())[0:6]
    tag1_val = str(uuid4())
    tag2_name = str(uuid4())[0:6]
    tag2_val = str(uuid4())
    instance1.create_tags(Tags=[{"Key": tag1_name, "Value": tag1_val}])
    instance1.create_tags(Tags=[{"Key": tag2_name, "Value": tag2_val}])
    instance2.create_tags(Tags=[{"Key": tag1_name, "Value": tag1_val}])
    instance2.create_tags(Tags=[{"Key": tag2_name, "Value": "wrong value"}])
    instance3.create_tags(Tags=[{"Key": tag2_name, "Value": tag2_val}])

    res = client.describe_instances(
        Filters=[{"Name": "tag-value", "Values": ["value0"]}]
    )
    # describe_instances should return no instances
    assert len(res["Reservations"]) == 0

    res = client.describe_instances(
        Filters=[{"Name": "tag-value", "Values": [tag1_val]}]
    )
    # describe_instances should return both instances with this tag value
    assert len(res["Reservations"]) == 1
    assert len(res["Reservations"][0]["Instances"]) == 2
    assert res["Reservations"][0]["Instances"][0]["InstanceId"] == instance1.id
    assert res["Reservations"][0]["Instances"][1]["InstanceId"] == instance2.id

    res = client.describe_instances(
        Filters=[{"Name": "tag-value", "Values": [tag2_val, tag1_val]}]
    )
    # describe_instances should return both instances with one of the
    # acceptable tag values
    assert len(res["Reservations"]) == 1
    assert len(res["Reservations"][0]["Instances"]) == 3
    assert res["Reservations"][0]["Instances"][0]["InstanceId"] == instance1.id
    assert res["Reservations"][0]["Instances"][1]["InstanceId"] == instance2.id
    assert res["Reservations"][0]["Instances"][2]["InstanceId"] == instance3.id

    res = client.describe_instances(
        Filters=[{"Name": "tag-value", "Values": [tag2_val, "bogus"]}]
    )
    # describe_instances should return both instances with one of the
    # acceptable tag values
    assert len(res["Reservations"]) == 1
    assert len(res["Reservations"][0]["Instances"]) == 2
    assert res["Reservations"][0]["Instances"][0]["InstanceId"] == instance1.id
    assert res["Reservations"][0]["Instances"][1]["InstanceId"] == instance3.id


@mock_ec2
def test_get_instances_filtering_by_tag_name():
    client = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    reservation = ec2.create_instances(ImageId=EXAMPLE_AMI_ID, MinCount=3, MaxCount=3)
    instance1, instance2, instance3 = reservation

    tag1 = str(uuid4())
    tag3 = str(uuid4())

    instance1.create_tags(Tags=[{"Key": tag1, "Value": ""}])
    instance1.create_tags(Tags=[{"Key": "tag2", "Value": ""}])
    instance2.create_tags(Tags=[{"Key": tag1, "Value": ""}])
    instance2.create_tags(Tags=[{"Key": "tag2X", "Value": ""}])
    instance3.create_tags(Tags=[{"Key": tag3, "Value": ""}])

    res = client.describe_instances(Filters=[{"Name": "tag-key", "Values": ["tagX"]}])
    # describe_instances should return no instances
    assert len(res["Reservations"]) == 0

    res = client.describe_instances(Filters=[{"Name": "tag-key", "Values": [tag1]}])
    # describe_instances should return both instances with this tag value
    assert len(res["Reservations"]) == 1
    assert len(res["Reservations"][0]["Instances"]) == 2
    assert res["Reservations"][0]["Instances"][0]["InstanceId"] == instance1.id
    assert res["Reservations"][0]["Instances"][1]["InstanceId"] == instance2.id

    res = client.describe_instances(
        Filters=[{"Name": "tag-key", "Values": [tag1, tag3]}]
    )
    # describe_instances should return both instances with one of the
    # acceptable tag values
    assert len(res["Reservations"]) == 1
    assert len(res["Reservations"][0]["Instances"]) == 3
    assert res["Reservations"][0]["Instances"][0]["InstanceId"] == instance1.id
    assert res["Reservations"][0]["Instances"][1]["InstanceId"] == instance2.id
    assert res["Reservations"][0]["Instances"][2]["InstanceId"] == instance3.id


@mock_ec2
def test_instance_start_and_stop():
    client = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    reservation = ec2.create_instances(ImageId=EXAMPLE_AMI_ID, MinCount=2, MaxCount=2)
    instance1, instance2 = reservation

    instance_ids = [instance1.id, instance2.id]

    with pytest.raises(ClientError) as ex:
        client.stop_instances(InstanceIds=instance_ids, DryRun=True)
    assert ex.value.response["Error"]["Code"] == "DryRunOperation"
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 412
    assert (
        ex.value.response["Error"]["Message"]
        == "An error occurred (DryRunOperation) when calling the StopInstances operation: Request would have succeeded, but DryRun flag is set"
    )

    stopped_instances = client.stop_instances(InstanceIds=instance_ids)[
        "StoppingInstances"
    ]

    for instance in stopped_instances:
        assert instance["PreviousState"] == {"Code": 16, "Name": "running"}
        assert instance["CurrentState"] == {"Code": 64, "Name": "stopping"}

    instance1.reload()
    assert instance1.state == {"Code": 80, "Name": "stopped"}

    with pytest.raises(ClientError) as ex:
        client.start_instances(InstanceIds=[instance1.id], DryRun=True)
    assert ex.value.response["Error"]["Code"] == "DryRunOperation"
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 412
    assert (
        ex.value.response["Error"]["Message"]
        == "An error occurred (DryRunOperation) when calling the StartInstances operation: Request would have succeeded, but DryRun flag is set"
    )

    instance1.reload()
    # The DryRun-operation did not change anything
    assert instance1.state == {"Code": 80, "Name": "stopped"}

    started_instances = client.start_instances(InstanceIds=[instance1.id])[
        "StartingInstances"
    ]
    assert started_instances[0]["CurrentState"] == {"Code": 0, "Name": "pending"}
    assert started_instances[0]["PreviousState"] == {"Code": 80, "Name": "stopped"}


@mock_ec2
def test_instance_reboot():
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    response = ec2.create_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)
    instance = response[0]
    assert instance.state == {"Code": 0, "Name": "pending"}
    instance.reload()
    assert instance.state == {"Code": 16, "Name": "running"}

    with pytest.raises(ClientError) as ex:
        instance.reboot(DryRun=True)
    assert ex.value.response["Error"]["Code"] == "DryRunOperation"
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 412
    assert (
        ex.value.response["Error"]["Message"]
        == "An error occurred (DryRunOperation) when calling the RebootInstances operation: Request would have succeeded, but DryRun flag is set"
    )

    assert instance.state == {"Code": 16, "Name": "running"}

    instance.reboot()
    assert instance.state == {"Code": 16, "Name": "running"}


@mock_ec2
def test_instance_attribute_instance_type():
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    response = ec2.create_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)
    instance = response[0]
    assert instance.instance_type == "m1.small"

    with pytest.raises(ClientError) as ex:
        instance.modify_attribute(InstanceType={"Value": "m1.medium"}, DryRun=True)
    assert ex.value.response["Error"]["Code"] == "DryRunOperation"
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 412
    assert (
        ex.value.response["Error"]["Message"]
        == "An error occurred (DryRunOperation) when calling the ModifyInstanceAttribute operation: Request would have succeeded, but DryRun flag is set"
    )

    instance.modify_attribute(InstanceType={"Value": "m1.medium"})

    assert instance.instance_type == "m1.medium"
    assert instance.describe_attribute(Attribute="instanceType")["InstanceType"] == {
        "Value": "m1.medium"
    }


@mock_ec2
def test_modify_instance_attribute_security_groups():
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    response = ec2.create_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)
    instance = response[0]
    old_groups = instance.describe_attribute(Attribute="groupSet")["Groups"]
    assert old_groups == []

    sg_id = ec2.create_security_group(
        GroupName=str(uuid4()), Description="this is a test security group"
    ).id
    sg_id2 = ec2.create_security_group(
        GroupName=str(uuid4()), Description="this is a test security group 2"
    ).id

    with pytest.raises(ClientError) as ex:
        instance.modify_attribute(Groups=[sg_id, sg_id2], DryRun=True)
    assert ex.value.response["Error"]["Code"] == "DryRunOperation"
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 412
    assert (
        ex.value.response["Error"]["Message"]
        == "An error occurred (DryRunOperation) when calling the ModifyInstanceAttribute operation: Request would have succeeded, but DryRun flag is set"
    )

    instance.modify_attribute(Groups=[sg_id, sg_id2])

    new_groups = instance.describe_attribute(Attribute="groupSet")["Groups"]
    assert len(new_groups) == 2
    assert {"GroupId": sg_id} in new_groups
    assert {"GroupId": sg_id2} in new_groups


@mock_ec2
def test_instance_attribute_user_data():
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    res = ec2.create_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)
    instance = res[0]

    with pytest.raises(ClientError) as ex:
        instance.modify_attribute(
            UserData={"Value": "this is my user data"}, DryRun=True
        )
    assert ex.value.response["Error"]["Code"] == "DryRunOperation"
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 412
    assert (
        ex.value.response["Error"]["Message"]
        == "An error occurred (DryRunOperation) when calling the ModifyInstanceAttribute operation: Request would have succeeded, but DryRun flag is set"
    )

    instance.modify_attribute(UserData={"Value": "this is my user data"})

    attribute = instance.describe_attribute(Attribute="userData")["UserData"]
    retrieved_user_data = attribute["Value"].encode("utf-8")
    assert decode_method(retrieved_user_data) == b"this is my user data"


@mock_ec2
def test_instance_attribute_source_dest_check():
    ec2 = boto3.resource("ec2", region_name="us-west-1")
    instance = ec2.create_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)[0]

    instance_attribute = instance.describe_attribute(Attribute="sourceDestCheck")
    assert instance_attribute.get("SourceDestCheck") == {"Value": True}

    # Set to false (note: Boto converts bool to string, eg 'false')

    with pytest.raises(ClientError) as ex:
        instance.modify_attribute(SourceDestCheck={"Value": False}, DryRun=True)
    assert ex.value.response["Error"]["Code"] == "DryRunOperation"
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 412
    assert (
        ex.value.response["Error"]["Message"]
        == "An error occurred (DryRunOperation) when calling the ModifyInstanceAttribute operation: Request would have succeeded, but DryRun flag is set"
    )

    instance.modify_attribute(SourceDestCheck={"Value": False})

    instance_attribute = instance.describe_attribute(Attribute="sourceDestCheck")
    assert instance_attribute.get("SourceDestCheck") == {"Value": False}

    # Set back to true
    instance.modify_attribute(SourceDestCheck={"Value": True})

    instance_attribute = instance.describe_attribute(Attribute="sourceDestCheck")
    assert instance_attribute.get("SourceDestCheck") == {"Value": True}


@mock_ec2
def test_user_data_with_run_instance():
    user_data = b"some user data"
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    instance = ec2.create_instances(
        ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1, UserData=user_data
    )[0]

    attribute = instance.describe_attribute(Attribute="userData")["UserData"]
    retrieved_user_data = attribute["Value"].encode("utf-8")
    decoded_user_data = decode_method(retrieved_user_data)
    assert decoded_user_data == b"some user data"


@mock_ec2
def test_run_instance_with_security_group_name():
    ec2 = boto3.resource("ec2", region_name="us-east-1")

    sec_group_name = str(uuid4())[0:6]

    with pytest.raises(ClientError) as ex:
        ec2.create_security_group(
            GroupName=sec_group_name, Description="d", DryRun=True
        )
    assert ex.value.response["Error"]["Code"] == "DryRunOperation"
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 412
    assert (
        ex.value.response["Error"]["Message"]
        == "An error occurred (DryRunOperation) when calling the CreateSecurityGroup operation: Request would have succeeded, but DryRun flag is set"
    )

    group = ec2.create_security_group(
        GroupName=sec_group_name, Description="some description"
    )

    res = ec2.create_instances(
        ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1, SecurityGroups=[sec_group_name]
    )
    instance = res[0]

    assert instance.security_groups == [
        {"GroupName": sec_group_name, "GroupId": group.id}
    ]


@mock_ec2
def test_run_instance_with_security_group_id():
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    sec_group_name = str(uuid4())
    group = ec2.create_security_group(
        GroupName=sec_group_name, Description="some description"
    )
    instance = ec2.create_instances(
        ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1, SecurityGroupIds=[group.id]
    )[0]

    assert instance.security_groups == [
        {"GroupName": sec_group_name, "GroupId": group.id}
    ]


@mock_ec2
@pytest.mark.parametrize("hibernate", [True, False])
def test_run_instance_with_additional_args(hibernate):
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    instance = ec2.create_instances(
        ImageId=EXAMPLE_AMI_ID,
        MinCount=1,
        MaxCount=1,
        InstanceType="t1.micro",
        Placement={"AvailabilityZone": "us-east-1b"},
        HibernationOptions={"Configured": hibernate},
    )[0]

    assert instance.instance_type == "t1.micro"
    assert instance.placement["AvailabilityZone"] == "us-east-1b"
    assert instance.hibernation_options == {"Configured": hibernate}


@mock_ec2
def test_run_instance_with_default_placement():
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    instance = ec2.create_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)[0]

    assert instance.placement["AvailabilityZone"] == "us-east-1a"


@mock_ec2
@mock.patch(
    "moto.ec2.models.instances.settings.EC2_ENABLE_INSTANCE_TYPE_VALIDATION",
    new_callable=mock.PropertyMock(return_value=True),
)
def test_run_instance_with_invalid_instance_type(m_flag):
    if settings.TEST_SERVER_MODE:
        raise SkipTest(
            "It is not possible to set the environment variable in server mode"
        )
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    with pytest.raises(ClientError) as ex:
        ec2.create_instances(
            ImageId=EXAMPLE_AMI_ID,
            InstanceType="invalid_type",
            MinCount=1,
            MaxCount=1,
            Placement={"AvailabilityZone": "us-east-1b"},
        )
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert (
        ex.value.response["Error"]["Message"]
        == "The instance type 'invalid_type' does not exist"
    )
    assert m_flag is True


@mock_ec2
def test_run_instance_with_availability_zone_not_from_region():
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    with pytest.raises(ClientError) as ex:
        ec2.create_instances(
            ImageId=EXAMPLE_AMI_ID,
            InstanceType="t2.nano",
            MinCount=1,
            MaxCount=1,
            Placement={"AvailabilityZone": "us-west-1b"},
        )

    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert (
        ex.value.response["Error"]["Message"]
        == "Invalid Availability Zone (us-west-1b)"
    )


@mock_ec2
def test_run_instance_with_subnet():
    client = boto3.client("ec2", region_name="eu-central-1")

    ip_networks = [
        (ipaddress.ip_network("10.0.0.0/16"), ipaddress.ip_network("10.0.99.0/24")),
        (
            ipaddress.ip_network("192.168.42.0/24"),
            ipaddress.ip_network("192.168.42.0/25"),
        ),
    ]

    # Tests instances are created with the correct IPs
    for vpc_cidr, subnet_cidr in ip_networks:
        resp = client.create_vpc(
            CidrBlock=str(vpc_cidr),
            AmazonProvidedIpv6CidrBlock=False,
            DryRun=False,
            InstanceTenancy="default",
        )
        vpc_id = resp["Vpc"]["VpcId"]

        resp = client.create_subnet(CidrBlock=str(subnet_cidr), VpcId=vpc_id)
        subnet_id = resp["Subnet"]["SubnetId"]

        resp = client.run_instances(
            ImageId=EXAMPLE_AMI_ID, MaxCount=1, MinCount=1, SubnetId=subnet_id
        )
        instance = resp["Instances"][0]
        assert instance["SubnetId"] == subnet_id

        priv_ipv4 = ipaddress.ip_address(str(instance["PrivateIpAddress"]))
        assert priv_ipv4 in subnet_cidr


@mock_ec2
def test_run_instance_with_specified_private_ipv4():
    client = boto3.client("ec2", region_name="eu-central-1")

    vpc_cidr = ipaddress.ip_network("192.168.42.0/24")
    subnet_cidr = ipaddress.ip_network("192.168.42.0/25")

    resp = client.create_vpc(
        CidrBlock=str(vpc_cidr),
        AmazonProvidedIpv6CidrBlock=False,
        DryRun=False,
        InstanceTenancy="default",
    )
    vpc_id = resp["Vpc"]["VpcId"]

    resp = client.create_subnet(CidrBlock=str(subnet_cidr), VpcId=vpc_id)
    subnet_id = resp["Subnet"]["SubnetId"]

    resp = client.run_instances(
        ImageId=EXAMPLE_AMI_ID,
        MaxCount=1,
        MinCount=1,
        SubnetId=subnet_id,
        PrivateIpAddress="192.168.42.5",
    )
    instance = resp["Instances"][0]
    assert instance["SubnetId"] == subnet_id
    assert instance["PrivateIpAddress"] == "192.168.42.5"


@mock_ec2
def test_run_instance_mapped_public_ipv4():
    client = boto3.client("ec2", region_name="eu-central-1")

    vpc_cidr = ipaddress.ip_network("192.168.42.0/24")
    subnet_cidr = ipaddress.ip_network("192.168.42.0/25")

    resp = client.create_vpc(
        CidrBlock=str(vpc_cidr),
        AmazonProvidedIpv6CidrBlock=False,
        DryRun=False,
        InstanceTenancy="default",
    )
    vpc_id = resp["Vpc"]["VpcId"]

    resp = client.create_subnet(CidrBlock=str(subnet_cidr), VpcId=vpc_id)
    subnet_id = resp["Subnet"]["SubnetId"]
    client.modify_subnet_attribute(
        SubnetId=subnet_id, MapPublicIpOnLaunch={"Value": True}
    )

    resp = client.run_instances(
        ImageId=EXAMPLE_AMI_ID, MaxCount=1, MinCount=1, SubnetId=subnet_id
    )
    instance = resp["Instances"][0]
    assert "PublicDnsName" in instance
    assert "PublicIpAddress" in instance
    assert len(instance["PublicDnsName"]) > 0
    assert len(instance["PublicIpAddress"]) > 0


@mock_ec2
def test_run_instance_with_nic_autocreated():
    ec2 = boto3.resource("ec2", "us-west-1")
    client = boto3.client("ec2", "us-west-1")
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    subnet = ec2.create_subnet(VpcId=vpc.id, CidrBlock="10.0.0.0/18")
    security_group1 = ec2.create_security_group(
        GroupName=str(uuid4()), Description="n/a"
    )
    security_group2 = ec2.create_security_group(
        GroupName=str(uuid4()), Description="n/a"
    )
    private_ip = "10.0.0.1"

    instance = ec2.create_instances(
        ImageId=EXAMPLE_AMI_ID,
        MinCount=1,
        MaxCount=1,
        SubnetId=subnet.id,
        SecurityGroups=[security_group1.group_name],
        SecurityGroupIds=[security_group2.group_id],
        PrivateIpAddress=private_ip,
    )[0]

    instance_eni = instance.network_interfaces_attribute
    assert len(instance_eni) == 1

    nii = instance_eni[0]["NetworkInterfaceId"]

    my_enis = client.describe_network_interfaces(NetworkInterfaceIds=[nii])[
        "NetworkInterfaces"
    ]
    assert len(my_enis) == 1
    eni = my_enis[0]

    assert instance.subnet_id == subnet.id
    assert len(instance.security_groups) == 2
    assert set([group["GroupId"] for group in instance.security_groups]) == {
        security_group1.id,
        security_group2.id,
    }

    assert eni["SubnetId"] == subnet.id
    assert len(eni["Groups"]) == 2
    assert set([group["GroupId"] for group in eni["Groups"]]) == {
        security_group1.id,
        security_group2.id,
    }
    assert len(eni["PrivateIpAddresses"]) == 1
    assert eni["PrivateIpAddresses"][0]["PrivateIpAddress"] == private_ip


@mock_ec2
def test_run_instance_with_nic_preexisting():
    ec2 = boto3.resource("ec2", "us-west-1")
    client = boto3.client("ec2", "us-west-1")
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    subnet = ec2.create_subnet(VpcId=vpc.id, CidrBlock="10.0.0.0/18")
    security_group1 = ec2.create_security_group(
        GroupName=str(uuid4()), Description="n/a"
    )
    security_group2 = ec2.create_security_group(
        GroupName=str(uuid4()), Description="n/a"
    )
    private_ip = "54.0.0.1"
    eni = ec2.create_network_interface(
        SubnetId=subnet.id,
        PrivateIpAddress=private_ip,
        Groups=[security_group1.group_id],
    )

    instance = ec2.create_instances(
        ImageId=EXAMPLE_AMI_ID,
        MinCount=1,
        MaxCount=1,
        NetworkInterfaces=[{"DeviceIndex": 0, "NetworkInterfaceId": eni.id}],
        SecurityGroupIds=[security_group2.group_id],
    )[0]

    assert instance.subnet_id == subnet.id

    nii = instance.network_interfaces_attribute[0]["NetworkInterfaceId"]

    all_enis = client.describe_network_interfaces(NetworkInterfaceIds=[nii])[
        "NetworkInterfaces"
    ]
    assert len(all_enis) == 1

    instance_enis = instance.network_interfaces_attribute
    assert len(instance_enis) == 1
    instance_eni = instance_enis[0]
    assert instance_eni["NetworkInterfaceId"] == eni.id

    assert instance_eni["SubnetId"] == subnet.id
    assert len(instance_eni["Groups"]) == 2
    assert set([group["GroupId"] for group in instance_eni["Groups"]]) == {
        security_group1.id,
        security_group2.id,
    }
    assert len(instance_eni["PrivateIpAddresses"]) == 1
    assert instance_eni["PrivateIpAddresses"][0]["PrivateIpAddress"] == private_ip


@mock_ec2
def test_run_instance_with_new_nic_and_security_groups():
    ec2 = boto3.resource("ec2", "us-west-1")
    client = boto3.client("ec2", "us-west-1")
    security_group1 = ec2.create_security_group(
        GroupName=str(uuid4()), Description="n/a"
    )
    security_group2 = ec2.create_security_group(
        GroupName=str(uuid4()), Description="n/a"
    )

    instance = ec2.create_instances(
        ImageId=EXAMPLE_AMI_ID,
        MinCount=1,
        MaxCount=1,
        NetworkInterfaces=[
            {
                "DeviceIndex": 0,
                "Groups": [security_group1.group_id, security_group2.group_id],
            }
        ],
    )[0]

    nii = instance.network_interfaces_attribute[0]["NetworkInterfaceId"]

    all_enis = client.describe_network_interfaces(NetworkInterfaceIds=[nii])[
        "NetworkInterfaces"
    ]
    assert len(all_enis) == 1

    instance_enis = instance.network_interfaces_attribute
    assert len(instance_enis) == 1
    instance_eni = instance_enis[0]

    assert len(instance_eni["Groups"]) == 2
    assert set([group["GroupId"] for group in instance_eni["Groups"]]) == {
        security_group1.id,
        security_group2.id,
    }


@mock_ec2
def test_instance_with_nic_attach_detach():
    ec2 = boto3.resource("ec2", "us-west-1")
    client = boto3.client("ec2", "us-west-1")
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    subnet = ec2.create_subnet(VpcId=vpc.id, CidrBlock="10.0.0.0/18")
    security_group1 = ec2.create_security_group(
        GroupName=str(uuid4()), Description="n/a"
    )
    security_group2 = ec2.create_security_group(
        GroupName=str(uuid4()), Description="n/a"
    )

    instance = ec2.create_instances(
        ImageId=EXAMPLE_AMI_ID,
        MinCount=1,
        MaxCount=1,
        SecurityGroupIds=[security_group1.group_id],
    )[0]

    eni = ec2.create_network_interface(SubnetId=subnet.id, Groups=[security_group2.id])
    eni_id = eni.id

    # Check initial instance and ENI data
    assert len(instance.network_interfaces_attribute) == 1

    assert [group["GroupId"] for group in eni.groups] == [security_group2.id]

    # Attach
    with pytest.raises(ClientError) as ex:
        client.attach_network_interface(
            NetworkInterfaceId=eni_id,
            InstanceId=instance.id,
            DeviceIndex=1,
            DryRun=True,
        )
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 412
    assert ex.value.response["Error"]["Code"] == "DryRunOperation"
    assert (
        ex.value.response["Error"]["Message"]
        == "An error occurred (DryRunOperation) when calling the AttachNetworkInterface operation: Request would have succeeded, but DryRun flag is set"
    )

    client.attach_network_interface(
        NetworkInterfaceId=eni_id, InstanceId=instance.id, DeviceIndex=1
    )

    # Check attached instance and ENI data
    instance.reload()
    assert len(instance.network_interfaces_attribute) == 2
    instance_eni = instance.network_interfaces_attribute[1]
    assert instance_eni["NetworkInterfaceId"] == eni_id
    assert len(instance_eni["Groups"]) == 2
    assert set([group["GroupId"] for group in instance_eni["Groups"]]) == {
        security_group1.id,
        security_group2.id,
    }

    eni = client.describe_network_interfaces(
        Filters=[{"Name": "network-interface-id", "Values": [eni_id]}]
    )["NetworkInterfaces"][0]
    assert len(eni["Groups"]) == 2
    assert set([group["GroupId"] for group in eni["Groups"]]) == {
        security_group1.id,
        security_group2.id,
    }

    # Detach
    with pytest.raises(ClientError) as ex:
        client.detach_network_interface(
            AttachmentId=instance_eni["Attachment"]["AttachmentId"], DryRun=True
        )
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 412
    assert ex.value.response["Error"]["Code"] == "DryRunOperation"
    assert (
        ex.value.response["Error"]["Message"]
        == "An error occurred (DryRunOperation) when calling the DetachNetworkInterface operation: Request would have succeeded, but DryRun flag is set"
    )

    client.detach_network_interface(
        AttachmentId=instance_eni["Attachment"]["AttachmentId"]
    )

    # Check detached instance and ENI data
    instance.reload()
    assert len(instance.network_interfaces_attribute) == 1

    eni = client.describe_network_interfaces(
        Filters=[{"Name": "network-interface-id", "Values": [eni_id]}]
    )["NetworkInterfaces"][0]
    assert [group["GroupId"] for group in eni["Groups"]] == [security_group2.id]

    # Detach with invalid attachment ID
    with pytest.raises(ClientError) as ex:
        client.detach_network_interface(AttachmentId="eni-attach-1234abcd")
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "RequestId" in ex.value.response["ResponseMetadata"]
    assert ex.value.response["Error"]["Code"] == "InvalidAttachmentID.NotFound"


@mock_ec2
def test_ec2_classic_has_public_ip_address():
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    instance = ec2.create_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)[0]
    assert instance.public_ip_address is not None
    assert instance.public_ip_address.replace(".", "-") in instance.public_dns_name
    assert instance.private_ip_address is not None
    assert instance.private_ip_address.replace(".", "-") in instance.private_dns_name


@mock_ec2
def test_run_instance_with_keypair():
    ec2 = boto3.resource("ec2", region_name="us-east-1")

    instance = ec2.create_instances(
        ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1, KeyName="keypair_name"
    )[0]

    assert instance.key_name == "keypair_name"


@mock_ec2
def test_describe_instances_with_keypair_filter():
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    for i in range(3):
        key_name = "kp-single" if i % 2 else "kp-multiple"
        ec2.create_instances(
            ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1, KeyName=key_name
        )
    test_data = [
        (["kp-single"], 1),
        (["kp-multiple"], 2),
        (["kp-single", "kp-multiple"], 3),
    ]
    for filter_values, expected_instance_count in test_data:
        _filter = [{"Name": "key-name", "Values": filter_values}]
        instances_found = list(ec2.instances.filter(Filters=_filter))
        assert len(instances_found) == expected_instance_count


@mock_ec2
@mock.patch(
    "moto.ec2.models.instances.settings.ENABLE_KEYPAIR_VALIDATION",
    new_callable=mock.PropertyMock(return_value=True),
)
def test_run_instance_with_invalid_keypair(m_flag):
    if settings.TEST_SERVER_MODE:
        raise SkipTest(
            "It is not possible to set the environment variable in server mode"
        )
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    keypair_name = "keypair_name"
    ec2.create_key_pair(KeyName=keypair_name)

    with pytest.raises(ClientError) as ex:
        ec2.create_instances(
            ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1, KeyName="not a key name"
        )[0]

    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert ex.value.response["Error"]["Code"] == "InvalidKeyPair.NotFound"
    assert m_flag is True


@mock_ec2
def test_run_instance_with_block_device_mappings():
    ec2_client = boto3.client("ec2", region_name="us-east-1")

    kwargs = {
        "MinCount": 1,
        "MaxCount": 1,
        "ImageId": EXAMPLE_AMI_ID,
        "KeyName": "the_key",
        "InstanceType": "t1.micro",
        "BlockDeviceMappings": [{"DeviceName": "/dev/sda2", "Ebs": {"VolumeSize": 50}}],
    }

    instance_id = ec2_client.run_instances(**kwargs)["Instances"][0]["InstanceId"]

    instances = ec2_client.describe_instances(InstanceIds=[instance_id])
    volume = instances["Reservations"][0]["Instances"][0]["BlockDeviceMappings"][0][
        "Ebs"
    ]

    volumes = ec2_client.describe_volumes(VolumeIds=[volume["VolumeId"]])
    assert volumes["Volumes"][0]["Size"] == 50


@mock_ec2
def test_run_instance_with_block_device_mappings_missing_ebs():
    ec2_client = boto3.client("ec2", region_name="us-east-1")

    kwargs = {
        "MinCount": 1,
        "MaxCount": 1,
        "ImageId": EXAMPLE_AMI_ID,
        "KeyName": "the_key",
        "InstanceType": "t1.micro",
        "BlockDeviceMappings": [{"DeviceName": "/dev/sda2"}],
    }
    with pytest.raises(ClientError) as ex:
        ec2_client.run_instances(**kwargs)

    assert ex.value.response["Error"]["Code"] == "MissingParameter"
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert (
        ex.value.response["Error"]["Message"]
        == "The request must contain the parameter ebs"
    )


@mock_ec2
def test_run_instance_with_block_device_mappings_using_no_device():
    ec2_client = boto3.client("ec2", region_name="us-east-1")

    kwargs = {
        "MinCount": 1,
        "MaxCount": 1,
        "ImageId": EXAMPLE_AMI_ID,
        "KeyName": "the_key",
        "InstanceType": "t1.micro",
        "BlockDeviceMappings": [{"DeviceName": "/dev/sda2", "NoDevice": ""}],
    }
    resp = ec2_client.run_instances(**kwargs)
    instance_id = resp["Instances"][0]["InstanceId"]

    instances = ec2_client.describe_instances(InstanceIds=[instance_id])
    # Assuming that /dev/sda2 is not the root device and that there is a /dev/sda1, boto would
    # create an instance with one block device instead of two.  However, moto's modeling of
    # BlockDeviceMappings is simplified, so we will accept that moto creates an instance without
    # block devices for now
    # assert "BlockDeviceMappings" not in instances["Reservations"][0]["Instances"][0]

    # moto gives the key with an empty list instead of not having it at all, that's also fine
    assert instances["Reservations"][0]["Instances"][0]["BlockDeviceMappings"] == []

    # passing None with NoDevice should raise ParamValidationError
    kwargs["BlockDeviceMappings"][0]["NoDevice"] = None
    with pytest.raises(ParamValidationError) as ex:
        ec2_client.run_instances(**kwargs)

    # passing a string other than "" with NoDevice should raise InvalidRequest
    kwargs["BlockDeviceMappings"][0]["NoDevice"] = "yes"
    with pytest.raises(ClientError) as ex:
        ec2_client.run_instances(**kwargs)

    assert ex.value.response["Error"]["Code"] == "InvalidRequest"
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert ex.value.response["Error"]["Message"] == "The request received was invalid"


@mock_ec2
def test_run_instance_with_block_device_mappings_missing_size():
    ec2_client = boto3.client("ec2", region_name="us-east-1")

    kwargs = {
        "MinCount": 1,
        "MaxCount": 1,
        "ImageId": EXAMPLE_AMI_ID,
        "KeyName": "the_key",
        "InstanceType": "t1.micro",
        "BlockDeviceMappings": [
            {"DeviceName": "/dev/sda2", "Ebs": {"VolumeType": "standard"}}
        ],
    }
    with pytest.raises(ClientError) as ex:
        ec2_client.run_instances(**kwargs)

    assert ex.value.response["Error"]["Code"] == "MissingParameter"
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert (
        ex.value.response["Error"]["Message"]
        == "The request must contain the parameter size or snapshotId"
    )


@mock_ec2
def test_run_instance_with_block_device_mappings_from_snapshot():
    ec2_client = boto3.client("ec2", region_name="us-east-1")
    ec2_resource = boto3.resource("ec2", region_name="us-east-1")

    volume_details = {
        "AvailabilityZone": "1a",
        "Size": 30,
    }

    volume = ec2_resource.create_volume(**volume_details)
    snapshot = volume.create_snapshot()
    kwargs = {
        "MinCount": 1,
        "MaxCount": 1,
        "ImageId": EXAMPLE_AMI_ID,
        "KeyName": "the_key",
        "InstanceType": "t1.micro",
        "BlockDeviceMappings": [
            {"DeviceName": "/dev/sda2", "Ebs": {"SnapshotId": snapshot.snapshot_id}}
        ],
    }

    resp = ec2_client.run_instances(**kwargs)
    instance_id = resp["Instances"][0]["InstanceId"]

    instances = ec2_client.describe_instances(InstanceIds=[instance_id])
    volume = instances["Reservations"][0]["Instances"][0]["BlockDeviceMappings"][0][
        "Ebs"
    ]

    volumes = ec2_client.describe_volumes(VolumeIds=[volume["VolumeId"]])

    assert volumes["Volumes"][0]["Size"] == 30
    assert volumes["Volumes"][0]["SnapshotId"] == snapshot.snapshot_id


@mock_ec2
def test_describe_instance_status_no_instances():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("ServerMode is not guaranteed to be empty")
    client = boto3.client("ec2", region_name="us-east-1")
    all_status = client.describe_instance_status()["InstanceStatuses"]
    assert len(all_status) == 0


@mock_ec2
def test_describe_instance_status_with_instances():
    client = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    instance = ec2.create_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)[0]

    all_status = client.describe_instance_status()["InstanceStatuses"]
    instance_ids = [s["InstanceId"] for s in all_status]
    assert instance.id in instance_ids

    my_status = [s for s in all_status if s["InstanceId"] == instance.id][0]
    assert my_status["InstanceStatus"]["Status"] == "ok"
    assert my_status["SystemStatus"]["Status"] == "ok"


@mock_ec2
def test_describe_instance_status_with_instance_filter_deprecated():
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    client = boto3.client("ec2", region_name="us-east-1")

    # We want to filter based on this one
    instance = ec2.create_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)[0]

    # This is just to setup the test
    ec2.create_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)

    all_status = client.describe_instance_status(InstanceIds=[instance.id])[
        "InstanceStatuses"
    ]
    assert len(all_status) == 1
    assert all_status[0]["InstanceId"] == instance.id

    # Call get_all_instance_status with a bad id should raise an error
    with pytest.raises(ClientError) as ex:
        client.describe_instance_status(InstanceIds=[instance.id, "i-1234abcd"])
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "RequestId" in ex.value.response["ResponseMetadata"]
    assert ex.value.response["Error"]["Code"] == "InvalidInstanceID.NotFound"


@mock_ec2
def test_describe_instance_credit_specifications():
    conn = boto3.client("ec2", region_name="us-west-1")

    # We want to filter based on this one
    reservation = conn.run_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)
    result = conn.describe_instance_credit_specifications(
        InstanceIds=[reservation["Instances"][0]["InstanceId"]]
    )
    assert (
        result["InstanceCreditSpecifications"][0]["InstanceId"]
        == reservation["Instances"][0]["InstanceId"]
    )


@mock_ec2
def test_describe_instance_status_with_instance_filter():
    conn = boto3.client("ec2", region_name="us-west-1")

    # We want to filter based on this one
    reservation = conn.run_instances(ImageId=EXAMPLE_AMI_ID, MinCount=3, MaxCount=3)
    instance1 = reservation["Instances"][0]
    instance2 = reservation["Instances"][1]
    instance3 = reservation["Instances"][2]
    conn.stop_instances(InstanceIds=[instance1["InstanceId"]])
    stopped_instance_ids = [instance1["InstanceId"]]
    running_instance_ids = sorted([instance2["InstanceId"], instance3["InstanceId"]])
    all_instance_ids = sorted(stopped_instance_ids + running_instance_ids)

    # Filter instance using the state name
    state_name_filter = {
        "running_and_stopped": [
            {"Name": "instance-state-name", "Values": ["running", "stopped"]}
        ],
        "running": [{"Name": "instance-state-name", "Values": ["running"]}],
        "stopped": [{"Name": "instance-state-name", "Values": ["stopped"]}],
    }

    found_statuses = conn.describe_instance_status(
        IncludeAllInstances=True, Filters=state_name_filter["running_and_stopped"]
    )["InstanceStatuses"]
    found_instance_ids = [status["InstanceId"] for status in found_statuses]
    for _id in all_instance_ids:
        assert _id in found_instance_ids

    found_statuses = conn.describe_instance_status(
        IncludeAllInstances=True, Filters=state_name_filter["running"]
    )["InstanceStatuses"]
    found_instance_ids = [status["InstanceId"] for status in found_statuses]
    for _id in stopped_instance_ids:
        assert _id not in found_instance_ids
    for _id in running_instance_ids:
        assert _id in found_instance_ids

    found_statuses = conn.describe_instance_status(
        IncludeAllInstances=True, Filters=state_name_filter["stopped"]
    )["InstanceStatuses"]
    found_instance_ids = [status["InstanceId"] for status in found_statuses]
    for _id in stopped_instance_ids:
        assert _id in found_instance_ids
    for _id in running_instance_ids:
        assert _id not in found_instance_ids

    # Filter instance using the state code
    state_code_filter = {
        "running_and_stopped": [
            {"Name": "instance-state-code", "Values": ["16", "80"]}
        ],
        "running": [{"Name": "instance-state-code", "Values": ["16"]}],
        "stopped": [{"Name": "instance-state-code", "Values": ["80"]}],
    }

    found_statuses = conn.describe_instance_status(
        IncludeAllInstances=True, Filters=state_code_filter["running_and_stopped"]
    )["InstanceStatuses"]
    found_instance_ids = [status["InstanceId"] for status in found_statuses]
    for _id in all_instance_ids:
        assert _id in found_instance_ids

    found_statuses = conn.describe_instance_status(
        IncludeAllInstances=True, Filters=state_code_filter["running"]
    )["InstanceStatuses"]
    found_instance_ids = [status["InstanceId"] for status in found_statuses]
    for _id in stopped_instance_ids:
        assert _id not in found_instance_ids
    for _id in running_instance_ids:
        assert _id in found_instance_ids

    found_statuses = conn.describe_instance_status(
        IncludeAllInstances=True, Filters=state_code_filter["stopped"]
    )["InstanceStatuses"]
    found_instance_ids = [status["InstanceId"] for status in found_statuses]
    for _id in stopped_instance_ids:
        assert _id in found_instance_ids
    for _id in running_instance_ids:
        assert _id not in found_instance_ids


@mock_ec2
def test_describe_instance_status_with_non_running_instances():
    client = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    reservation = ec2.create_instances(ImageId=EXAMPLE_AMI_ID, MinCount=3, MaxCount=3)
    instance1, instance2, instance3 = reservation
    instance1.stop()
    instance2.terminate()

    all_running_status = client.describe_instance_status()["InstanceStatuses"]
    assert instance1.id not in [status["InstanceId"] for status in all_running_status]
    assert instance2.id not in [status["InstanceId"] for status in all_running_status]
    assert instance3.id in [status["InstanceId"] for status in all_running_status]

    my_status = [s for s in all_running_status if s["InstanceId"] == instance3.id][0]
    assert my_status["InstanceState"] == {"Code": 16, "Name": "running"}

    all_status = client.describe_instance_status(IncludeAllInstances=True)[
        "InstanceStatuses"
    ]
    assert instance1.id in [status["InstanceId"] for status in all_status]
    assert instance2.id in [status["InstanceId"] for status in all_status]
    assert instance3.id in [status["InstanceId"] for status in all_status]

    status1 = next((s for s in all_status if s["InstanceId"] == instance1.id), None)
    assert status1["InstanceState"] == {"Code": 80, "Name": "stopped"}

    status2 = next((s for s in all_status if s["InstanceId"] == instance2.id), None)
    assert status2["InstanceState"] == {"Code": 48, "Name": "terminated"}

    status3 = next((s for s in all_status if s["InstanceId"] == instance3.id), None)
    assert status3["InstanceState"] == {"Code": 16, "Name": "running"}


@mock_ec2
def test_get_instance_by_security_group():
    client = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")

    instance = ec2.create_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)[0]

    security_group = ec2.create_security_group(
        GroupName=str(uuid4())[0:6], Description="test"
    )

    with pytest.raises(ClientError) as ex:
        client.modify_instance_attribute(
            InstanceId=instance.id, Groups=[security_group.id], DryRun=True
        )
    assert ex.value.response["Error"]["Code"] == "DryRunOperation"
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 412
    assert (
        ex.value.response["Error"]["Message"]
        == "An error occurred (DryRunOperation) when calling the ModifyInstanceAttribute operation: Request would have succeeded, but DryRun flag is set"
    )

    client.modify_instance_attribute(InstanceId=instance.id, Groups=[security_group.id])

    instance.reload()
    security_group_instances = instance.describe_attribute(Attribute="groupSet")[
        "Groups"
    ]

    assert len(security_group_instances) == 1
    assert security_group_instances == [{"GroupId": security_group.id}]


@mock_ec2
def test_modify_delete_on_termination():
    ec2_client = boto3.resource("ec2", region_name="us-west-1")
    result = ec2_client.create_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)
    instance = result[0]
    instance.load()
    assert instance.block_device_mappings[0]["Ebs"]["DeleteOnTermination"] is True
    instance.modify_attribute(
        BlockDeviceMappings=[
            {"DeviceName": "/dev/sda1", "Ebs": {"DeleteOnTermination": False}}
        ]
    )
    instance.load()
    assert instance.block_device_mappings[0]["Ebs"]["DeleteOnTermination"] is False


@mock_ec2
def test_create_instance_with_default_options():
    client = boto3.client("ec2", region_name="eu-west-1")

    def assert_instance(instance):
        # TODO: Add additional asserts for default instance response
        assert instance["ImageId"] == EXAMPLE_AMI_ID
        assert "KeyName" not in instance

    resp = client.run_instances(ImageId=EXAMPLE_AMI_ID, MaxCount=1, MinCount=1)
    assert_instance(resp["Instances"][0])

    resp = client.describe_instances(InstanceIds=[resp["Instances"][0]["InstanceId"]])
    assert_instance(resp["Reservations"][0]["Instances"][0])


@mock_ec2
def test_create_instance_ebs_optimized():
    ec2_resource = boto3.resource("ec2", region_name="eu-west-1")

    instance = ec2_resource.create_instances(
        ImageId=EXAMPLE_AMI_ID, MaxCount=1, MinCount=1, EbsOptimized=True
    )[0]
    instance.load()
    assert instance.ebs_optimized is True

    instance.modify_attribute(EbsOptimized={"Value": False})
    instance.load()
    assert instance.ebs_optimized is False

    instance = ec2_resource.create_instances(
        ImageId=EXAMPLE_AMI_ID, MaxCount=1, MinCount=1
    )[0]
    instance.load()
    assert instance.ebs_optimized is False


@mock_ec2
def test_run_multiple_instances_in_same_command():
    instance_count = 4
    client = boto3.client("ec2", region_name="us-east-1")
    instances = client.run_instances(
        ImageId=EXAMPLE_AMI_ID, MinCount=instance_count, MaxCount=instance_count
    )
    reservation_id = instances["ReservationId"]

    # TODO: use this filter when implemented
    # client.describe_instances(Filters=[{"Name": "reservation-id", "Values": [instances["ReservationId"]]}])["Reservations"]
    all_reservations = retrieve_all_reservations(client)
    my_reservation = [
        r for r in all_reservations if r["ReservationId"] == reservation_id
    ][0]

    assert len(my_reservation["Instances"]) == instance_count

    instances = my_reservation["Instances"]
    for i in range(0, instance_count):
        assert instances[i]["AmiLaunchIndex"] == i


@mock_ec2
def test_describe_instance_attribute():
    client = boto3.client("ec2", region_name="us-east-1")
    security_group_id = client.create_security_group(
        GroupName=str(uuid4()), Description="this is a test security group"
    )["GroupId"]
    resp = client.run_instances(
        ImageId=EXAMPLE_AMI_ID,
        MinCount=1,
        MaxCount=1,
        SecurityGroupIds=[security_group_id],
    )
    instance_id = resp["Instances"][0]["InstanceId"]

    valid_instance_attributes = [
        "instanceType",
        "kernel",
        "ramdisk",
        "userData",
        "disableApiTermination",
        "instanceInitiatedShutdownBehavior",
        "rootDeviceName",
        "blockDeviceMapping",
        "productCodes",
        "sourceDestCheck",
        "groupSet",
        "ebsOptimized",
        "sriovNetSupport",
    ]

    for valid_instance_attribute in valid_instance_attributes:
        response = client.describe_instance_attribute(
            InstanceId=instance_id, Attribute=valid_instance_attribute
        )
        if valid_instance_attribute == "groupSet":
            assert "Groups" in response
            assert len(response["Groups"]) == 1
            assert response["Groups"][0]["GroupId"] == security_group_id
        elif valid_instance_attribute == "userData":
            assert "UserData" in response
            assert response["UserData"] == {}

    invalid_instance_attributes = [
        "abc",
        "Kernel",
        "RamDisk",
        "userdata",
        "iNsTaNcEtYpE",
    ]

    for invalid_instance_attribute in invalid_instance_attributes:
        with pytest.raises(ClientError) as ex:
            client.describe_instance_attribute(
                InstanceId=instance_id, Attribute=invalid_instance_attribute
            )
        assert ex.value.response["Error"]["Code"] == "InvalidParameterValue"
        assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
        message = f"Value ({invalid_instance_attribute}) for parameter attribute is invalid. Unknown attribute."
        assert ex.value.response["Error"]["Message"] == message


@mock_ec2
def test_warn_on_invalid_ami():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Can't capture warnings in server mode.")
    ec2 = boto3.resource("ec2", "us-east-1")
    with pytest.warns(
        PendingDeprecationWarning,
        match=r"Could not find AMI with image-id:invalid-ami.+",
    ):
        ec2.create_instances(ImageId="invalid-ami", MinCount=1, MaxCount=1)


@mock_ec2
@mock.patch(
    "moto.ec2.models.instances.settings.ENABLE_AMI_VALIDATION",
    new_callable=mock.PropertyMock(return_value=True),
)
def test_error_on_invalid_ami(m_flag):
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Can't capture warnings in server mode.")
    ec2 = boto3.resource("ec2", "us-east-1")
    with pytest.raises(ClientError) as ex:
        ec2.create_instances(ImageId="ami-invalid", MinCount=1, MaxCount=1)
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert ex.value.response["Error"]["Code"] == "InvalidAMIID.NotFound"
    assert (
        ex.value.response["Error"]["Message"]
        == "The image id '[['ami-invalid']]' does not exist"
    )

    assert m_flag is True


@mock_ec2
@mock.patch(
    "moto.ec2.models.instances.settings.ENABLE_AMI_VALIDATION",
    new_callable=mock.PropertyMock(return_value=True),
)
def test_error_on_invalid_ami_format(m_flag):
    if settings.TEST_SERVER_MODE:
        raise SkipTest(
            "It is not possible to set the environment variable in server mode"
        )
    ec2 = boto3.resource("ec2", "us-east-1")
    with pytest.raises(ClientError) as ex:
        ec2.create_instances(ImageId="invalid-ami-format", MinCount=1, MaxCount=1)
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert ex.value.response["Error"]["Code"] == "InvalidAMIID.Malformed"
    assert (
        ex.value.response["Error"]["Message"]
        == 'Invalid id: "[\'invalid-ami-format\']" (expecting "ami-...")'
    )

    assert m_flag is True


@mock_ec2
def test_filter_wildcard_in_specified_tag_only():
    ec2_client = boto3.client("ec2", region_name="us-west-1")

    name = str(uuid4())[0:6]
    tags_name = [{"Key": "Name", "Value": f"{name} in wonderland"}]
    ec2_client.run_instances(
        ImageId=EXAMPLE_AMI_ID,
        MaxCount=1,
        MinCount=1,
        TagSpecifications=[{"ResourceType": "instance", "Tags": tags_name}],
    )

    tags_owner = [{"Key": "Owner", "Value": f"{name} in wonderland"}]
    ec2_client.run_instances(
        ImageId=EXAMPLE_AMI_ID,
        MaxCount=1,
        MinCount=1,
        TagSpecifications=[{"ResourceType": "instance", "Tags": tags_owner}],
    )

    # should only match the Name tag
    response = ec2_client.describe_instances(
        Filters=[{"Name": "tag:Name", "Values": [f"*{name}*"]}]
    )
    instances = [i for r in response["Reservations"] for i in r["Instances"]]
    assert len(instances) == 1
    assert instances[0]["Tags"][0]["Key"] == "Name"


@mock_ec2
def test_instance_termination_protection():
    client = boto3.client("ec2", region_name="us-west-1")

    resp = client.run_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)
    instance_id = resp["Instances"][0]["InstanceId"]

    client.modify_instance_attribute(
        InstanceId=instance_id, DisableApiTermination={"Value": True}
    )
    client.stop_instances(InstanceIds=[instance_id], Force=True)

    with pytest.raises(ClientError) as ex:
        client.terminate_instances(InstanceIds=[instance_id])
    error = ex.value.response["Error"]
    assert error["Code"] == "OperationNotPermitted"
    assert (
        f"The instance '{instance_id}' may not be terminated"
        in ex.value.response["Error"]["Message"]
    )

    # Use alternate request syntax for setting attribute.
    client.modify_instance_attribute(
        InstanceId=instance_id, Attribute="disableApiTermination", Value="false"
    )
    client.terminate_instances(InstanceIds=[instance_id])

    resp = client.describe_instances(InstanceIds=[instance_id])
    instances = resp["Reservations"][0]["Instances"]
    assert len(instances) == 1
    instance = instances[0]
    assert instance["State"]["Name"] == "terminated"


@mock_ec2
def test_terminate_unknown_instances():
    client = boto3.client("ec2", region_name="us-west-1")

    # Correct error message for single unknown instance
    with pytest.raises(ClientError) as ex:
        client.terminate_instances(InstanceIds=["i-12345678"])
    error = ex.value.response["Error"]
    assert error["Code"] == "InvalidInstanceID.NotFound"
    assert error["Message"] == "The instance ID 'i-12345678' does not exist"

    # Correct error message for multiple unknown instances
    with pytest.raises(ClientError) as ex:
        client.terminate_instances(InstanceIds=["i-12345678", "i-12345668"])
    error = ex.value.response["Error"]
    assert error["Code"] == "InvalidInstanceID.NotFound"
    assert error["Message"] == "The instance IDs 'i-12345678, i-12345668' do not exist"

    # Create an instance
    resp = client.run_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)
    instance_id = resp["Instances"][0]["InstanceId"]

    # Correct error message if one instance is known
    with pytest.raises(ClientError) as ex:
        client.terminate_instances(InstanceIds=["i-12345678", instance_id])
    error = ex.value.response["Error"]
    assert error["Code"] == "InvalidInstanceID.NotFound"
    assert error["Message"] == "The instance ID 'i-12345678' does not exist"

    # status = still running
    resp = client.describe_instances(InstanceIds=[instance_id])
    instance = resp["Reservations"][0]["Instances"][0]
    assert instance["State"]["Name"] == "running"


@mock_ec2
def test_instance_lifecycle():
    ec2_resource = boto3.resource("ec2", "us-west-1")

    result = ec2_resource.create_instances(
        ImageId=EXAMPLE_AMI_ID,
        MinCount=1,
        MaxCount=1,
        BlockDeviceMappings=[
            {
                "DeviceName": "/dev/sda1",
                "Ebs": {"VolumeSize": 50, "DeleteOnTermination": True},
            }
        ],
    )
    instance = result[0]

    assert instance.instance_lifecycle is None


@mock_ec2
@pytest.mark.parametrize(
    "launch_template_kind", ("LaunchTemplateId", "LaunchTemplateName")
)
def test_create_instance_with_launch_template_id_produces_no_warning(
    launch_template_kind,
):
    client, resource = (
        boto3.client("ec2", region_name="us-west-1"),
        boto3.resource("ec2", region_name="us-west-1"),
    )

    template = client.create_launch_template(
        LaunchTemplateName=str(uuid4()), LaunchTemplateData={"ImageId": EXAMPLE_AMI_ID}
    )["LaunchTemplate"]

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        resource.create_instances(
            MinCount=1,
            MaxCount=1,
            LaunchTemplate={launch_template_kind: template[launch_template_kind]},
        )


@mock_ec2
def test_create_instance_from_launch_template__process_tags():
    client = boto3.client("ec2", region_name="us-west-1")

    template = client.create_launch_template(
        LaunchTemplateName=str(uuid4()),
        LaunchTemplateData={
            "ImageId": EXAMPLE_AMI_ID,
            "TagSpecifications": [
                {"ResourceType": "instance", "Tags": [{"Key": "k", "Value": "v"}]}
            ],
        },
    )["LaunchTemplate"]

    instance = client.run_instances(
        MinCount=1,
        MaxCount=1,
        LaunchTemplate={"LaunchTemplateId": template["LaunchTemplateId"]},
    )["Instances"][0]

    assert instance["Tags"] == [{"Key": "k", "Value": "v"}]


@mock_ec2
def test_run_instance_and_associate_public_ip():
    ec2 = boto3.resource("ec2", "us-west-1")
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    subnet = ec2.create_subnet(VpcId=vpc.id, CidrBlock="10.0.0.0/18")

    # Do not pass AssociatePublicIpAddress-argument
    instance = ec2.create_instances(
        ImageId=EXAMPLE_AMI_ID,
        MinCount=1,
        MaxCount=1,
        NetworkInterfaces=[{"DeviceIndex": 0, "SubnetId": subnet.id}],
    )[0]
    interfaces = instance.network_interfaces_attribute
    addresses = interfaces[0]["PrivateIpAddresses"][0]
    assert addresses["Primary"] is True
    assert "PrivateIpAddress" in addresses
    assert "Association" not in addresses

    # Pass AssociatePublicIpAddress=False
    instance = ec2.create_instances(
        ImageId=EXAMPLE_AMI_ID,
        MinCount=1,
        MaxCount=1,
        NetworkInterfaces=[
            {"DeviceIndex": 0, "SubnetId": subnet.id, "AssociatePublicIpAddress": False}
        ],
    )[0]
    interfaces = instance.network_interfaces_attribute
    addresses = interfaces[0]["PrivateIpAddresses"][0]
    assert addresses["Primary"] is True
    assert "PrivateIpAddress" in addresses
    assert "Association" not in addresses

    # Pass AssociatePublicIpAddress=True
    instance = ec2.create_instances(
        ImageId=EXAMPLE_AMI_ID,
        MinCount=1,
        MaxCount=1,
        NetworkInterfaces=[
            {"DeviceIndex": 0, "SubnetId": subnet.id, "AssociatePublicIpAddress": True}
        ],
    )[0]
    interfaces = instance.network_interfaces_attribute
    addresses = interfaces[0]["PrivateIpAddresses"][0]
    assert addresses["Primary"] is True
    assert "PrivateIpAddress" in addresses
    assert "Association" in addresses
    # Only now should we have a PublicIp
    assert addresses["Association"]["IpOwnerId"] == ACCOUNT_ID
    assert "PublicIp" in addresses["Association"]


@mock_ec2
def test_run_instance_cannot_have_subnet_and_networkinterface_parameter():
    ec2 = boto3.resource("ec2", "us-west-1")
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    subnet = ec2.create_subnet(VpcId=vpc.id, CidrBlock="10.0.0.0/18")

    with pytest.raises(ClientError) as exc:
        ec2.create_instances(
            ImageId=EXAMPLE_AMI_ID,
            MinCount=1,
            MaxCount=1,
            SubnetId=subnet.id,
            NetworkInterfaces=[{"DeviceIndex": 0}],
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParameterCombination"
    assert (
        err["Message"]
        == "Network interfaces and an instance-level subnet ID may not be specified on the same request"
    )


@mock_ec2
def test_run_instance_in_subnet_with_nic_private_ip():
    vpc_cidr_block = "10.26.0.0/16"
    subnet_cidr_block = "10.26.1.0/24"
    private_ip = "10.26.1.3"
    ec2 = boto3.resource("ec2", region_name="eu-west-1")
    vpc = ec2.create_vpc(CidrBlock=vpc_cidr_block)
    subnet = ec2.create_subnet(
        VpcId=vpc.id,
        CidrBlock=subnet_cidr_block,
    )
    my_interface = {
        "SubnetId": subnet.id,
        "DeviceIndex": 0,
        "PrivateIpAddress": private_ip,
    }
    [instance] = ec2.create_instances(
        ImageId=EXAMPLE_AMI_ID, NetworkInterfaces=[my_interface], MinCount=1, MaxCount=1
    )
    assert instance.private_ip_address == private_ip

    interfaces = instance.network_interfaces_attribute
    address = interfaces[0]["PrivateIpAddresses"][0]
    assert "Association" not in address


@mock_ec2
def test_run_instance_in_subnet_with_nic_private_ip_and_public_association():
    vpc_cidr_block = "10.26.0.0/16"
    subnet_cidr_block = "10.26.1.0/24"
    primary_private_ip = "10.26.1.3"
    other_private_ip = "10.26.1.4"
    ec2 = boto3.resource("ec2", region_name="eu-west-1")
    vpc = ec2.create_vpc(CidrBlock=vpc_cidr_block)
    subnet = ec2.create_subnet(
        VpcId=vpc.id,
        CidrBlock=subnet_cidr_block,
    )
    my_interface = {
        "SubnetId": subnet.id,
        "DeviceIndex": 0,
        "AssociatePublicIpAddress": True,
        "PrivateIpAddresses": [
            {"Primary": True, "PrivateIpAddress": primary_private_ip},
            {"Primary": False, "PrivateIpAddress": other_private_ip},
        ],
    }
    [instance] = ec2.create_instances(
        ImageId=EXAMPLE_AMI_ID, NetworkInterfaces=[my_interface], MinCount=1, MaxCount=1
    )
    assert instance.private_ip_address == primary_private_ip

    interfaces = instance.network_interfaces_attribute
    address = interfaces[0]["PrivateIpAddresses"][0]
    assert address["Association"]["IpOwnerId"] == ACCOUNT_ID


@mock_ec2
def test_describe_instances_dryrun():
    client = boto3.client("ec2", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        client.describe_instances(DryRun=True)
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 412
    assert ex.value.response["Error"]["Code"] == "DryRunOperation"
    assert (
        ex.value.response["Error"]["Message"]
        == "An error occurred (DryRunOperation) when calling the DescribeInstances operation: Request would have succeeded, but DryRun flag is set"
    )


@mock_ec2
def test_describe_instances_filter_vpcid_via_networkinterface():
    vpc_cidr_block = "10.26.0.0/16"
    subnet_cidr_block = "10.26.1.0/24"
    ec2 = boto3.resource("ec2", region_name="eu-west-1")
    vpc = ec2.create_vpc(CidrBlock=vpc_cidr_block)
    subnet = ec2.create_subnet(
        VpcId=vpc.id, CidrBlock=subnet_cidr_block, AvailabilityZone="eu-west-1a"
    )
    my_interface = {
        "SubnetId": subnet.id,
        "DeviceIndex": 0,
        "PrivateIpAddresses": [{"Primary": True, "PrivateIpAddress": "10.26.1.3"}],
    }
    instance = ec2.create_instances(
        ImageId=EXAMPLE_AMI_ID, NetworkInterfaces=[my_interface], MinCount=1, MaxCount=1
    )[0]

    _filter = [{"Name": "vpc-id", "Values": [vpc.id]}]
    found = list(ec2.instances.filter(Filters=_filter))
    assert len(found) == 1
    assert found == [instance]


@mock_ec2
@mock_iam
def test_instance_iam_instance_profile():
    ec2_resource = boto3.resource("ec2", "us-west-1")
    iam = boto3.client("iam", "us-west-1")
    profile_name = "fake_profile"
    profile = iam.create_instance_profile(
        InstanceProfileName=profile_name,
    )

    result1 = ec2_resource.create_instances(
        ImageId=EXAMPLE_AMI_ID,
        MinCount=1,
        MaxCount=1,
        IamInstanceProfile={
            "Name": profile_name,
        },
    )
    instance = result1[0]
    assert "Arn" in instance.iam_instance_profile
    assert "Id" in instance.iam_instance_profile
    assert profile["InstanceProfile"]["Arn"] == instance.iam_instance_profile["Arn"]

    result2 = ec2_resource.create_instances(
        ImageId=EXAMPLE_AMI_ID,
        MinCount=1,
        MaxCount=1,
        IamInstanceProfile={
            "Arn": profile["InstanceProfile"]["Arn"],
        },
    )
    instance = result2[0]
    assert "Arn" in instance.iam_instance_profile
    assert "Id" in instance.iam_instance_profile
    assert profile["InstanceProfile"]["Arn"] == instance.iam_instance_profile["Arn"]


def retrieve_all_reservations(client, filters=[]):  # pylint: disable=W0102
    resp = client.describe_instances(Filters=filters)
    all_reservations = resp["Reservations"]
    next_token = resp.get("NextToken")
    while next_token:
        resp = client.describe_instances(Filters=filters, NextToken=next_token)
        all_reservations.extend(resp["Reservations"])
        next_token = resp.get("NextToken")
    return all_reservations


def retrieve_all_instances(client, filters=[]):  # pylint: disable=W0102
    reservations = retrieve_all_reservations(client, filters)
    return [i for r in reservations for i in r["Instances"]]


@mock_ec2
def test_run_multiple_instances_with_single_nic_template():
    ec2 = boto3.resource("ec2", "us-west-1")
    client = boto3.client("ec2", "us-west-1")
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    subnet = ec2.create_subnet(VpcId=vpc.id, CidrBlock="10.0.0.0/18")
    security_group1 = ec2.create_security_group(
        GroupName=str(uuid4()), Description="n/a"
    )

    instances = ec2.create_instances(
        ImageId=EXAMPLE_AMI_ID,
        MinCount=2,
        MaxCount=2,
        NetworkInterfaces=[
            {
                "AssociatePublicIpAddress": False,
                "DeleteOnTermination": True,
                "DeviceIndex": 0,
                "Groups": [security_group1.group_id],
                "SubnetId": subnet.id,
                "InterfaceType": "interface",
            }
        ],
    )

    enis = []

    for instance in instances:
        instance_eni = instance.network_interfaces_attribute
        assert len(instance_eni) == 1

        nii = instance_eni[0]["NetworkInterfaceId"]

        my_enis = client.describe_network_interfaces(NetworkInterfaceIds=[nii])[
            "NetworkInterfaces"
        ]
        assert len(my_enis) == 1
        eni = my_enis[0]

        assert instance.subnet_id == subnet.id

        assert eni["SubnetId"] == subnet.id
        assert len(eni["Groups"]) == 1
        assert [group["GroupId"] for group in eni["Groups"]] == [security_group1.id]
        assert len(eni["PrivateIpAddresses"]) == 1
        assert eni["PrivateIpAddresses"][0]["PrivateIpAddress"] is not None

        enis.append(eni)

    instance_0_ip = enis[0]["PrivateIpAddresses"][0]["PrivateIpAddress"]
    instance_1_ip = enis[1]["PrivateIpAddresses"][0]["PrivateIpAddress"]

    assert instance_0_ip != instance_1_ip
