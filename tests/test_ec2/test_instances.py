from botocore.exceptions import ClientError

import pytest
from unittest import SkipTest

import base64
import ipaddress

import boto
import boto3
from boto.ec2.instance import Reservation, InstanceAttribute
from boto.exception import EC2ResponseError
from freezegun import freeze_time
import sure  # noqa # pylint: disable=unused-import

from moto import mock_ec2_deprecated, mock_ec2, settings
from moto.core import ACCOUNT_ID
from tests import EXAMPLE_AMI_ID
from tests.helpers import requires_boto_gte
from uuid import uuid4


decode_method = base64.decodebytes

################ Test Readme ###############
def add_servers(ami_id, count):
    conn = boto.connect_ec2()
    for _ in range(count):
        conn.run_instances(ami_id)


# Has boto3 equivalent
@mock_ec2_deprecated
def test_add_servers():
    add_servers(EXAMPLE_AMI_ID, 2)

    conn = boto.connect_ec2()
    reservations = conn.get_all_reservations()
    assert len(reservations) == 2
    instance1 = reservations[0].instances[0]
    assert instance1.image_id == EXAMPLE_AMI_ID


@mock_ec2
def test_add_servers_boto3():
    client = boto3.client("ec2", region_name="us-east-1")
    resp = client.run_instances(ImageId=EXAMPLE_AMI_ID, MinCount=2, MaxCount=2)
    for i in resp["Instances"]:
        i["ImageId"].should.equal(EXAMPLE_AMI_ID)

    instances = client.describe_instances(
        InstanceIds=[i["InstanceId"] for i in resp["Instances"]]
    )["Reservations"][0]["Instances"]
    instances.should.have.length_of(2)
    for i in instances:
        i["ImageId"].should.equal(EXAMPLE_AMI_ID)


############################################


# Has boto3 equivalent
@freeze_time("2014-01-01 05:00:00")
@mock_ec2_deprecated
def test_instance_launch_and_terminate():
    conn = boto.ec2.connect_to_region("us-east-1")

    with pytest.raises(EC2ResponseError) as ex:
        reservation = conn.run_instances(EXAMPLE_AMI_ID, dry_run=True)
    ex.value.error_code.should.equal("DryRunOperation")
    ex.value.status.should.equal(412)
    ex.value.message.should.equal(
        "An error occurred (DryRunOperation) when calling the RunInstance operation: Request would have succeeded, but DryRun flag is set"
    )

    reservation = conn.run_instances(EXAMPLE_AMI_ID)
    reservation.should.be.a(Reservation)
    reservation.instances.should.have.length_of(1)
    instance = reservation.instances[0]
    instance.state.should.equal("pending")

    reservations = conn.get_all_reservations()
    reservations.should.have.length_of(1)
    reservations[0].id.should.equal(reservation.id)
    instances = reservations[0].instances
    instances.should.have.length_of(1)
    instance = instances[0]
    instance.id.should.equal(instance.id)
    instance.state.should.equal("running")
    instance.launch_time.should.equal("2014-01-01T05:00:00.000Z")
    instance.vpc_id.shouldnt.equal(None)
    instance.placement.should.equal("us-east-1a")

    root_device_name = instance.root_device_name
    instance.block_device_mapping[root_device_name].status.should.equal("in-use")
    volume_id = instance.block_device_mapping[root_device_name].volume_id
    volume_id.should.match(r"vol-\w+")

    volume = conn.get_all_volumes(volume_ids=[volume_id])[0]
    volume.attach_data.instance_id.should.equal(instance.id)
    volume.status.should.equal("in-use")

    with pytest.raises(EC2ResponseError) as ex:
        conn.terminate_instances([instance.id], dry_run=True)
    ex.value.error_code.should.equal("DryRunOperation")
    ex.value.status.should.equal(412)
    ex.value.message.should.equal(
        "An error occurred (DryRunOperation) when calling the TerminateInstance operation: Request would have succeeded, but DryRun flag is set"
    )

    conn.terminate_instances([instance.id])

    reservations = conn.get_all_reservations()
    instance = reservations[0].instances[0]
    instance.state.should.equal("terminated")


@freeze_time("2014-01-01 05:00:00")
@mock_ec2
def test_instance_launch_and_terminate_boto3():
    client = boto3.client("ec2", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        client.run_instances(
            ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1, DryRun=True
        )
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(412)
    ex.value.response["Error"]["Code"].should.equal("DryRunOperation")
    ex.value.response["Error"]["Message"].should.equal(
        "An error occurred (DryRunOperation) when calling the RunInstance operation: Request would have succeeded, but DryRun flag is set"
    )

    reservation = client.run_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)
    reservation["Instances"].should.have.length_of(1)
    instance = reservation["Instances"][0]
    instance["State"].should.equal({"Code": 0, "Name": "pending"})
    instance_id = instance["InstanceId"]

    reservations = client.describe_instances(InstanceIds=[instance_id])["Reservations"]
    reservations.should.have.length_of(1)
    reservations[0]["ReservationId"].should.equal(reservation["ReservationId"])
    instances = reservations[0]["Instances"]
    instances.should.have.length_of(1)
    instance = instances[0]
    instance["InstanceId"].should.equal(instance_id)
    instance["State"].should.equal({"Code": 16, "Name": "running"})
    if settings.TEST_SERVER_MODE:
        # Exact value can't be determined in ServerMode
        instance.should.have.key("LaunchTime")
    else:
        launch_time = instance["LaunchTime"].strftime("%Y-%m-%dT%H:%M:%S.000Z")
        launch_time.should.equal("2014-01-01T05:00:00.000Z")
    instance["VpcId"].shouldnt.equal(None)
    instance["Placement"]["AvailabilityZone"].should.equal("us-east-1a")

    root_device_name = instance["RootDeviceName"]
    mapping = instance["BlockDeviceMappings"][0]
    mapping["DeviceName"].should.equal(root_device_name)
    mapping["Ebs"]["Status"].should.equal("in-use")
    volume_id = mapping["Ebs"]["VolumeId"]
    volume_id.should.match(r"vol-\w+")

    volume = client.describe_volumes(VolumeIds=[volume_id])["Volumes"][0]
    volume["Attachments"][0]["InstanceId"].should.equal(instance_id)
    volume["State"].should.equal("in-use")

    with pytest.raises(ClientError) as ex:
        client.terminate_instances(InstanceIds=[instance_id], DryRun=True)
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(412)
    ex.value.response["Error"]["Code"].should.equal("DryRunOperation")
    ex.value.response["Error"]["Message"].should.equal(
        "An error occurred (DryRunOperation) when calling the TerminateInstance operation: Request would have succeeded, but DryRun flag is set"
    )

    client.terminate_instances(InstanceIds=[instance_id])

    reservations = client.describe_instances(InstanceIds=[instance_id])["Reservations"]
    instance = reservations[0]["Instances"][0]
    instance["State"].should.equal({"Code": 48, "Name": "terminated"})


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
        all_volumes_ids.shouldnt.contain(my_id)


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
        all_volumes_ids.should.contain(my_id)


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
    volume.state.should.equal("available")


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
        response["State"].should.equal("detaching")

    instance.terminate()
    instance.wait_until_terminated()

    all_volumes_ids = [v.id for v in list(ec2_resource.volumes.all())]
    for my_id in my_volume_ids:
        all_volumes_ids.should.contain(my_id)


@mock_ec2
def test_instance_detach_volume_wrong_path():
    ec2_resource = boto3.resource("ec2", "us-west-1")
    result = ec2_resource.create_instances(
        ImageId=EXAMPLE_AMI_ID,
        MinCount=1,
        MaxCount=1,
        BlockDeviceMappings=[{"DeviceName": "/dev/sda1", "Ebs": {"VolumeSize": 50}},],
    )
    instance = result[0]
    for volume in instance.volumes.all():
        with pytest.raises(ClientError) as ex:
            instance.detach_volume(VolumeId=volume.volume_id, Device="/dev/sdf")

        ex.value.response["Error"]["Code"].should.equal("InvalidAttachment.NotFound")
        ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
        ex.value.response["Error"]["Message"].should.equal(
            "The volume {0} is not attached to instance {1} as device {2}".format(
                volume.volume_id, instance.instance_id, "/dev/sdf"
            )
        )


# Has boto3 equivalent
@mock_ec2_deprecated
def test_terminate_empty_instances():
    conn = boto.connect_ec2("the_key", "the_secret")
    conn.terminate_instances.when.called_with([]).should.throw(EC2ResponseError)


@mock_ec2
def test_terminate_empty_instances_boto3():
    client = boto3.client("ec2", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        client.terminate_instances(InstanceIds=[])
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["Error"]["Code"].should.equal("InvalidParameterCombination")
    ex.value.response["Error"]["Message"].should.equal("No instances specified")


# Has boto3 equivalent
@freeze_time("2014-01-01 05:00:00")
@mock_ec2_deprecated
def test_instance_attach_volume():
    conn = boto.connect_ec2("the_key", "the_secret")
    reservation = conn.run_instances(EXAMPLE_AMI_ID)
    instance = reservation.instances[0]

    vol1 = conn.create_volume(size=36, zone=conn.region.name)
    vol1.attach(instance.id, "/dev/sda1")
    vol1.update()
    vol2 = conn.create_volume(size=65, zone=conn.region.name)
    vol2.attach(instance.id, "/dev/sdb1")
    vol2.update()
    vol3 = conn.create_volume(size=130, zone=conn.region.name)
    vol3.attach(instance.id, "/dev/sdc1")
    vol3.update()

    reservations = conn.get_all_reservations()
    instance = reservations[0].instances[0]

    instance.block_device_mapping.should.have.length_of(3)

    for v in conn.get_all_volumes(
        volume_ids=[instance.block_device_mapping["/dev/sdc1"].volume_id]
    ):
        v.attach_data.instance_id.should.equal(instance.id)
        # can do due to freeze_time decorator.
        v.attach_data.attach_time.should.equal(instance.launch_time)
        # can do due to freeze_time decorator.
        v.create_time.should.equal(instance.launch_time)
        v.region.name.should.equal(instance.region.name)
        v.status.should.equal("in-use")


@freeze_time("2014-01-01 05:00:00")
@mock_ec2
def test_instance_attach_volume_boto3():
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

    instance.block_device_mappings.should.have.length_of(3)
    expected_vol3_id = [
        m["Ebs"]["VolumeId"]
        for m in instance.block_device_mappings
        if m["DeviceName"] == "/dev/sdc1"
    ][0]

    expected_vol3 = ec2.Volume(expected_vol3_id)
    expected_vol3.attachments[0]["InstanceId"].should.equal(instance.id)
    expected_vol3.availability_zone.should.equal("us-east-1a")
    expected_vol3.state.should.equal("in-use")
    if not settings.TEST_SERVER_MODE:
        # FreezeTime does not work in ServerMode
        expected_vol3.attachments[0]["AttachTime"].should.equal(instance.launch_time)
        expected_vol3.create_time.should.equal(instance.launch_time)


# Has boto3 equivalent
@mock_ec2_deprecated
def test_get_instances_by_id():
    conn = boto.connect_ec2()
    reservation = conn.run_instances(EXAMPLE_AMI_ID, min_count=2)
    instance1, instance2 = reservation.instances

    reservations = conn.get_all_reservations(instance_ids=[instance1.id])
    reservations.should.have.length_of(1)
    reservation = reservations[0]
    reservation.instances.should.have.length_of(1)
    reservation.instances[0].id.should.equal(instance1.id)

    reservations = conn.get_all_reservations(instance_ids=[instance1.id, instance2.id])
    reservations.should.have.length_of(1)
    reservation = reservations[0]
    reservation.instances.should.have.length_of(2)
    instance_ids = [instance.id for instance in reservation.instances]
    instance_ids.should.equal([instance1.id, instance2.id])

    # Call get_all_reservations with a bad id should raise an error
    with pytest.raises(EC2ResponseError) as cm:
        conn.get_all_reservations(instance_ids=[instance1.id, "i-1234abcd"])
    cm.value.code.should.equal("InvalidInstanceID.NotFound")
    cm.value.status.should.equal(400)
    cm.value.request_id.should_not.be.none


@mock_ec2
def test_get_instances_by_id_boto3():
    client = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    reservation = client.run_instances(ImageId=EXAMPLE_AMI_ID, MinCount=2, MaxCount=2)
    instance1 = ec2.Instance(reservation["Instances"][0]["InstanceId"])
    instance2 = ec2.Instance(reservation["Instances"][1]["InstanceId"])

    reservations = client.describe_instances(InstanceIds=[instance1.id])["Reservations"]
    reservations.should.have.length_of(1)
    reservation = reservations[0]
    reservation["Instances"].should.have.length_of(1)
    reservation["Instances"][0]["InstanceId"].should.equal(instance1.id)

    reservations = client.describe_instances(InstanceIds=[instance1.id, instance2.id])[
        "Reservations"
    ]
    reservations.should.have.length_of(1)
    reservation = reservations[0]
    reservation["Instances"].should.have.length_of(2)
    instance_ids = [instance["InstanceId"] for instance in reservation["Instances"]]
    set(instance_ids).should.equal(set([instance1.id, instance2.id]))

    # Call describe_instances with a bad id should raise an error
    with pytest.raises(ClientError) as ex:
        client.describe_instances(InstanceIds=[instance1.id, "i-1234abcd"])
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["ResponseMetadata"].should.have.key("RequestId")
    ex.value.response["Error"]["Code"].should.equal("InvalidInstanceID.NotFound")


@mock_ec2
def test_get_paginated_instances():
    client = boto3.client("ec2", region_name="us-east-1")
    conn = boto3.resource("ec2", "us-east-1")
    instances = []
    for i in range(12):
        instances.extend(
            conn.create_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)
        )
    instance_ids = [i.id for i in instances]

    resp1 = client.describe_instances(InstanceIds=instance_ids, MaxResults=5)
    res1 = resp1["Reservations"]
    res1.should.have.length_of(5)
    next_token = resp1["NextToken"]

    next_token.should_not.be.none

    resp2 = client.describe_instances(InstanceIds=instance_ids, NextToken=next_token)
    resp2["Reservations"].should.have.length_of(7)  # 12 total - 5 from the first call
    assert "NextToken" not in resp2  # This is it - no more pages

    for i in instances:
        i.terminate()


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
    len(instances["Instances"][0]["Tags"]).should.equal(3)


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
        volumes = ec2.describe_volumes(VolumeIds=[instance_volume["VolumeId"]]).get(
            "Volumes"
        )
        for volume in volumes:
            sorted(volume["Tags"], key=lambda i: i["Key"]).should.equal(volume_tags)


# Has boto3 equivalent
@mock_ec2_deprecated
def test_get_instances_filtering_by_state():
    conn = boto.connect_ec2()
    reservation = conn.run_instances(EXAMPLE_AMI_ID, min_count=3)
    instance1, instance2, instance3 = reservation.instances

    conn.terminate_instances([instance1.id])

    reservations = conn.get_all_reservations(filters={"instance-state-name": "running"})
    reservations.should.have.length_of(1)
    # Since we terminated instance1, only instance2 and instance3 should be
    # returned
    instance_ids = [instance.id for instance in reservations[0].instances]
    set(instance_ids).should.equal(set([instance2.id, instance3.id]))

    reservations = conn.get_all_reservations(
        [instance2.id], filters={"instance-state-name": "running"}
    )
    reservations.should.have.length_of(1)
    instance_ids = [instance.id for instance in reservations[0].instances]
    instance_ids.should.equal([instance2.id])

    reservations = conn.get_all_reservations(
        [instance2.id], filters={"instance-state-name": "terminated"}
    )
    list(reservations).should.equal([])

    # get_all_reservations should still return all 3
    reservations = conn.get_all_reservations()
    reservations[0].instances.should.have.length_of(3)

    conn.get_all_reservations.when.called_with(
        filters={"not-implemented-filter": "foobar"}
    ).should.throw(NotImplementedError)


@mock_ec2
def test_get_instances_filtering_by_state_boto3():
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
    instance_ids.shouldnt.contain(instance1.id)
    instance_ids.should.contain(instance2.id)
    instance_ids.should.contain(instance3.id)

    reservations = client.describe_instances(
        InstanceIds=[instance2.id],
        Filters=[{"Name": "instance-state-name", "Values": ["running"]}],
    )["Reservations"]
    reservations.should.have.length_of(1)
    instance_ids = [instance["InstanceId"] for instance in reservations[0]["Instances"]]
    instance_ids.should.equal([instance2.id])

    reservations = client.describe_instances(
        InstanceIds=[instance2.id],
        Filters=[{"Name": "instance-state-name", "Values": ["terminated"]}],
    )["Reservations"]
    reservations.should.equal([])

    # get_all_reservations should still return all 3
    instances = retrieve_all_instances(client, filters=[])
    instance_ids = [i["InstanceId"] for i in instances]
    instance_ids.should.contain(instance1.id)
    instance_ids.should.contain(instance2.id)
    instance_ids.should.contain(instance3.id)

    if not settings.TEST_SERVER_MODE:
        # ServerMode will just throw a generic 500
        filters = [{"Name": "not-implemented-filter", "Values": ["foobar"]}]
        client.describe_instances.when.called_with(Filters=filters).should.throw(
            NotImplementedError
        )


# Has boto3 equivalent
@mock_ec2_deprecated
def test_get_instances_filtering_by_instance_id():
    conn = boto.connect_ec2()
    reservation = conn.run_instances(EXAMPLE_AMI_ID, min_count=3)
    instance1, instance2, _ = reservation.instances

    reservations = conn.get_all_reservations(filters={"instance-id": instance1.id})
    # get_all_reservations should return just instance1
    reservations[0].instances.should.have.length_of(1)
    reservations[0].instances[0].id.should.equal(instance1.id)

    reservations = conn.get_all_reservations(
        filters={"instance-id": [instance1.id, instance2.id]}
    )
    # get_all_reservations should return two
    reservations[0].instances.should.have.length_of(2)

    reservations = conn.get_all_reservations(filters={"instance-id": "non-existing-id"})
    reservations.should.have.length_of(0)


@mock_ec2
def test_get_instances_filtering_by_instance_id_boto3():
    ec2 = boto3.resource("ec2", "us-west-1")
    client = boto3.client("ec2", "us-west-1")
    reservation = ec2.create_instances(ImageId=EXAMPLE_AMI_ID, MinCount=3, MaxCount=3)
    instance1, instance2, _ = reservation

    def _filter(values, exists=True):
        f = [{"Name": "instance-id", "Values": values}]
        r = client.describe_instances(Filters=f)["Reservations"]
        if exists:
            r[0]["Instances"].should.have.length_of(len(values))
            found_ids = [i["InstanceId"] for i in r[0]["Instances"]]
            set(found_ids).should.equal(set(values))
        else:
            r.should.have.length_of(0)

    _filter(values=[instance1.id])
    _filter(values=[instance1.id, instance2.id])
    _filter(values=["non-existing-id"], exists=False)


# Has boto3 equivalent
@mock_ec2_deprecated
def test_get_instances_filtering_by_instance_type():
    conn = boto.connect_ec2()
    reservation1 = conn.run_instances(EXAMPLE_AMI_ID, instance_type="m1.small")
    instance1 = reservation1.instances[0]
    reservation2 = conn.run_instances(EXAMPLE_AMI_ID, instance_type="m1.small")
    instance2 = reservation2.instances[0]
    reservation3 = conn.run_instances(EXAMPLE_AMI_ID, instance_type="t1.micro")
    instance3 = reservation3.instances[0]

    reservations = conn.get_all_reservations(filters={"instance-type": "m1.small"})
    # get_all_reservations should return instance1,2
    reservations.should.have.length_of(2)
    reservations[0].instances.should.have.length_of(1)
    reservations[1].instances.should.have.length_of(1)
    instance_ids = [reservations[0].instances[0].id, reservations[1].instances[0].id]
    set(instance_ids).should.equal(set([instance1.id, instance2.id]))

    reservations = conn.get_all_reservations(filters={"instance-type": "t1.micro"})
    # get_all_reservations should return one
    reservations.should.have.length_of(1)
    reservations[0].instances.should.have.length_of(1)
    reservations[0].instances[0].id.should.equal(instance3.id)

    reservations = conn.get_all_reservations(
        filters={"instance-type": ["t1.micro", "m1.small"]}
    )
    reservations.should.have.length_of(3)
    reservations[0].instances.should.have.length_of(1)
    reservations[1].instances.should.have.length_of(1)
    reservations[2].instances.should.have.length_of(1)
    instance_ids = [
        reservations[0].instances[0].id,
        reservations[1].instances[0].id,
        reservations[2].instances[0].id,
    ]
    set(instance_ids).should.equal(set([instance1.id, instance2.id, instance3.id]))

    reservations = conn.get_all_reservations(filters={"instance-type": "bogus"})
    # bogus instance-type should return none
    reservations.should.have.length_of(0)


@mock_ec2
def test_get_instances_filtering_by_instance_type_boto3():
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
    set(instance_ids).should.contain(instance1.id)
    set(instance_ids).should.contain(instance2.id)

    instances = retrieve_all_instances(
        client, [{"Name": "instance-type", "Values": ["t1.micro"]}]
    )
    instance_ids = [i["InstanceId"] for i in instances]
    instance_ids.should.contain(instance3.id)

    instances = retrieve_all_instances(
        client, [{"Name": "instance-type", "Values": ["t1.micro", "m1.small"]}]
    )
    instance_ids = [i["InstanceId"] for i in instances]
    instance_ids.should.contain(instance1.id)
    instance_ids.should.contain(instance2.id)
    instance_ids.should.contain(instance3.id)

    res = client.describe_instances(
        Filters=[{"Name": "instance-type", "Values": ["bogus"]}]
    )
    res["Reservations"].should.have.length_of(0)


# Has boto3 equivalent
@mock_ec2_deprecated
def test_get_instances_filtering_by_reason_code():
    conn = boto.connect_ec2()
    reservation = conn.run_instances(EXAMPLE_AMI_ID, min_count=3)
    instance1, instance2, instance3 = reservation.instances
    instance1.stop()
    instance2.terminate()

    reservations = conn.get_all_reservations(
        filters={"state-reason-code": "Client.UserInitiatedShutdown"}
    )
    # get_all_reservations should return instance1 and instance2
    reservations[0].instances.should.have.length_of(2)
    set([instance1.id, instance2.id]).should.equal(
        set([i.id for i in reservations[0].instances])
    )

    reservations = conn.get_all_reservations(filters={"state-reason-code": ""})
    # get_all_reservations should return instance 3
    reservations[0].instances.should.have.length_of(1)
    reservations[0].instances[0].id.should.equal(instance3.id)


@mock_ec2
def test_get_instances_filtering_by_reason_code_boto3():
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

    instance_ids.should.contain(instance1.id)
    instance_ids.should.contain(instance2.id)
    instance_ids.shouldnt.contain(instance3.id)

    filters = [{"Name": "state-reason-code", "Values": [""]}]
    instances = retrieve_all_instances(client, filters)
    instance_ids = [i["InstanceId"] for i in instances]
    instance_ids.should.contain(instance3.id)
    instance_ids.shouldnt.contain(instance1.id)
    instance_ids.shouldnt.contain(instance2.id)


# Has boto3 equivalent
@mock_ec2_deprecated
def test_get_instances_filtering_by_source_dest_check():
    conn = boto.connect_ec2()
    reservation = conn.run_instances(EXAMPLE_AMI_ID, min_count=2)
    instance1, instance2 = reservation.instances
    conn.modify_instance_attribute(
        instance1.id, attribute="sourceDestCheck", value=False
    )

    source_dest_check_false = conn.get_all_reservations(
        filters={"source-dest-check": "false"}
    )
    source_dest_check_true = conn.get_all_reservations(
        filters={"source-dest-check": "true"}
    )

    source_dest_check_false[0].instances.should.have.length_of(1)
    source_dest_check_false[0].instances[0].id.should.equal(instance1.id)

    source_dest_check_true[0].instances.should.have.length_of(1)
    source_dest_check_true[0].instances[0].id.should.equal(instance2.id)


@mock_ec2
def test_get_instances_filtering_by_source_dest_check_boto3():
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

    [i["InstanceId"] for i in instances_false].should.contain(instance1.id)
    [i["InstanceId"] for i in instances_false].shouldnt.contain(instance2.id)

    [i["InstanceId"] for i in instances_true].shouldnt.contain(instance1.id)
    [i["InstanceId"] for i in instances_true].should.contain(instance2.id)


# Has boto3 equivalent
@mock_ec2_deprecated
def test_get_instances_filtering_by_vpc_id():
    conn = boto.connect_vpc("the_key", "the_secret")
    vpc1 = conn.create_vpc("10.0.0.0/16")
    subnet1 = conn.create_subnet(vpc1.id, "10.0.0.0/27")
    reservation1 = conn.run_instances(EXAMPLE_AMI_ID, min_count=1, subnet_id=subnet1.id)
    instance1 = reservation1.instances[0]

    vpc2 = conn.create_vpc("10.1.0.0/16")
    subnet2 = conn.create_subnet(vpc2.id, "10.1.0.0/27")
    reservation2 = conn.run_instances(EXAMPLE_AMI_ID, min_count=1, subnet_id=subnet2.id)
    instance2 = reservation2.instances[0]

    reservations1 = conn.get_all_reservations(filters={"vpc-id": vpc1.id})
    reservations1.should.have.length_of(1)
    reservations1[0].instances.should.have.length_of(1)
    reservations1[0].instances[0].id.should.equal(instance1.id)
    reservations1[0].instances[0].vpc_id.should.equal(vpc1.id)
    reservations1[0].instances[0].subnet_id.should.equal(subnet1.id)

    reservations2 = conn.get_all_reservations(filters={"vpc-id": vpc2.id})
    reservations2.should.have.length_of(1)
    reservations2[0].instances.should.have.length_of(1)
    reservations2[0].instances[0].id.should.equal(instance2.id)
    reservations2[0].instances[0].vpc_id.should.equal(vpc2.id)
    reservations2[0].instances[0].subnet_id.should.equal(subnet2.id)


@mock_ec2
def test_get_instances_filtering_by_vpc_id_boto3():
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
    res1.should.have.length_of(1)
    res1[0]["Instances"].should.have.length_of(1)
    res1[0]["Instances"][0]["InstanceId"].should.equal(instance1.id)
    res1[0]["Instances"][0]["VpcId"].should.equal(vpc1.id)
    res1[0]["Instances"][0]["SubnetId"].should.equal(subnet1.id)

    res2 = client.describe_instances(Filters=[{"Name": "vpc-id", "Values": [vpc2.id]}])[
        "Reservations"
    ]
    res2.should.have.length_of(1)
    res2[0]["Instances"].should.have.length_of(1)
    res2[0]["Instances"][0]["InstanceId"].should.equal(instance2.id)
    res2[0]["Instances"][0]["VpcId"].should.equal(vpc2.id)
    res2[0]["Instances"][0]["SubnetId"].should.equal(subnet2.id)


# Has boto3 equivalent
@mock_ec2_deprecated
def test_get_instances_filtering_by_architecture():
    conn = boto.connect_ec2()
    conn.run_instances(EXAMPLE_AMI_ID, min_count=1)

    reservations = conn.get_all_reservations(filters={"architecture": "x86_64"})
    # get_all_reservations should return the instance
    reservations[0].instances.should.have.length_of(1)


@mock_ec2
def test_get_instances_filtering_by_architecture_boto3():
    ec2 = boto3.resource("ec2", region_name="us-west-1")
    client = boto3.client("ec2", region_name="us-west-1")
    ec2.create_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)

    reservations = client.describe_instances(
        Filters=[{"Name": "architecture", "Values": ["x86_64"]}]
    )["Reservations"]
    # get_all_reservations should return the instance
    reservations[0]["Instances"].should.have.length_of(1)


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

    [i["InstanceId"] for i in instances].should.contain(instance.id)


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
    reservations[0]["Instances"].should.have.length_of(1)


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
    reservations[0]["Instances"].should.have.length_of(1)


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
    reservations[0]["Instances"].should.have.length_of(1)


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
    reservations[0]["Instances"].should.have.length_of(1)


@mock_ec2
def test_get_instances_filtering_by_subnet_id():
    client = boto3.client("ec2", region_name="us-east-1")

    vpc_cidr = ipaddress.ip_network("192.168.42.0/24")
    subnet_cidr = ipaddress.ip_network("192.168.42.0/25")

    resp = client.create_vpc(CidrBlock=str(vpc_cidr),)
    vpc_id = resp["Vpc"]["VpcId"]

    resp = client.create_subnet(CidrBlock=str(subnet_cidr), VpcId=vpc_id)
    subnet_id = resp["Subnet"]["SubnetId"]

    client.run_instances(
        ImageId=EXAMPLE_AMI_ID, MaxCount=1, MinCount=1, SubnetId=subnet_id,
    )

    reservations = client.describe_instances(
        Filters=[{"Name": "subnet-id", "Values": [subnet_id]}]
    )["Reservations"]
    reservations.should.have.length_of(1)


# Has boto3 equivalent
@mock_ec2_deprecated
def test_get_instances_filtering_by_tag():
    conn = boto.connect_ec2()
    reservation = conn.run_instances(EXAMPLE_AMI_ID, min_count=3)
    instance1, instance2, instance3 = reservation.instances
    instance1.add_tag("tag1", "value1")
    instance1.add_tag("tag2", "value2")
    instance2.add_tag("tag1", "value1")
    instance2.add_tag("tag2", "wrong value")
    instance3.add_tag("tag2", "value2")

    reservations = conn.get_all_reservations(filters={"tag:tag0": "value0"})
    # get_all_reservations should return no instances
    reservations.should.have.length_of(0)

    reservations = conn.get_all_reservations(filters={"tag:tag1": "value1"})
    # get_all_reservations should return both instances with this tag value
    reservations.should.have.length_of(1)
    reservations[0].instances.should.have.length_of(2)
    reservations[0].instances[0].id.should.equal(instance1.id)
    reservations[0].instances[1].id.should.equal(instance2.id)

    reservations = conn.get_all_reservations(
        filters={"tag:tag1": "value1", "tag:tag2": "value2"}
    )
    # get_all_reservations should return the instance with both tag values
    reservations.should.have.length_of(1)
    reservations[0].instances.should.have.length_of(1)
    reservations[0].instances[0].id.should.equal(instance1.id)

    reservations = conn.get_all_reservations(
        filters={"tag:tag1": "value1", "tag:tag2": "value2"}
    )
    # get_all_reservations should return the instance with both tag values
    reservations.should.have.length_of(1)
    reservations[0].instances.should.have.length_of(1)
    reservations[0].instances[0].id.should.equal(instance1.id)

    reservations = conn.get_all_reservations(filters={"tag:tag2": ["value2", "bogus"]})
    # get_all_reservations should return both instances with one of the
    # acceptable tag values
    reservations.should.have.length_of(1)
    reservations[0].instances.should.have.length_of(2)
    reservations[0].instances[0].id.should.equal(instance1.id)
    reservations[0].instances[1].id.should.equal(instance3.id)


@mock_ec2
def test_get_instances_filtering_by_tag_boto3():
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
        Filters=[{"Name": "tag:tag0", "Values": ["value0"]}]
    )
    # describe_instances should return no instances
    res["Reservations"].should.have.length_of(0)

    res = client.describe_instances(
        Filters=[{"Name": f"tag:{tag1_name}", "Values": [tag1_val]}]
    )
    # describe_instances should return both instances with this tag value
    res["Reservations"].should.have.length_of(1)
    res["Reservations"][0]["Instances"].should.have.length_of(2)
    res["Reservations"][0]["Instances"][0]["InstanceId"].should.equal(instance1.id)
    res["Reservations"][0]["Instances"][1]["InstanceId"].should.equal(instance2.id)

    res = client.describe_instances(
        Filters=[
            {"Name": f"tag:{tag1_name}", "Values": [tag1_val]},
            {"Name": f"tag:{tag2_name}", "Values": [tag2_val]},
        ]
    )
    # describe_instances should return the instance with both tag values
    res["Reservations"].should.have.length_of(1)
    res["Reservations"][0]["Instances"].should.have.length_of(1)
    res["Reservations"][0]["Instances"][0]["InstanceId"].should.equal(instance1.id)

    res = client.describe_instances(
        Filters=[{"Name": f"tag:{tag2_name}", "Values": [tag2_val, "bogus"]}]
    )
    # describe_instances should return both instances with one of the
    # acceptable tag values
    res["Reservations"].should.have.length_of(1)
    res["Reservations"][0]["Instances"].should.have.length_of(2)
    res["Reservations"][0]["Instances"][0]["InstanceId"].should.equal(instance1.id)
    res["Reservations"][0]["Instances"][1]["InstanceId"].should.equal(instance3.id)


# Has boto3 equivalent
@mock_ec2_deprecated
def test_get_instances_filtering_by_tag_value():
    conn = boto.connect_ec2()
    reservation = conn.run_instances(EXAMPLE_AMI_ID, min_count=3)
    instance1, instance2, instance3 = reservation.instances
    instance1.add_tag("tag1", "value1")
    instance1.add_tag("tag2", "value2")
    instance2.add_tag("tag1", "value1")
    instance2.add_tag("tag2", "wrong value")
    instance3.add_tag("tag2", "value2")

    reservations = conn.get_all_reservations(filters={"tag-value": "value0"})
    # get_all_reservations should return no instances
    reservations.should.have.length_of(0)

    reservations = conn.get_all_reservations(filters={"tag-value": "value1"})
    # get_all_reservations should return both instances with this tag value
    reservations.should.have.length_of(1)
    reservations[0].instances.should.have.length_of(2)
    reservations[0].instances[0].id.should.equal(instance1.id)
    reservations[0].instances[1].id.should.equal(instance2.id)

    reservations = conn.get_all_reservations(
        filters={"tag-value": ["value2", "value1"]}
    )
    # get_all_reservations should return both instances with one of the
    # acceptable tag values
    reservations.should.have.length_of(1)
    reservations[0].instances.should.have.length_of(3)
    reservations[0].instances[0].id.should.equal(instance1.id)
    reservations[0].instances[1].id.should.equal(instance2.id)
    reservations[0].instances[2].id.should.equal(instance3.id)

    reservations = conn.get_all_reservations(filters={"tag-value": ["value2", "bogus"]})
    # get_all_reservations should return both instances with one of the
    # acceptable tag values
    reservations.should.have.length_of(1)
    reservations[0].instances.should.have.length_of(2)
    reservations[0].instances[0].id.should.equal(instance1.id)
    reservations[0].instances[1].id.should.equal(instance3.id)


@mock_ec2
def test_get_instances_filtering_by_tag_value_boto3():
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
    res["Reservations"].should.have.length_of(0)

    res = client.describe_instances(
        Filters=[{"Name": "tag-value", "Values": [tag1_val]}]
    )
    # describe_instances should return both instances with this tag value
    res["Reservations"].should.have.length_of(1)
    res["Reservations"][0]["Instances"].should.have.length_of(2)
    res["Reservations"][0]["Instances"][0]["InstanceId"].should.equal(instance1.id)
    res["Reservations"][0]["Instances"][1]["InstanceId"].should.equal(instance2.id)

    res = client.describe_instances(
        Filters=[{"Name": "tag-value", "Values": [tag2_val, tag1_val]}]
    )
    # describe_instances should return both instances with one of the
    # acceptable tag values
    res["Reservations"].should.have.length_of(1)
    res["Reservations"][0]["Instances"].should.have.length_of(3)
    res["Reservations"][0]["Instances"][0]["InstanceId"].should.equal(instance1.id)
    res["Reservations"][0]["Instances"][1]["InstanceId"].should.equal(instance2.id)
    res["Reservations"][0]["Instances"][2]["InstanceId"].should.equal(instance3.id)

    res = client.describe_instances(
        Filters=[{"Name": "tag-value", "Values": [tag2_val, "bogus"]}]
    )
    # describe_instances should return both instances with one of the
    # acceptable tag values
    res["Reservations"].should.have.length_of(1)
    res["Reservations"][0]["Instances"].should.have.length_of(2)
    res["Reservations"][0]["Instances"][0]["InstanceId"].should.equal(instance1.id)
    res["Reservations"][0]["Instances"][1]["InstanceId"].should.equal(instance3.id)


# Has boto3 equivalent
@mock_ec2_deprecated
def test_get_instances_filtering_by_tag_name():
    conn = boto.connect_ec2()
    reservation = conn.run_instances(EXAMPLE_AMI_ID, min_count=3)
    instance1, instance2, instance3 = reservation.instances
    instance1.add_tag("tag1")
    instance1.add_tag("tag2")
    instance2.add_tag("tag1")
    instance2.add_tag("tag2X")
    instance3.add_tag("tag3")

    reservations = conn.get_all_reservations(filters={"tag-key": "tagX"})
    # get_all_reservations should return no instances
    reservations.should.have.length_of(0)

    reservations = conn.get_all_reservations(filters={"tag-key": "tag1"})
    # get_all_reservations should return both instances with this tag value
    reservations.should.have.length_of(1)
    reservations[0].instances.should.have.length_of(2)
    reservations[0].instances[0].id.should.equal(instance1.id)
    reservations[0].instances[1].id.should.equal(instance2.id)

    reservations = conn.get_all_reservations(filters={"tag-key": ["tag1", "tag3"]})
    # get_all_reservations should return both instances with one of the
    # acceptable tag values
    reservations.should.have.length_of(1)
    reservations[0].instances.should.have.length_of(3)
    reservations[0].instances[0].id.should.equal(instance1.id)
    reservations[0].instances[1].id.should.equal(instance2.id)
    reservations[0].instances[2].id.should.equal(instance3.id)


@mock_ec2
def test_get_instances_filtering_by_tag_name_boto3():
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
    res["Reservations"].should.have.length_of(0)

    res = client.describe_instances(Filters=[{"Name": "tag-key", "Values": [tag1]}])
    # describe_instances should return both instances with this tag value
    res["Reservations"].should.have.length_of(1)
    res["Reservations"][0]["Instances"].should.have.length_of(2)
    res["Reservations"][0]["Instances"][0]["InstanceId"].should.equal(instance1.id)
    res["Reservations"][0]["Instances"][1]["InstanceId"].should.equal(instance2.id)

    res = client.describe_instances(
        Filters=[{"Name": "tag-key", "Values": [tag1, tag3]}]
    )
    # describe_instances should return both instances with one of the
    # acceptable tag values
    res["Reservations"].should.have.length_of(1)
    res["Reservations"][0]["Instances"].should.have.length_of(3)
    res["Reservations"][0]["Instances"][0]["InstanceId"].should.equal(instance1.id)
    res["Reservations"][0]["Instances"][1]["InstanceId"].should.equal(instance2.id)
    res["Reservations"][0]["Instances"][2]["InstanceId"].should.equal(instance3.id)


# Has boto3 equivalent
@mock_ec2_deprecated
def test_instance_start_and_stop():
    conn = boto.connect_ec2("the_key", "the_secret")
    reservation = conn.run_instances(EXAMPLE_AMI_ID, min_count=2)
    instances = reservation.instances
    instances.should.have.length_of(2)

    instance_ids = [instance.id for instance in instances]

    with pytest.raises(EC2ResponseError) as ex:
        stopped_instances = conn.stop_instances(instance_ids, dry_run=True)
    ex.value.error_code.should.equal("DryRunOperation")
    ex.value.status.should.equal(412)
    ex.value.message.should.equal(
        "An error occurred (DryRunOperation) when calling the StopInstance operation: Request would have succeeded, but DryRun flag is set"
    )

    stopped_instances = conn.stop_instances(instance_ids)

    for instance in stopped_instances:
        instance.state.should.equal("stopping")

    with pytest.raises(EC2ResponseError) as ex:
        started_instances = conn.start_instances([instances[0].id], dry_run=True)
    ex.value.error_code.should.equal("DryRunOperation")
    ex.value.status.should.equal(412)
    ex.value.message.should.equal(
        "An error occurred (DryRunOperation) when calling the StartInstance operation: Request would have succeeded, but DryRun flag is set"
    )

    started_instances = conn.start_instances([instances[0].id])
    started_instances[0].state.should.equal("pending")


@mock_ec2
def test_instance_start_and_stop_boto3():
    client = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    reservation = ec2.create_instances(ImageId=EXAMPLE_AMI_ID, MinCount=2, MaxCount=2)
    instance1, instance2 = reservation

    instance_ids = [instance1.id, instance2.id]

    with pytest.raises(ClientError) as ex:
        client.stop_instances(InstanceIds=instance_ids, DryRun=True)
    ex.value.response["Error"]["Code"].should.equal("DryRunOperation")
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(412)
    ex.value.response["Error"]["Message"].should.equal(
        "An error occurred (DryRunOperation) when calling the StopInstance operation: Request would have succeeded, but DryRun flag is set"
    )

    stopped_instances = client.stop_instances(InstanceIds=instance_ids)[
        "StoppingInstances"
    ]

    for instance in stopped_instances:
        instance["PreviousState"].should.equal({"Code": 16, "Name": "running"})
        instance["CurrentState"].should.equal({"Code": 64, "Name": "stopping"})

    instance1.reload()
    instance1.state.should.equal({"Code": 80, "Name": "stopped"})

    with pytest.raises(ClientError) as ex:
        client.start_instances(InstanceIds=[instance1.id], DryRun=True)
    ex.value.response["Error"]["Code"].should.equal("DryRunOperation")
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(412)
    ex.value.response["Error"]["Message"].should.equal(
        "An error occurred (DryRunOperation) when calling the StartInstance operation: Request would have succeeded, but DryRun flag is set"
    )

    instance1.reload()
    # The DryRun-operation did not change anything
    instance1.state.should.equal({"Code": 80, "Name": "stopped"})

    started_instances = client.start_instances(InstanceIds=[instance1.id])[
        "StartingInstances"
    ]
    started_instances[0]["CurrentState"].should.equal({"Code": 0, "Name": "pending"})
    # TODO: The PreviousState is hardcoded to 'running' atm
    # started_instances[0]["PreviousState"].should.equal({'Code': 80, 'Name': 'stopped'})


# Has boto3 equivalent
@mock_ec2_deprecated
def test_instance_reboot():
    conn = boto.connect_ec2("the_key", "the_secret")
    reservation = conn.run_instances(EXAMPLE_AMI_ID)
    instance = reservation.instances[0]

    with pytest.raises(EC2ResponseError) as ex:
        instance.reboot(dry_run=True)
    ex.value.error_code.should.equal("DryRunOperation")
    ex.value.status.should.equal(412)
    ex.value.message.should.equal(
        "An error occurred (DryRunOperation) when calling the RebootInstance operation: Request would have succeeded, but DryRun flag is set"
    )

    instance.reboot()
    instance.state.should.equal("pending")


@mock_ec2
def test_instance_reboot_boto3():
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    response = ec2.create_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)
    instance = response[0]
    instance.state.should.equal({"Code": 0, "Name": "pending"})
    instance.reload()
    instance.state.should.equal({"Code": 16, "Name": "running"})

    with pytest.raises(ClientError) as ex:
        instance.reboot(DryRun=True)
    ex.value.response["Error"]["Code"].should.equal("DryRunOperation")
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(412)
    ex.value.response["Error"]["Message"].should.equal(
        "An error occurred (DryRunOperation) when calling the RebootInstance operation: Request would have succeeded, but DryRun flag is set"
    )

    instance.state.should.equal({"Code": 16, "Name": "running"})

    instance.reboot()
    instance.state.should.equal({"Code": 16, "Name": "running"})


# Has boto3 equivalent
@mock_ec2_deprecated
def test_instance_attribute_instance_type():
    conn = boto.connect_ec2("the_key", "the_secret")
    reservation = conn.run_instances(EXAMPLE_AMI_ID)
    instance = reservation.instances[0]

    with pytest.raises(EC2ResponseError) as ex:
        instance.modify_attribute("instanceType", "m1.small", dry_run=True)
    ex.value.error_code.should.equal("DryRunOperation")
    ex.value.status.should.equal(412)
    ex.value.message.should.equal(
        "An error occurred (DryRunOperation) when calling the ModifyInstanceType operation: Request would have succeeded, but DryRun flag is set"
    )

    instance.modify_attribute("instanceType", "m1.small")

    instance_attribute = instance.get_attribute("instanceType")
    instance_attribute.should.be.a(InstanceAttribute)
    instance_attribute.get("instanceType").should.equal("m1.small")


@mock_ec2
def test_instance_attribute_instance_type_boto3():
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    response = ec2.create_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)
    instance = response[0]
    instance.instance_type.should.equal("m1.small")

    with pytest.raises(ClientError) as ex:
        instance.modify_attribute(InstanceType={"Value": "m1.medium"}, DryRun=True)
    ex.value.response["Error"]["Code"].should.equal("DryRunOperation")
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(412)
    ex.value.response["Error"]["Message"].should.equal(
        "An error occurred (DryRunOperation) when calling the ModifyInstanceType operation: Request would have succeeded, but DryRun flag is set"
    )

    instance.modify_attribute(InstanceType={"Value": "m1.medium"})

    instance.instance_type.should.equal("m1.medium")
    instance.describe_attribute(Attribute="instanceType")["InstanceType"].should.equal(
        {"Value": "m1.medium"}
    )


# Has boto3 equivalent
@mock_ec2_deprecated
def test_modify_instance_attribute_security_groups():
    conn = boto.connect_ec2("the_key", "the_secret")
    reservation = conn.run_instances(EXAMPLE_AMI_ID)
    instance = reservation.instances[0]

    sg_id = conn.create_security_group(
        "test security group", "this is a test security group"
    ).id
    sg_id2 = conn.create_security_group(
        "test security group 2", "this is a test security group 2"
    ).id

    with pytest.raises(EC2ResponseError) as ex:
        instance.modify_attribute("groupSet", [sg_id, sg_id2], dry_run=True)
    ex.value.error_code.should.equal("DryRunOperation")
    ex.value.status.should.equal(412)
    ex.value.message.should.equal(
        "An error occurred (DryRunOperation) when calling the ModifyInstanceSecurityGroups operation: Request would have succeeded, but DryRun flag is set"
    )

    instance.modify_attribute("groupSet", [sg_id, sg_id2])

    instance_attribute = instance.get_attribute("groupSet")
    instance_attribute.should.be.a(InstanceAttribute)
    group_list = instance_attribute.get("groupSet")
    any(g.id == sg_id for g in group_list).should.be.ok
    any(g.id == sg_id2 for g in group_list).should.be.ok


@mock_ec2
def test_modify_instance_attribute_security_groups_boto3():
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    response = ec2.create_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)
    instance = response[0]
    old_groups = instance.describe_attribute(Attribute="groupSet")["Groups"]
    old_groups.should.equal([])

    sg_id = ec2.create_security_group(
        GroupName=str(uuid4()), Description="this is a test security group"
    ).id
    sg_id2 = ec2.create_security_group(
        GroupName=str(uuid4()), Description="this is a test security group 2"
    ).id

    with pytest.raises(ClientError) as ex:
        instance.modify_attribute(Groups=[sg_id, sg_id2], DryRun=True)
    ex.value.response["Error"]["Code"].should.equal("DryRunOperation")
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(412)
    ex.value.response["Error"]["Message"].should.equal(
        "An error occurred (DryRunOperation) when calling the ModifyInstanceSecurityGroups operation: Request would have succeeded, but DryRun flag is set"
    )

    instance.modify_attribute(Groups=[sg_id, sg_id2])

    new_groups = instance.describe_attribute(Attribute="groupSet")["Groups"]
    new_groups.should.have.length_of(2)
    new_groups.should.contain({"GroupId": sg_id})
    new_groups.should.contain({"GroupId": sg_id2})


# Has boto3 equivalent
@mock_ec2_deprecated
def test_instance_attribute_user_data():
    conn = boto.connect_ec2("the_key", "the_secret")
    reservation = conn.run_instances(EXAMPLE_AMI_ID)
    instance = reservation.instances[0]

    with pytest.raises(EC2ResponseError) as ex:
        instance.modify_attribute("userData", "this is my user data", dry_run=True)
    ex.value.error_code.should.equal("DryRunOperation")
    ex.value.status.should.equal(412)
    ex.value.message.should.equal(
        "An error occurred (DryRunOperation) when calling the ModifyUserData operation: Request would have succeeded, but DryRun flag is set"
    )

    instance.modify_attribute("userData", "this is my user data")

    instance_attribute = instance.get_attribute("userData")
    instance_attribute.should.be.a(InstanceAttribute)
    instance_attribute.get("userData").should.equal("this is my user data")


@mock_ec2
def test_instance_attribute_user_data_boto3():
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    res = ec2.create_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)
    instance = res[0]

    with pytest.raises(ClientError) as ex:
        instance.modify_attribute(
            UserData={"Value": "this is my user data"}, DryRun=True
        )
    ex.value.response["Error"]["Code"].should.equal("DryRunOperation")
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(412)
    ex.value.response["Error"]["Message"].should.equal(
        "An error occurred (DryRunOperation) when calling the ModifyUserData operation: Request would have succeeded, but DryRun flag is set"
    )

    instance.modify_attribute(UserData={"Value": "this is my user data"})

    attribute = instance.describe_attribute(Attribute="userData")["UserData"]
    retrieved_user_data = attribute["Value"].encode("utf-8")
    decode_method(retrieved_user_data).should.equal(b"this is my user data")


# Has boto3 equivalent
@mock_ec2_deprecated
def test_instance_attribute_source_dest_check():
    conn = boto.connect_ec2("the_key", "the_secret")
    reservation = conn.run_instances(EXAMPLE_AMI_ID)
    instance = reservation.instances[0]

    # Default value is true
    instance.sourceDestCheck.should.equal("true")

    instance_attribute = instance.get_attribute("sourceDestCheck")
    instance_attribute.should.be.a(InstanceAttribute)
    instance_attribute.get("sourceDestCheck").should.equal(True)

    # Set to false (note: Boto converts bool to string, eg 'false')

    with pytest.raises(EC2ResponseError) as ex:
        instance.modify_attribute("sourceDestCheck", False, dry_run=True)
    ex.value.error_code.should.equal("DryRunOperation")
    ex.value.status.should.equal(412)
    ex.value.message.should.equal(
        "An error occurred (DryRunOperation) when calling the ModifySourceDestCheck operation: Request would have succeeded, but DryRun flag is set"
    )

    instance.modify_attribute("sourceDestCheck", False)

    instance.update()
    instance.sourceDestCheck.should.equal("false")

    instance_attribute = instance.get_attribute("sourceDestCheck")
    instance_attribute.should.be.a(InstanceAttribute)
    instance_attribute.get("sourceDestCheck").should.equal(False)

    # Set back to true
    instance.modify_attribute("sourceDestCheck", True)

    instance.update()
    instance.sourceDestCheck.should.equal("true")

    instance_attribute = instance.get_attribute("sourceDestCheck")
    instance_attribute.should.be.a(InstanceAttribute)
    instance_attribute.get("sourceDestCheck").should.equal(True)


@mock_ec2
def test_instance_attribute_source_dest_check_boto3():
    ec2 = boto3.resource("ec2", region_name="us-west-1")
    instance = ec2.create_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)[0]

    instance_attribute = instance.describe_attribute(Attribute="sourceDestCheck")
    instance_attribute.get("SourceDestCheck").should.equal({"Value": True})

    # Set to false (note: Boto converts bool to string, eg 'false')

    with pytest.raises(ClientError) as ex:
        instance.modify_attribute(SourceDestCheck={"Value": False}, DryRun=True)
    ex.value.response["Error"]["Code"].should.equal("DryRunOperation")
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(412)
    ex.value.response["Error"]["Message"].should.equal(
        "An error occurred (DryRunOperation) when calling the ModifySourceDestCheck operation: Request would have succeeded, but DryRun flag is set"
    )

    instance.modify_attribute(SourceDestCheck={"Value": False})

    instance_attribute = instance.describe_attribute(Attribute="sourceDestCheck")
    instance_attribute.get("SourceDestCheck").should.equal({"Value": False})

    # Set back to true
    instance.modify_attribute(SourceDestCheck={"Value": True})

    instance_attribute = instance.describe_attribute(Attribute="sourceDestCheck")
    instance_attribute.get("SourceDestCheck").should.equal({"Value": True})


# Has boto3 equivalent
@mock_ec2_deprecated
def test_user_data_with_run_instance():
    user_data = b"some user data"
    conn = boto.connect_ec2("the_key", "the_secret")
    reservation = conn.run_instances(EXAMPLE_AMI_ID, user_data=user_data)
    instance = reservation.instances[0]

    instance_attribute = instance.get_attribute("userData")
    instance_attribute.should.be.a(InstanceAttribute)
    retrieved_user_data = instance_attribute.get("userData").encode("utf-8")
    decoded_user_data = decode_method(retrieved_user_data)
    decoded_user_data.should.equal(b"some user data")


@mock_ec2
def test_user_data_with_run_instance_boto3():
    user_data = b"some user data"
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    instance = ec2.create_instances(
        ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1, UserData=user_data
    )[0]

    attribute = instance.describe_attribute(Attribute="userData")["UserData"]
    retrieved_user_data = attribute["Value"].encode("utf-8")
    decoded_user_data = decode_method(retrieved_user_data)
    decoded_user_data.should.equal(b"some user data")


# Has boto3 equivalent
@mock_ec2_deprecated
def test_run_instance_with_security_group_name():
    conn = boto.connect_ec2("the_key", "the_secret")

    with pytest.raises(EC2ResponseError) as ex:
        group = conn.create_security_group("group1", "some description", dry_run=True)
    ex.value.error_code.should.equal("DryRunOperation")
    ex.value.status.should.equal(412)
    ex.value.message.should.equal(
        "An error occurred (DryRunOperation) when calling the CreateSecurityGroup operation: Request would have succeeded, but DryRun flag is set"
    )

    group = conn.create_security_group("group1", "some description")

    reservation = conn.run_instances(EXAMPLE_AMI_ID, security_groups=["group1"])
    instance = reservation.instances[0]

    instance.groups[0].id.should.equal(group.id)
    instance.groups[0].name.should.equal("group1")


@mock_ec2
def test_run_instance_with_security_group_name_boto3():
    ec2 = boto3.resource("ec2", region_name="us-east-1")

    sec_group_name = str(uuid4())[0:6]

    with pytest.raises(ClientError) as ex:
        ec2.create_security_group(
            GroupName=sec_group_name, Description="d", DryRun=True
        )
    ex.value.response["Error"]["Code"].should.equal("DryRunOperation")
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(412)
    ex.value.response["Error"]["Message"].should.equal(
        "An error occurred (DryRunOperation) when calling the CreateSecurityGroup operation: Request would have succeeded, but DryRun flag is set"
    )

    group = ec2.create_security_group(
        GroupName=sec_group_name, Description="some description"
    )

    res = ec2.create_instances(
        ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1, SecurityGroups=[sec_group_name]
    )
    instance = res[0]

    instance.security_groups.should.equal(
        [{"GroupName": sec_group_name, "GroupId": group.id}]
    )


# Has boto3 equivalent
@mock_ec2_deprecated
def test_run_instance_with_security_group_id():
    conn = boto.connect_ec2("the_key", "the_secret")
    group = conn.create_security_group("group1", "some description")
    reservation = conn.run_instances(EXAMPLE_AMI_ID, security_group_ids=[group.id])
    instance = reservation.instances[0]

    instance.groups[0].id.should.equal(group.id)
    instance.groups[0].name.should.equal("group1")


@mock_ec2
def test_run_instance_with_security_group_id_boto3():
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    sec_group_name = str(uuid4())
    group = ec2.create_security_group(
        GroupName=sec_group_name, Description="some description"
    )
    instance = ec2.create_instances(
        ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1, SecurityGroupIds=[group.id]
    )[0]

    instance.security_groups.should.equal(
        [{"GroupName": sec_group_name, "GroupId": group.id}]
    )


# Has boto3 equivalent
@mock_ec2_deprecated
def test_run_instance_with_instance_type():
    conn = boto.connect_ec2("the_key", "the_secret")
    reservation = conn.run_instances(EXAMPLE_AMI_ID, instance_type="t1.micro")
    instance = reservation.instances[0]

    instance.instance_type.should.equal("t1.micro")


@mock_ec2
def test_run_instance_with_instance_type_boto3():
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    instance = ec2.create_instances(
        ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1, InstanceType="t1.micro"
    )[0]

    instance.instance_type.should.equal("t1.micro")


# Has boto3 equivalent
@mock_ec2_deprecated
def test_run_instance_with_default_placement():
    conn = boto.ec2.connect_to_region("us-east-1")
    reservation = conn.run_instances(EXAMPLE_AMI_ID)
    instance = reservation.instances[0]

    instance.placement.should.equal("us-east-1a")


@mock_ec2
def test_run_instance_with_default_placement_boto3():
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    instance = ec2.create_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)[0]

    instance.placement.should.have.key("AvailabilityZone").equal("us-east-1a")


# Has boto3 equivalent
@mock_ec2_deprecated
def test_run_instance_with_placement():
    conn = boto.connect_ec2("the_key", "the_secret")
    reservation = conn.run_instances(EXAMPLE_AMI_ID, placement="us-east-1b")
    instance = reservation.instances[0]

    instance.placement.should.equal("us-east-1b")


@mock_ec2
def test_run_instance_with_placement_boto3():
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    instance = ec2.create_instances(
        ImageId=EXAMPLE_AMI_ID,
        MinCount=1,
        MaxCount=1,
        Placement={"AvailabilityZone": "us-east-1b"},
    )[0]

    instance.placement.should.have.key("AvailabilityZone").equal("us-east-1b")


@mock_ec2
def test_run_instance_with_subnet_boto3():
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
        instance["SubnetId"].should.equal(subnet_id)

        priv_ipv4 = ipaddress.ip_address(str(instance["PrivateIpAddress"]))
        subnet_cidr.should.contain(priv_ipv4)


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
    instance["SubnetId"].should.equal(subnet_id)
    instance["PrivateIpAddress"].should.equal("192.168.42.5")


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
    instance.should.contain("PublicDnsName")
    instance.should.contain("PublicIpAddress")
    len(instance["PublicDnsName"]).should.be.greater_than(0)
    len(instance["PublicIpAddress"]).should.be.greater_than(0)


# Has boto3 equivalent
@mock_ec2_deprecated
def test_run_instance_with_nic_autocreated():
    conn = boto.connect_vpc("the_key", "the_secret")
    vpc = conn.create_vpc("10.0.0.0/16")
    subnet = conn.create_subnet(vpc.id, "10.0.0.0/18")
    security_group1 = conn.create_security_group(
        "test security group #1", "this is a test security group"
    )
    security_group2 = conn.create_security_group(
        "test security group #2", "this is a test security group"
    )
    private_ip = "10.0.0.1"

    reservation = conn.run_instances(
        EXAMPLE_AMI_ID,
        subnet_id=subnet.id,
        security_groups=[security_group1.name],
        security_group_ids=[security_group2.id],
        private_ip_address=private_ip,
    )
    instance = reservation.instances[0]

    all_enis = conn.get_all_network_interfaces()
    all_enis.should.have.length_of(1)
    eni = all_enis[0]

    instance.interfaces.should.have.length_of(1)
    instance.interfaces[0].id.should.equal(eni.id)

    instance.subnet_id.should.equal(subnet.id)
    instance.groups.should.have.length_of(2)
    set([group.id for group in instance.groups]).should.equal(
        set([security_group1.id, security_group2.id])
    )

    eni.subnet_id.should.equal(subnet.id)
    eni.groups.should.have.length_of(2)
    set([group.id for group in eni.groups]).should.equal(
        set([security_group1.id, security_group2.id])
    )
    eni.private_ip_addresses.should.have.length_of(1)
    eni.private_ip_addresses[0].private_ip_address.should.equal(private_ip)


@mock_ec2
def test_run_instance_with_nic_autocreated_boto3():
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
    instance_eni.should.have.length_of(1)

    nii = instance_eni[0]["NetworkInterfaceId"]

    my_enis = client.describe_network_interfaces(NetworkInterfaceIds=[nii])[
        "NetworkInterfaces"
    ]
    my_enis.should.have.length_of(1)
    eni = my_enis[0]

    instance.subnet_id.should.equal(subnet.id)
    instance.security_groups.should.have.length_of(2)
    set([group["GroupId"] for group in instance.security_groups]).should.equal(
        set([security_group1.id, security_group2.id])
    )

    eni["SubnetId"].should.equal(subnet.id)
    eni["Groups"].should.have.length_of(2)
    set([group["GroupId"] for group in eni["Groups"]]).should.equal(
        set([security_group1.id, security_group2.id])
    )
    eni["PrivateIpAddresses"].should.have.length_of(1)
    eni["PrivateIpAddresses"][0]["PrivateIpAddress"].should.equal(private_ip)


# Has boto3 equivalent
@mock_ec2_deprecated
def test_run_instance_with_nic_preexisting():
    conn = boto.connect_vpc("the_key", "the_secret")
    vpc = conn.create_vpc("10.0.0.0/16")
    subnet = conn.create_subnet(vpc.id, "10.0.0.0/18")
    security_group1 = conn.create_security_group(
        "test security group #1", "this is a test security group"
    )
    security_group2 = conn.create_security_group(
        "test security group #2", "this is a test security group"
    )
    private_ip = "54.0.0.1"
    eni = conn.create_network_interface(
        subnet.id, private_ip, groups=[security_group1.id]
    )

    # Boto requires NetworkInterfaceCollection of NetworkInterfaceSpecifications...
    #   annoying, but generates the desired querystring.
    from boto.ec2.networkinterface import (
        NetworkInterfaceSpecification,
        NetworkInterfaceCollection,
    )

    interface = NetworkInterfaceSpecification(
        network_interface_id=eni.id, device_index=0
    )
    interfaces = NetworkInterfaceCollection(interface)
    # end Boto objects

    reservation = conn.run_instances(
        EXAMPLE_AMI_ID,
        network_interfaces=interfaces,
        security_group_ids=[security_group2.id],
    )
    instance = reservation.instances[0]

    instance.subnet_id.should.equal(subnet.id)

    all_enis = conn.get_all_network_interfaces()
    all_enis.should.have.length_of(1)

    instance.interfaces.should.have.length_of(1)
    instance_eni = instance.interfaces[0]
    instance_eni.id.should.equal(eni.id)

    instance_eni.subnet_id.should.equal(subnet.id)
    instance_eni.groups.should.have.length_of(2)
    set([group.id for group in instance_eni.groups]).should.equal(
        set([security_group1.id, security_group2.id])
    )
    instance_eni.private_ip_addresses.should.have.length_of(1)
    instance_eni.private_ip_addresses[0].private_ip_address.should.equal(private_ip)


@mock_ec2
def test_run_instance_with_nic_preexisting_boto3():
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
        NetworkInterfaces=[{"DeviceIndex": 0, "NetworkInterfaceId": eni.id,}],
        SubnetId=subnet.id,
        SecurityGroupIds=[security_group2.group_id],
    )[0]

    instance.subnet_id.should.equal(subnet.id)

    nii = instance.network_interfaces_attribute[0]["NetworkInterfaceId"]

    all_enis = client.describe_network_interfaces(NetworkInterfaceIds=[nii])[
        "NetworkInterfaces"
    ]
    all_enis.should.have.length_of(1)

    instance_enis = instance.network_interfaces_attribute
    instance_enis.should.have.length_of(1)
    instance_eni = instance_enis[0]
    instance_eni["NetworkInterfaceId"].should.equal(eni.id)

    instance_eni["SubnetId"].should.equal(subnet.id)
    instance_eni["Groups"].should.have.length_of(2)
    set([group["GroupId"] for group in instance_eni["Groups"]]).should.equal(
        set([security_group1.id, security_group2.id])
    )
    instance_eni["PrivateIpAddresses"].should.have.length_of(1)
    instance_eni["PrivateIpAddresses"][0]["PrivateIpAddress"].should.equal(private_ip)


# Has boto3 equivalent
@requires_boto_gte("2.32.0")
@mock_ec2_deprecated
def test_instance_with_nic_attach_detach():
    conn = boto.connect_vpc("the_key", "the_secret")
    vpc = conn.create_vpc("10.0.0.0/16")
    subnet = conn.create_subnet(vpc.id, "10.0.0.0/18")

    security_group1 = conn.create_security_group(
        "test security group #1", "this is a test security group"
    )
    security_group2 = conn.create_security_group(
        "test security group #2", "this is a test security group"
    )

    reservation = conn.run_instances(
        EXAMPLE_AMI_ID, security_group_ids=[security_group1.id]
    )
    instance = reservation.instances[0]

    eni = conn.create_network_interface(subnet.id, groups=[security_group2.id])

    # Check initial instance and ENI data
    instance.interfaces.should.have.length_of(1)

    eni.groups.should.have.length_of(1)
    set([group.id for group in eni.groups]).should.equal(set([security_group2.id]))

    # Attach
    with pytest.raises(EC2ResponseError) as ex:
        conn.attach_network_interface(eni.id, instance.id, device_index=1, dry_run=True)
    ex.value.error_code.should.equal("DryRunOperation")
    ex.value.status.should.equal(412)
    ex.value.message.should.equal(
        "An error occurred (DryRunOperation) when calling the AttachNetworkInterface operation: Request would have succeeded, but DryRun flag is set"
    )

    conn.attach_network_interface(eni.id, instance.id, device_index=1)

    # Check attached instance and ENI data
    instance.update()
    instance.interfaces.should.have.length_of(2)
    instance_eni = instance.interfaces[1]
    instance_eni.id.should.equal(eni.id)
    instance_eni.groups.should.have.length_of(2)
    set([group.id for group in instance_eni.groups]).should.equal(
        set([security_group1.id, security_group2.id])
    )

    eni = conn.get_all_network_interfaces(filters={"network-interface-id": eni.id})[0]
    eni.groups.should.have.length_of(2)
    set([group.id for group in eni.groups]).should.equal(
        set([security_group1.id, security_group2.id])
    )

    # Detach
    with pytest.raises(EC2ResponseError) as ex:
        conn.detach_network_interface(instance_eni.attachment.id, dry_run=True)
    ex.value.error_code.should.equal("DryRunOperation")
    ex.value.status.should.equal(412)
    ex.value.message.should.equal(
        "An error occurred (DryRunOperation) when calling the DetachNetworkInterface operation: Request would have succeeded, but DryRun flag is set"
    )

    conn.detach_network_interface(instance_eni.attachment.id)

    # Check detached instance and ENI data
    instance.update()
    instance.interfaces.should.have.length_of(1)

    eni = conn.get_all_network_interfaces(filters={"network-interface-id": eni.id})[0]
    eni.groups.should.have.length_of(1)
    set([group.id for group in eni.groups]).should.equal(set([security_group2.id]))

    # Detach with invalid attachment ID
    with pytest.raises(EC2ResponseError) as cm:
        conn.detach_network_interface("eni-attach-1234abcd")
    cm.value.code.should.equal("InvalidAttachmentID.NotFound")
    cm.value.status.should.equal(400)
    cm.value.request_id.should_not.be.none


@mock_ec2
def test_instance_with_nic_attach_detach_boto3():
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
    instance.network_interfaces_attribute.should.have.length_of(1)

    eni.groups.should.have.length_of(1)
    set([group["GroupId"] for group in eni.groups]).should.equal(
        set([security_group2.id])
    )

    # Attach
    with pytest.raises(ClientError) as ex:
        client.attach_network_interface(
            NetworkInterfaceId=eni_id,
            InstanceId=instance.id,
            DeviceIndex=1,
            DryRun=True,
        )
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(412)
    ex.value.response["Error"]["Code"].should.equal("DryRunOperation")
    ex.value.response["Error"]["Message"].should.equal(
        "An error occurred (DryRunOperation) when calling the AttachNetworkInterface operation: Request would have succeeded, but DryRun flag is set"
    )

    client.attach_network_interface(
        NetworkInterfaceId=eni_id, InstanceId=instance.id, DeviceIndex=1
    )

    # Check attached instance and ENI data
    instance.reload()
    instance.network_interfaces_attribute.should.have.length_of(2)
    instance_eni = instance.network_interfaces_attribute[1]
    instance_eni["NetworkInterfaceId"].should.equal(eni_id)
    instance_eni["Groups"].should.have.length_of(2)
    set([group["GroupId"] for group in instance_eni["Groups"]]).should.equal(
        set([security_group1.id, security_group2.id])
    )

    eni = client.describe_network_interfaces(
        Filters=[{"Name": "network-interface-id", "Values": [eni_id]}]
    )["NetworkInterfaces"][0]
    eni["Groups"].should.have.length_of(2)
    set([group["GroupId"] for group in eni["Groups"]]).should.equal(
        set([security_group1.id, security_group2.id])
    )

    # Detach
    with pytest.raises(ClientError) as ex:
        client.detach_network_interface(
            AttachmentId=instance_eni["Attachment"]["AttachmentId"], DryRun=True
        )
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(412)
    ex.value.response["Error"]["Code"].should.equal("DryRunOperation")
    ex.value.response["Error"]["Message"].should.equal(
        "An error occurred (DryRunOperation) when calling the DetachNetworkInterface operation: Request would have succeeded, but DryRun flag is set"
    )

    client.detach_network_interface(
        AttachmentId=instance_eni["Attachment"]["AttachmentId"]
    )

    # Check detached instance and ENI data
    instance.reload()
    instance.network_interfaces_attribute.should.have.length_of(1)

    eni = client.describe_network_interfaces(
        Filters=[{"Name": "network-interface-id", "Values": [eni_id]}]
    )["NetworkInterfaces"][0]
    eni["Groups"].should.have.length_of(1)
    set([group["GroupId"] for group in eni["Groups"]]).should.equal(
        set([security_group2.id])
    )

    # Detach with invalid attachment ID
    with pytest.raises(ClientError) as ex:
        client.detach_network_interface(AttachmentId="eni-attach-1234abcd")
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["ResponseMetadata"].should.have.key("RequestId")
    ex.value.response["Error"]["Code"].should.equal("InvalidAttachmentID.NotFound")


# Has boto3 equivalent
@mock_ec2_deprecated
def test_ec2_classic_has_public_ip_address():
    conn = boto.connect_ec2("the_key", "the_secret")
    reservation = conn.run_instances(EXAMPLE_AMI_ID, key_name="keypair_name")
    instance = reservation.instances[0]
    instance.ip_address.should_not.equal(None)
    instance.public_dns_name.should.contain(instance.ip_address.replace(".", "-"))
    instance.private_ip_address.should_not.equal(None)
    instance.private_dns_name.should.contain(
        instance.private_ip_address.replace(".", "-")
    )


@mock_ec2
def test_ec2_classic_has_public_ip_address_boto3():
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    instance = ec2.create_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)[0]
    instance.public_ip_address.should_not.equal(None)
    instance.public_dns_name.should.contain(
        instance.public_ip_address.replace(".", "-")
    )
    instance.private_ip_address.should_not.equal(None)
    instance.private_dns_name.should.contain(
        instance.private_ip_address.replace(".", "-")
    )


# Has boto3 equivalent
@mock_ec2_deprecated
def test_run_instance_with_keypair():
    conn = boto.connect_ec2("the_key", "the_secret")
    reservation = conn.run_instances(EXAMPLE_AMI_ID, key_name="keypair_name")
    instance = reservation.instances[0]

    instance.key_name.should.equal("keypair_name")


@mock_ec2
def test_run_instance_with_keypair_boto3():
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    instance = ec2.create_instances(
        ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1, KeyName="keypair_name"
    )[0]

    instance.key_name.should.equal("keypair_name")


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
    volumes["Volumes"][0]["Size"].should.equal(50)


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

    ex.value.response["Error"]["Code"].should.equal("MissingParameter")
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["Error"]["Message"].should.equal(
        "The request must contain the parameter ebs"
    )


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

    ex.value.response["Error"]["Code"].should.equal("MissingParameter")
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["Error"]["Message"].should.equal(
        "The request must contain the parameter size or snapshotId"
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

    volumes["Volumes"][0]["Size"].should.equal(30)
    volumes["Volumes"][0]["SnapshotId"].should.equal(snapshot.snapshot_id)


# Has boto3 equivalent
@mock_ec2_deprecated
def test_describe_instance_status_no_instances():
    conn = boto.connect_ec2("the_key", "the_secret")
    all_status = conn.get_all_instance_status()
    len(all_status).should.equal(0)


@mock_ec2
def test_describe_instance_status_no_instances_boto3():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("ServerMode is not guaranteed to be empty")
    client = boto3.client("ec2", region_name="us-east-1")
    all_status = client.describe_instance_status()["InstanceStatuses"]
    all_status.should.have.length_of(0)


# Has boto3 equivalent
@mock_ec2_deprecated
def test_describe_instance_status_with_instances():
    conn = boto.connect_ec2("the_key", "the_secret")
    conn.run_instances(EXAMPLE_AMI_ID, key_name="keypair_name")

    all_status = conn.get_all_instance_status()
    len(all_status).should.equal(1)
    all_status[0].instance_status.status.should.equal("ok")
    all_status[0].system_status.status.should.equal("ok")


@mock_ec2
def test_describe_instance_status_with_instances_boto3():
    client = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    instance = ec2.create_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)[0]

    all_status = client.describe_instance_status()["InstanceStatuses"]
    instance_ids = [s["InstanceId"] for s in all_status]
    instance_ids.should.contain(instance.id)

    my_status = [s for s in all_status if s["InstanceId"] == instance.id][0]
    my_status["InstanceStatus"]["Status"].should.equal("ok")
    my_status["SystemStatus"]["Status"].should.equal("ok")


# Has boto3 equivalent
@mock_ec2_deprecated
def test_describe_instance_status_with_instance_filter_deprecated():
    conn = boto.connect_ec2("the_key", "the_secret")

    # We want to filter based on this one
    reservation = conn.run_instances(EXAMPLE_AMI_ID, key_name="keypair_name")
    instance = reservation.instances[0]

    # This is just to setup the test
    conn.run_instances(EXAMPLE_AMI_ID, key_name="keypair_name")

    all_status = conn.get_all_instance_status(instance_ids=[instance.id])
    len(all_status).should.equal(1)
    all_status[0].id.should.equal(instance.id)

    # Call get_all_instance_status with a bad id should raise an error
    with pytest.raises(EC2ResponseError) as cm:
        conn.get_all_instance_status(instance_ids=[instance.id, "i-1234abcd"])
    cm.value.code.should.equal("InvalidInstanceID.NotFound")
    cm.value.status.should.equal(400)
    cm.value.request_id.should_not.be.none


@mock_ec2
def test_describe_instance_status_with_instance_filter_deprecated_boto3():
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    client = boto3.client("ec2", region_name="us-east-1")

    # We want to filter based on this one
    instance = ec2.create_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)[0]

    # This is just to setup the test
    ec2.create_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)

    all_status = client.describe_instance_status(InstanceIds=[instance.id])[
        "InstanceStatuses"
    ]
    all_status.should.have.length_of(1)
    all_status[0]["InstanceId"].should.equal(instance.id)

    # Call get_all_instance_status with a bad id should raise an error
    with pytest.raises(ClientError) as ex:
        client.describe_instance_status(InstanceIds=[instance.id, "i-1234abcd"])
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["ResponseMetadata"].should.have.key("RequestId")
    ex.value.response["Error"]["Code"].should.equal("InvalidInstanceID.NotFound")


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
        found_instance_ids.should.contain(_id)

    found_statuses = conn.describe_instance_status(
        IncludeAllInstances=True, Filters=state_name_filter["running"]
    )["InstanceStatuses"]
    found_instance_ids = [status["InstanceId"] for status in found_statuses]
    for _id in stopped_instance_ids:
        found_instance_ids.shouldnt.contain(_id)
    for _id in running_instance_ids:
        found_instance_ids.should.contain(_id)

    found_statuses = conn.describe_instance_status(
        IncludeAllInstances=True, Filters=state_name_filter["stopped"]
    )["InstanceStatuses"]
    found_instance_ids = [status["InstanceId"] for status in found_statuses]
    for _id in stopped_instance_ids:
        found_instance_ids.should.contain(_id)
    for _id in running_instance_ids:
        found_instance_ids.shouldnt.contain(_id)

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
        found_instance_ids.should.contain(_id)

    found_statuses = conn.describe_instance_status(
        IncludeAllInstances=True, Filters=state_code_filter["running"]
    )["InstanceStatuses"]
    found_instance_ids = [status["InstanceId"] for status in found_statuses]
    for _id in stopped_instance_ids:
        found_instance_ids.shouldnt.contain(_id)
    for _id in running_instance_ids:
        found_instance_ids.should.contain(_id)

    found_statuses = conn.describe_instance_status(
        IncludeAllInstances=True, Filters=state_code_filter["stopped"]
    )["InstanceStatuses"]
    found_instance_ids = [status["InstanceId"] for status in found_statuses]
    for _id in stopped_instance_ids:
        found_instance_ids.should.contain(_id)
    for _id in running_instance_ids:
        found_instance_ids.shouldnt.contain(_id)


# Has boto3 equivalent
@requires_boto_gte("2.32.0")
@mock_ec2_deprecated
def test_describe_instance_status_with_non_running_instances():
    conn = boto.connect_ec2("the_key", "the_secret")
    reservation = conn.run_instances(EXAMPLE_AMI_ID, min_count=3)
    instance1, instance2, instance3 = reservation.instances
    instance1.stop()
    instance2.terminate()

    all_running_status = conn.get_all_instance_status()
    all_running_status.should.have.length_of(1)
    all_running_status[0].id.should.equal(instance3.id)
    all_running_status[0].state_name.should.equal("running")

    all_status = conn.get_all_instance_status(include_all_instances=True)
    all_status.should.have.length_of(3)

    status1 = next((s for s in all_status if s.id == instance1.id), None)
    status1.state_name.should.equal("stopped")

    status2 = next((s for s in all_status if s.id == instance2.id), None)
    status2.state_name.should.equal("terminated")

    status3 = next((s for s in all_status if s.id == instance3.id), None)
    status3.state_name.should.equal("running")


@mock_ec2
def test_describe_instance_status_with_non_running_instances_boto3():
    client = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    reservation = ec2.create_instances(ImageId=EXAMPLE_AMI_ID, MinCount=3, MaxCount=3)
    instance1, instance2, instance3 = reservation
    instance1.stop()
    instance2.terminate()

    all_running_status = client.describe_instance_status()["InstanceStatuses"]
    [status["InstanceId"] for status in all_running_status].shouldnt.contain(
        instance1.id
    )
    [status["InstanceId"] for status in all_running_status].shouldnt.contain(
        instance2.id
    )
    [status["InstanceId"] for status in all_running_status].should.contain(instance3.id)

    my_status = [s for s in all_running_status if s["InstanceId"] == instance3.id][0]
    my_status["InstanceState"].should.equal({"Code": 16, "Name": "running"})

    all_status = client.describe_instance_status(IncludeAllInstances=True)[
        "InstanceStatuses"
    ]
    [status["InstanceId"] for status in all_status].should.contain(instance1.id)
    [status["InstanceId"] for status in all_status].should.contain(instance2.id)
    [status["InstanceId"] for status in all_status].should.contain(instance3.id)

    status1 = next((s for s in all_status if s["InstanceId"] == instance1.id), None)
    status1["InstanceState"].should.equal({"Code": 80, "Name": "stopped"})

    status2 = next((s for s in all_status if s["InstanceId"] == instance2.id), None)
    status2["InstanceState"].should.equal({"Code": 48, "Name": "terminated"})

    status3 = next((s for s in all_status if s["InstanceId"] == instance3.id), None)
    status3["InstanceState"].should.equal({"Code": 16, "Name": "running"})


# Has boto3 equivalent
@mock_ec2_deprecated
def test_get_instance_by_security_group():
    conn = boto.connect_ec2("the_key", "the_secret")

    conn.run_instances(EXAMPLE_AMI_ID)
    instance = conn.get_only_instances()[0]

    security_group = conn.create_security_group("test", "test")

    with pytest.raises(EC2ResponseError) as ex:
        conn.modify_instance_attribute(
            instance.id, "groupSet", [security_group.id], dry_run=True
        )
    ex.value.error_code.should.equal("DryRunOperation")
    ex.value.status.should.equal(412)
    ex.value.message.should.equal(
        "An error occurred (DryRunOperation) when calling the ModifyInstanceSecurityGroups operation: Request would have succeeded, but DryRun flag is set"
    )

    conn.modify_instance_attribute(instance.id, "groupSet", [security_group.id])

    security_group_instances = security_group.instances()

    assert len(security_group_instances) == 1
    assert security_group_instances[0].id == instance.id


@mock_ec2
def test_get_instance_by_security_group_boto3():
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
    ex.value.response["Error"]["Code"].should.equal("DryRunOperation")
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(412)
    ex.value.response["Error"]["Message"].should.equal(
        "An error occurred (DryRunOperation) when calling the ModifyInstanceSecurityGroups operation: Request would have succeeded, but DryRun flag is set"
    )

    client.modify_instance_attribute(InstanceId=instance.id, Groups=[security_group.id])

    instance.reload()
    security_group_instances = instance.describe_attribute(Attribute="groupSet")[
        "Groups"
    ]

    security_group_instances.should.have.length_of(1)
    security_group_instances.should.equal([{"GroupId": security_group.id}])


@mock_ec2
def test_modify_delete_on_termination():
    ec2_client = boto3.resource("ec2", region_name="us-west-1")
    result = ec2_client.create_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)
    instance = result[0]
    instance.load()
    instance.block_device_mappings[0]["Ebs"]["DeleteOnTermination"].should.be(True)
    instance.modify_attribute(
        BlockDeviceMappings=[
            {"DeviceName": "/dev/sda1", "Ebs": {"DeleteOnTermination": False}}
        ]
    )
    instance.load()
    instance.block_device_mappings[0]["Ebs"]["DeleteOnTermination"].should.be(False)


@mock_ec2
def test_create_instance_ebs_optimized():
    ec2_resource = boto3.resource("ec2", region_name="eu-west-1")

    instance = ec2_resource.create_instances(
        ImageId=EXAMPLE_AMI_ID, MaxCount=1, MinCount=1, EbsOptimized=True
    )[0]
    instance.load()
    instance.ebs_optimized.should.be(True)

    instance.modify_attribute(EbsOptimized={"Value": False})
    instance.load()
    instance.ebs_optimized.should.be(False)

    instance = ec2_resource.create_instances(
        ImageId=EXAMPLE_AMI_ID, MaxCount=1, MinCount=1,
    )[0]
    instance.load()
    instance.ebs_optimized.should.be(False)


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

    my_reservation["Instances"].should.have.length_of(instance_count)

    instances = my_reservation["Instances"]
    for i in range(0, instance_count):
        instances[i]["AmiLaunchIndex"].should.be(i)


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
            response.should.have.key("Groups")
            response["Groups"].should.have.length_of(1)
            response["Groups"][0]["GroupId"].should.equal(security_group_id)
        elif valid_instance_attribute == "userData":
            response.should.have.key("UserData")
            response["UserData"].should.be.empty

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
        ex.value.response["Error"]["Code"].should.equal("InvalidParameterValue")
        ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
        message = "Value ({invalid_instance_attribute}) for parameter attribute is invalid. Unknown attribute.".format(
            invalid_instance_attribute=invalid_instance_attribute
        )
        ex.value.response["Error"]["Message"].should.equal(message)


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
    instances.should.have.length_of(1)
    instances[0]["Tags"][0].should.have.key("Key").should.equal("Name")


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
    error["Code"].should.equal("OperationNotPermitted")
    ex.value.response["Error"]["Message"].should.match(
        r"The instance '{}' may not be terminated.*$".format(instance_id)
    )

    # Use alternate request syntax for setting attribute.
    client.modify_instance_attribute(
        InstanceId=instance_id, Attribute="disableApiTermination", Value="false"
    )
    client.terminate_instances(InstanceIds=[instance_id])

    resp = client.describe_instances(InstanceIds=[instance_id])
    instances = resp["Reservations"][0]["Instances"]
    instances.should.have.length_of(1)
    instance = instances[0]
    instance["State"]["Name"].should.equal("terminated")


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
        LaunchTemplateName=str(uuid4()), LaunchTemplateData={"ImageId": EXAMPLE_AMI_ID},
    )["LaunchTemplate"]

    with pytest.warns(None) as captured_warnings:
        resource.create_instances(
            MinCount=1,
            MaxCount=1,
            LaunchTemplate={launch_template_kind: template[launch_template_kind]},
        )

    assert len(captured_warnings) == 0


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
        NetworkInterfaces=[{"DeviceIndex": 0}],
        SubnetId=subnet.id,
    )[0]
    interfaces = instance.network_interfaces_attribute
    addresses = interfaces[0]["PrivateIpAddresses"][0]
    addresses.should.have.key("Primary").equal(True)
    addresses.should.have.key("PrivateIpAddress")
    addresses.shouldnt.have.key("Association")

    # Pass AssociatePublicIpAddress=False
    instance = ec2.create_instances(
        ImageId=EXAMPLE_AMI_ID,
        MinCount=1,
        MaxCount=1,
        NetworkInterfaces=[{"DeviceIndex": 0, "AssociatePublicIpAddress": False}],
        SubnetId=subnet.id,
    )[0]
    interfaces = instance.network_interfaces_attribute
    addresses = interfaces[0]["PrivateIpAddresses"][0]
    addresses.should.have.key("Primary").equal(True)
    addresses.should.have.key("PrivateIpAddress")
    addresses.shouldnt.have.key("Association")

    # Pass AssociatePublicIpAddress=True
    instance = ec2.create_instances(
        ImageId=EXAMPLE_AMI_ID,
        MinCount=1,
        MaxCount=1,
        NetworkInterfaces=[{"DeviceIndex": 0, "AssociatePublicIpAddress": True}],
        SubnetId=subnet.id,
    )[0]
    interfaces = instance.network_interfaces_attribute
    addresses = interfaces[0]["PrivateIpAddresses"][0]
    addresses.should.have.key("Primary").equal(True)
    addresses.should.have.key("PrivateIpAddress")
    addresses.should.have.key("Association")
    # Only now should we have a PublicIp
    addresses["Association"].should.have.key("IpOwnerId").equal(ACCOUNT_ID)
    addresses["Association"].should.have.key("PublicIp")


@mock_ec2
def test_describe_instances_dryrun():
    client = boto3.client("ec2", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        client.describe_instances(DryRun=True)
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(412)
    ex.value.response["Error"]["Code"].should.equal("DryRunOperation")
    ex.value.response["Error"]["Message"].should.equal(
        "An error occurred (DryRunOperation) when calling the DescribeInstances operation: Request would have succeeded, but DryRun flag is set"
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
        "PrivateIpAddresses": [{"Primary": True, "PrivateIpAddress": "10.26.1.3"},],
    }
    instance = ec2.create_instances(
        ImageId="myami", NetworkInterfaces=[my_interface], MinCount=1, MaxCount=1
    )[0]

    _filter = [{"Name": "vpc-id", "Values": [vpc.id,]}]
    found = list(ec2.instances.filter(Filters=_filter))
    found.should.have.length_of(1)
    found.should.equal([instance])


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
