import pytest

import itertools

import boto
import boto3
from botocore.exceptions import ClientError
from boto.exception import EC2ResponseError
from boto.ec2.instance import Reservation
import sure  # noqa # pylint: disable=unused-import

from moto import mock_ec2_deprecated, mock_ec2
from tests import EXAMPLE_AMI_ID
from .test_instances import retrieve_all_instances
from uuid import uuid4


# Has boto3 equivalent
@mock_ec2_deprecated
def test_add_tag():
    conn = boto.connect_ec2("the_key", "the_secret")
    reservation = conn.run_instances(EXAMPLE_AMI_ID)
    instance = reservation.instances[0]

    with pytest.raises(EC2ResponseError) as ex:
        instance.add_tag("a key", "some value", dry_run=True)
    ex.value.error_code.should.equal("DryRunOperation")
    ex.value.status.should.equal(412)
    ex.value.message.should.equal(
        "An error occurred (DryRunOperation) when calling the CreateTags operation: Request would have succeeded, but DryRun flag is set"
    )

    instance.add_tag("a key", "some value")
    chain = itertools.chain.from_iterable
    existing_instances = list(
        chain([res.instances for res in conn.get_all_reservations()])
    )
    existing_instances.should.have.length_of(1)
    existing_instance = existing_instances[0]
    existing_instance.tags["a key"].should.equal("some value")


@mock_ec2
def test_instance_create_tags():
    ec2 = boto3.resource("ec2", "us-west-1")
    client = boto3.client("ec2", "us-west-1")
    instance = ec2.create_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)[0]

    with pytest.raises(ClientError) as ex:
        instance.create_tags(
            Tags=[{"Key": "a key", "Value": "some value"}], DryRun=True
        )
    ex.value.response["Error"]["Code"].should.equal("DryRunOperation")
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(412)
    ex.value.response["Error"]["Message"].should.equal(
        "An error occurred (DryRunOperation) when calling the CreateTags operation: Request would have succeeded, but DryRun flag is set"
    )

    instance.create_tags(Tags=[{"Key": "a key", "Value": "some value"}])
    existing_instances = retrieve_all_instances(client)
    ours = [i for i in existing_instances if i["InstanceId"] == instance.id][0]
    ours["Tags"].should.equal([{"Key": "a key", "Value": "some value"}])


# Has boto3 equivalent
@mock_ec2_deprecated
def test_remove_tag():
    conn = boto.connect_ec2("the_key", "the_secret")
    reservation = conn.run_instances(EXAMPLE_AMI_ID)
    instance = reservation.instances[0]

    instance.add_tag("a key", "some value")

    tags = conn.get_all_tags()
    tag = tags[0]
    tag.name.should.equal("a key")
    tag.value.should.equal("some value")

    with pytest.raises(EC2ResponseError) as ex:
        instance.remove_tag("a key", dry_run=True)
    ex.value.error_code.should.equal("DryRunOperation")
    ex.value.status.should.equal(412)
    ex.value.message.should.equal(
        "An error occurred (DryRunOperation) when calling the DeleteTags operation: Request would have succeeded, but DryRun flag is set"
    )

    instance.remove_tag("a key")
    conn.get_all_tags().should.have.length_of(0)

    instance.add_tag("a key", "some value")
    conn.get_all_tags().should.have.length_of(1)
    instance.remove_tag("a key", "some value")


@mock_ec2
def test_instance_delete_tags():
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    client = boto3.client("ec2", region_name="us-east-1")
    instance = ec2.create_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)[0]

    instance.create_tags(Tags=[{"Key": "a key", "Value": "some value"}])

    tags = client.describe_tags(
        Filters=[{"Name": "resource-id", "Values": [instance.id]}]
    )["Tags"]
    tag = tags[0]
    tag.should.have.key("Key").equal("a key")
    tag.should.have.key("Value").equal("some value")

    with pytest.raises(ClientError) as ex:
        instance.delete_tags(DryRun=True)
    ex.value.response["Error"]["Code"].should.equal("DryRunOperation")
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(412)
    ex.value.response["Error"]["Message"].should.equal(
        "An error occurred (DryRunOperation) when calling the DeleteTags operation: Request would have succeeded, but DryRun flag is set"
    )

    # Specifying key only
    instance.delete_tags(Tags=[{"Key": "a key"}])
    client.describe_tags(Filters=[{"Name": "resource-id", "Values": [instance.id]}])[
        "Tags"
    ].should.have.length_of(0)

    instance.create_tags(Tags=[{"Key": "a key", "Value": "some value"}])
    client.describe_tags(Filters=[{"Name": "resource-id", "Values": [instance.id]}])[
        "Tags"
    ].should.have.length_of(1)

    # Specifying key and value
    instance.delete_tags(Tags=[{"Key": "a key", "Value": "some value"}])
    client.describe_tags(Filters=[{"Name": "resource-id", "Values": [instance.id]}])[
        "Tags"
    ].should.have.length_of(0)


# Has boto3 equivalent
@mock_ec2_deprecated
def test_get_all_tags():
    conn = boto.connect_ec2("the_key", "the_secret")
    reservation = conn.run_instances(EXAMPLE_AMI_ID)
    instance = reservation.instances[0]

    instance.add_tag("a key", "some value")

    tags = conn.get_all_tags()
    tag = tags[0]
    tag.name.should.equal("a key")
    tag.value.should.equal("some value")


# Has boto3 equivalent
@mock_ec2_deprecated
def test_get_all_tags_with_special_characters():
    conn = boto.connect_ec2("the_key", "the_secret")
    reservation = conn.run_instances(EXAMPLE_AMI_ID)
    instance = reservation.instances[0]

    instance.add_tag("a key", "some<> value")

    tags = conn.get_all_tags()
    tag = tags[0]
    tag.name.should.equal("a key")
    tag.value.should.equal("some<> value")


@mock_ec2
def test_get_all_tags_with_special_characters_boto3():
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    client = boto3.client("ec2", region_name="us-east-1")
    instance = ec2.create_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)[0]

    tag_key = str(uuid4())
    instance.create_tags(Tags=[{"Key": tag_key, "Value": "some<> value"}])

    tag = client.describe_tags(Filters=[{"Name": "key", "Values": [tag_key]}])["Tags"][
        0
    ]
    tag.should.have.key("Key").equal(tag_key)
    tag.should.have.key("Value").equal("some<> value")


# Has boto3 equivalent
@mock_ec2_deprecated
def test_create_tags():
    conn = boto.connect_ec2("the_key", "the_secret")
    reservation = conn.run_instances(EXAMPLE_AMI_ID)
    instance = reservation.instances[0]
    tag_dict = {
        "a key": "some value",
        "another key": "some other value",
        "blank key": "",
    }

    with pytest.raises(EC2ResponseError) as ex:
        conn.create_tags(instance.id, tag_dict, dry_run=True)
    ex.value.error_code.should.equal("DryRunOperation")
    ex.value.status.should.equal(412)
    ex.value.message.should.equal(
        "An error occurred (DryRunOperation) when calling the CreateTags operation: Request would have succeeded, but DryRun flag is set"
    )

    conn.create_tags(instance.id, tag_dict)
    tags = conn.get_all_tags()
    set([key for key in tag_dict]).should.equal(set([tag.name for tag in tags]))
    set([tag_dict[key] for key in tag_dict]).should.equal(
        set([tag.value for tag in tags])
    )


@mock_ec2
def test_create_tags_boto3():
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    client = boto3.client("ec2", region_name="us-east-1")
    instance = ec2.create_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)[0]
    tag_list = [
        {"Key": "a key", "Value": "some value"},
        {"Key": "another key", "Value": "some other value"},
        {"Key": "blank key", "Value": ""},
    ]

    with pytest.raises(ClientError) as ex:
        client.create_tags(Resources=[instance.id], Tags=tag_list, DryRun=True)
    ex.value.response["Error"]["Code"].should.equal("DryRunOperation")
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(412)
    ex.value.response["Error"]["Message"].should.equal(
        "An error occurred (DryRunOperation) when calling the CreateTags operation: Request would have succeeded, but DryRun flag is set"
    )

    client.create_tags(Resources=[instance.id], Tags=tag_list)
    tags = client.describe_tags(
        Filters=[{"Name": "resource-id", "Values": [instance.id]}]
    )["Tags"]
    tags.should.have.length_of(3)
    for expected_tag in tag_list:
        tags.should.contain(
            {
                "Key": expected_tag["Key"],
                "ResourceId": instance.id,
                "ResourceType": "instance",
                "Value": expected_tag["Value"],
            }
        )


# Has boto3 equivalent
@mock_ec2_deprecated
def test_tag_limit_exceeded():
    conn = boto.connect_ec2("the_key", "the_secret")
    reservation = conn.run_instances(EXAMPLE_AMI_ID)
    instance = reservation.instances[0]
    tag_dict = {}
    for i in range(51):
        tag_dict["{0:02d}".format(i + 1)] = ""

    with pytest.raises(EC2ResponseError) as cm:
        conn.create_tags(instance.id, tag_dict)
    cm.value.code.should.equal("TagLimitExceeded")
    cm.value.status.should.equal(400)
    cm.value.request_id.should_not.be.none

    instance.add_tag("a key", "a value")
    with pytest.raises(EC2ResponseError) as cm:
        conn.create_tags(instance.id, tag_dict)
    cm.value.code.should.equal("TagLimitExceeded")
    cm.value.status.should.equal(400)
    cm.value.request_id.should_not.be.none

    tags = conn.get_all_tags()
    tag = tags[0]
    tags.should.have.length_of(1)
    tag.name.should.equal("a key")
    tag.value.should.equal("a value")


@mock_ec2
def test_tag_limit_exceeded_boto3():
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    client = boto3.client("ec2", region_name="us-east-1")
    instance = ec2.create_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)[0]
    tag_list = []
    for i in range(51):
        tag_list.append({"Key": "{0:02d}".format(i + 1), "Value": ""})

    with pytest.raises(ClientError) as ex:
        client.create_tags(Resources=[instance.id], Tags=tag_list)
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["ResponseMetadata"].should.have.key("RequestId")
    ex.value.response["Error"]["Code"].should.equal("TagLimitExceeded")

    instance.create_tags(Tags=[{"Key": "a key", "Value": "a value"}])
    with pytest.raises(ClientError) as ex:
        client.create_tags(Resources=[instance.id], Tags=tag_list)
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["ResponseMetadata"].should.have.key("RequestId")
    ex.value.response["Error"]["Code"].should.equal("TagLimitExceeded")

    tags = client.describe_tags(
        Filters=[{"Name": "resource-id", "Values": [instance.id]}]
    )["Tags"]
    tags.should.have.length_of(1)
    tags[0].should.have.key("Key").equal("a key")
    tags[0].should.have.key("Value").equal("a value")


# Has boto3 equivalent
@mock_ec2_deprecated
def test_invalid_parameter_tag_null():
    conn = boto.connect_ec2("the_key", "the_secret")
    reservation = conn.run_instances(EXAMPLE_AMI_ID)
    instance = reservation.instances[0]

    with pytest.raises(EC2ResponseError) as cm:
        instance.add_tag("a key", None)
    cm.value.code.should.equal("InvalidParameterValue")
    cm.value.status.should.equal(400)
    cm.value.request_id.should_not.be.none


# Has boto3 equivalent
@mock_ec2_deprecated
def test_invalid_id():
    conn = boto.connect_ec2("the_key", "the_secret")
    with pytest.raises(EC2ResponseError) as cm:
        conn.create_tags("ami-blah", {"key": "tag"})
    cm.value.code.should.equal("InvalidID")
    cm.value.status.should.equal(400)
    cm.value.request_id.should_not.be.none

    with pytest.raises(EC2ResponseError) as cm:
        conn.create_tags("blah-blah", {"key": "tag"})
    cm.value.code.should.equal("InvalidID")
    cm.value.status.should.equal(400)
    cm.value.request_id.should_not.be.none


@mock_ec2
def test_invalid_id_boto3():
    client = boto3.client("ec2", region_name="us-east-1")
    with pytest.raises(ClientError) as ex:
        client.create_tags(
            Resources=["ami-blah"], Tags=[{"Key": "key", "Value": "tag"}]
        )
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["ResponseMetadata"].should.have.key("RequestId")
    ex.value.response["Error"]["Code"].should.equal("InvalidID")

    with pytest.raises(ClientError) as ex:
        client.create_tags(
            Resources=["blah-blah"], Tags=[{"Key": "key", "Value": "tag"}]
        )
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["ResponseMetadata"].should.have.key("RequestId")
    ex.value.response["Error"]["Code"].should.equal("InvalidID")


# Has boto3 equivalent
@mock_ec2_deprecated
def test_get_all_tags_resource_id_filter():
    conn = boto.connect_ec2("the_key", "the_secret")
    reservation = conn.run_instances(EXAMPLE_AMI_ID)
    instance = reservation.instances[0]
    instance.add_tag("an instance key", "some value")
    image_id = conn.create_image(instance.id, "test-ami", "this is a test ami")
    image = conn.get_image(image_id)
    image.add_tag("an image key", "some value")

    tags = conn.get_all_tags(filters={"resource-id": instance.id})
    tag = tags[0]
    tags.should.have.length_of(1)
    tag.res_id.should.equal(instance.id)
    tag.res_type.should.equal("instance")
    tag.name.should.equal("an instance key")
    tag.value.should.equal("some value")

    tags = conn.get_all_tags(filters={"resource-id": image_id})
    tag = tags[0]
    tags.should.have.length_of(1)
    tag.res_id.should.equal(image_id)
    tag.res_type.should.equal("image")
    tag.name.should.equal("an image key")
    tag.value.should.equal("some value")


@mock_ec2
def test_get_all_tags_resource_filter_boto3():
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    client = boto3.client("ec2", region_name="us-east-1")
    instance = ec2.create_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)[0]
    inst_tag_key = str(uuid4())[0:6]
    client.create_tags(
        Resources=[instance.id], Tags=[{"Key": inst_tag_key, "Value": "some value"}],
    )
    image = instance.create_image(Name="test-ami", Description="this is a test ami")
    image.create_tags(Tags=[{"Key": "an image key", "Value": "some value"}])

    expected = {
        "Key": inst_tag_key,
        "ResourceId": instance.id,
        "ResourceType": "instance",
        "Value": "some value",
    }
    our_tags = client.describe_tags(
        Filters=[{"Name": "resource-id", "Values": [instance.id]}]
    )["Tags"]
    our_tags.should.equal([expected])
    instances = client.describe_tags(
        Filters=[{"Name": "resource-type", "Values": ["instance"]}]
    )["Tags"]
    instances.should.contain(expected)
    tags = client.describe_tags(Filters=[{"Name": "key", "Values": [inst_tag_key]}])[
        "Tags"
    ]
    tags.should.equal([expected])

    expected = {
        "Key": "an image key",
        "ResourceId": image.id,
        "ResourceType": "image",
        "Value": "some value",
    }
    my_image = client.describe_tags(
        Filters=[{"Name": "resource-id", "Values": [image.id]}]
    )["Tags"]
    my_image.should.equal([expected])
    all_images = client.describe_tags(
        Filters=[{"Name": "resource-type", "Values": ["image"]}]
    )["Tags"]
    all_images.should.contain(expected)

    tags = client.describe_tags(
        Filters=[{"Name": "resource-type", "Values": ["unknown"]}]
    )["Tags"]
    tags.should.equal([])


# Has boto3 equivalent
@mock_ec2_deprecated
def test_get_all_tags_resource_type_filter():
    conn = boto.connect_ec2("the_key", "the_secret")
    reservation = conn.run_instances(EXAMPLE_AMI_ID)
    instance = reservation.instances[0]
    instance.add_tag("an instance key", "some value")
    image_id = conn.create_image(instance.id, "test-ami", "this is a test ami")
    image = conn.get_image(image_id)
    image.add_tag("an image key", "some value")

    tags = conn.get_all_tags(filters={"resource-type": "instance"})
    tag = tags[0]
    tags.should.have.length_of(1)
    tag.res_id.should.equal(instance.id)
    tag.res_type.should.equal("instance")
    tag.name.should.equal("an instance key")
    tag.value.should.equal("some value")

    tags = conn.get_all_tags(filters={"resource-type": "image"})
    tag = tags[0]
    tags.should.have.length_of(1)
    tag.res_id.should.equal(image_id)
    tag.res_type.should.equal("image")
    tag.name.should.equal("an image key")
    tag.value.should.equal("some value")


# Has boto3 equivalent
@mock_ec2_deprecated
def test_get_all_tags_key_filter():
    conn = boto.connect_ec2("the_key", "the_secret")
    reservation = conn.run_instances(EXAMPLE_AMI_ID)
    instance = reservation.instances[0]
    instance.add_tag("an instance key", "some value")
    image_id = conn.create_image(instance.id, "test-ami", "this is a test ami")
    image = conn.get_image(image_id)
    image.add_tag("an image key", "some value")

    tags = conn.get_all_tags(filters={"key": "an instance key"})
    tag = tags[0]
    tags.should.have.length_of(1)
    tag.res_id.should.equal(instance.id)
    tag.res_type.should.equal("instance")
    tag.name.should.equal("an instance key")
    tag.value.should.equal("some value")


# Has boto3 equivalent
@mock_ec2_deprecated
def test_get_all_tags_value_filter():
    conn = boto.connect_ec2("the_key", "the_secret")
    reservation = conn.run_instances(EXAMPLE_AMI_ID)
    instance = reservation.instances[0]
    instance.add_tag("an instance key", "some value")
    reservation_b = conn.run_instances(EXAMPLE_AMI_ID)
    instance_b = reservation_b.instances[0]
    instance_b.add_tag("an instance key", "some other value")
    reservation_c = conn.run_instances(EXAMPLE_AMI_ID)
    instance_c = reservation_c.instances[0]
    instance_c.add_tag("an instance key", "other value*")
    reservation_d = conn.run_instances(EXAMPLE_AMI_ID)
    instance_d = reservation_d.instances[0]
    instance_d.add_tag("an instance key", "other value**")
    reservation_e = conn.run_instances(EXAMPLE_AMI_ID)
    instance_e = reservation_e.instances[0]
    instance_e.add_tag("an instance key", "other value*?")
    image_id = conn.create_image(instance.id, "test-ami", "this is a test ami")
    image = conn.get_image(image_id)
    image.add_tag("an image key", "some value")

    tags = conn.get_all_tags(filters={"value": "some value"})
    tags.should.have.length_of(2)

    tags = conn.get_all_tags(filters={"value": "some*value"})
    tags.should.have.length_of(3)

    tags = conn.get_all_tags(filters={"value": "*some*value"})
    tags.should.have.length_of(3)

    tags = conn.get_all_tags(filters={"value": "*some*value*"})
    tags.should.have.length_of(3)

    tags = conn.get_all_tags(filters={"value": r"*value\*"})
    tags.should.have.length_of(1)

    tags = conn.get_all_tags(filters={"value": r"*value\*\*"})
    tags.should.have.length_of(1)

    tags = conn.get_all_tags(filters={"value": r"*value\*\?"})
    tags.should.have.length_of(1)


@mock_ec2
def test_get_all_tags_value_filter_boto3():
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    client = boto3.client("ec2", region_name="us-east-1")

    def create_instance_with_tag(value):
        instance = ec2.create_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)[
            0
        ]
        tag = {"Key": "an instance key", "Value": value}
        client.create_tags(Resources=[instance.id], Tags=[tag])
        return instance

    instance_a = create_instance_with_tag("some value")
    instance_b = create_instance_with_tag("some other value")
    instance_c = create_instance_with_tag("other value*")
    instance_d = create_instance_with_tag("other value**")
    instance_e = create_instance_with_tag("other value*?")

    image = instance_a.create_image(Name="test-ami", Description="this is a test ami")
    image.create_tags(Tags=[{"Key": "an image key", "Value": "some value"}])

    def filter_by_value(query, expected):
        filters = [{"Name": "value", "Values": [query]}]
        tags = retrieve_all_tagged(client, filters)
        actual = set([t["ResourceId"] for t in tags])
        for e in expected:
            actual.should.contain(e)

    filter_by_value("some value", [instance_a.id, image.id])
    filter_by_value("some*value", [instance_a.id, instance_b.id, image.id])
    filter_by_value("*some*value", [instance_a.id, instance_b.id, image.id])
    filter_by_value("*some*value*", [instance_a.id, instance_b.id, image.id])
    filter_by_value(r"*value\*", [instance_c.id])
    filter_by_value(r"*value\*\*", [instance_d.id])
    filter_by_value(r"*value\*\?", [instance_e.id])


# Has boto3 equivalent
@mock_ec2_deprecated
def test_retrieved_instances_must_contain_their_tags():
    tag_key = "Tag name"
    tag_value = "Tag value"
    tags_to_be_set = {tag_key: tag_value}

    conn = boto.connect_ec2("the_key", "the_secret")
    reservation = conn.run_instances(EXAMPLE_AMI_ID)
    reservation.should.be.a(Reservation)
    reservation.instances.should.have.length_of(1)
    instance = reservation.instances[0]

    reservations = conn.get_all_reservations()
    reservations.should.have.length_of(1)
    reservations[0].id.should.equal(reservation.id)
    instances = reservations[0].instances
    instances.should.have.length_of(1)
    instances[0].id.should.equal(instance.id)

    conn.create_tags([instance.id], tags_to_be_set)
    reservations = conn.get_all_reservations()
    instance = reservations[0].instances[0]
    retrieved_tags = instance.tags

    # Cleanup of instance
    conn.terminate_instances([instances[0].id])

    # Check whether tag is present with correct value
    retrieved_tags[tag_key].should.equal(tag_value)


@mock_ec2
def test_retrieved_instances_must_contain_their_tags_boto3():
    tag_key = "Tag name"
    tag_value = "Tag value"
    tags_to_be_set = {"Key": tag_key, "Value": tag_value}

    ec2 = boto3.resource("ec2", region_name="us-east-1")
    client = boto3.client("ec2", region_name="us-east-1")
    instance = ec2.create_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)[0]

    all_instances = retrieve_all_instances(client)
    ours = [i for i in all_instances if i["InstanceId"] == instance.id]
    ours.should.have.length_of(1)
    ours[0]["InstanceId"].should.equal(instance.id)
    ours[0].shouldnt.have.key("Tags")

    client.create_tags(Resources=[instance.id], Tags=[tags_to_be_set])

    all_instances = retrieve_all_instances(client)
    ours = [i for i in all_instances if i["InstanceId"] == instance.id]
    retrieved_tags = ours[0]["Tags"]

    # Check whether tag is present with correct value
    retrieved_tags.should.equal([{"Key": tag_key, "Value": tag_value}])


# Has boto3 equivalent
@mock_ec2_deprecated
def test_retrieved_volumes_must_contain_their_tags():
    tag_key = "Tag name"
    tag_value = "Tag value"
    tags_to_be_set = {tag_key: tag_value}
    conn = boto.connect_ec2("the_key", "the_secret")
    volume = conn.create_volume(80, "us-east-1a")

    all_volumes = conn.get_all_volumes()
    volume = all_volumes[0]
    conn.create_tags([volume.id], tags_to_be_set)

    # Fetch the volume again
    all_volumes = conn.get_all_volumes()
    volume = all_volumes[0]
    retrieved_tags = volume.tags

    volume.delete()

    # Check whether tag is present with correct value
    retrieved_tags[tag_key].should.equal(tag_value)


@mock_ec2
def test_retrieved_volumes_must_contain_their_tags_boto3():
    tag_key = "Tag name"
    tag_value = "Tag value"
    tags_to_be_set = {"Key": tag_key, "Value": tag_value}

    ec2 = boto3.resource("ec2", region_name="eu-west-1")
    client = boto3.client("ec2", region_name="eu-west-1")
    volume = ec2.create_volume(Size=80, AvailabilityZone="us-east-1a")
    volume.tags.should.be.none

    client.create_tags(Resources=[volume.id], Tags=[tags_to_be_set])

    volume.reload()
    volume.tags.should.equal([{"Key": tag_key, "Value": tag_value}])


# Has boto3 equivalent
@mock_ec2_deprecated
def test_retrieved_snapshots_must_contain_their_tags():
    tag_key = "Tag name"
    tag_value = "Tag value"
    tags_to_be_set = {tag_key: tag_value}
    conn = boto.connect_ec2(
        aws_access_key_id="the_key", aws_secret_access_key="the_secret"
    )
    volume = conn.create_volume(80, "eu-west-1a")
    snapshot = conn.create_snapshot(volume.id)
    conn.create_tags([snapshot.id], tags_to_be_set)

    # Fetch the snapshot again
    all_snapshots = conn.get_all_snapshots()
    snapshot = [item for item in all_snapshots if item.id == snapshot.id][0]
    retrieved_tags = snapshot.tags

    conn.delete_snapshot(snapshot.id)
    volume.delete()

    # Check whether tag is present with correct value
    retrieved_tags[tag_key].should.equal(tag_value)


@mock_ec2
def test_retrieved_snapshots_must_contain_their_tags_boto3():
    tag_key = "Tag name"
    tag_value = "Tag value"
    tags_to_be_set = {"Key": tag_key, "Value": tag_value}

    ec2 = boto3.resource("ec2", region_name="eu-west-1")
    client = boto3.client("ec2", region_name="eu-west-1")

    volume = ec2.create_volume(Size=80, AvailabilityZone="eu-west-1a")
    snapshot = ec2.create_snapshot(VolumeId=volume.id)
    client.create_tags(Resources=[snapshot.id], Tags=[tags_to_be_set])

    snapshot = client.describe_snapshots(SnapshotIds=[snapshot.id])["Snapshots"][0]
    snapshot["Tags"].should.equal([{"Key": tag_key, "Value": tag_value}])


# Has boto3 equivalent
@mock_ec2_deprecated
def test_filter_instances_by_wildcard_tags():
    conn = boto.connect_ec2(
        aws_access_key_id="the_key", aws_secret_access_key="the_secret"
    )
    reservation = conn.run_instances(EXAMPLE_AMI_ID)
    instance_a = reservation.instances[0]
    instance_a.add_tag("Key1", "Value1")
    reservation_b = conn.run_instances(EXAMPLE_AMI_ID)
    instance_b = reservation_b.instances[0]
    instance_b.add_tag("Key1", "Value2")

    reservations = conn.get_all_reservations(filters={"tag:Key1": "Value*"})
    reservations.should.have.length_of(2)

    reservations = conn.get_all_reservations(filters={"tag-key": "Key*"})
    reservations.should.have.length_of(2)

    reservations = conn.get_all_reservations(filters={"tag-value": "Value*"})
    reservations.should.have.length_of(2)


@mock_ec2
def test_filter_instances_by_wildcard_tags_boto3():
    ec2 = boto3.resource("ec2", region_name="eu-west-1")
    client = boto3.client("ec2", region_name="eu-west-1")

    reservations = ec2.create_instances(ImageId=EXAMPLE_AMI_ID, MinCount=2, MaxCount=2)
    instance_a, instance_b = reservations

    instance_a.create_tags(Tags=[{"Key": "Key1", "Value": "Value1"}])
    instance_b.create_tags(Tags=[{"Key": "Key1", "Value": "Value2"}])

    res = client.describe_instances(
        Filters=[{"Name": "tag:Key1", "Values": ["Value*"]}]
    )
    res["Reservations"][0]["Instances"].should.have.length_of(2)

    res = client.describe_instances(Filters=[{"Name": "tag-key", "Values": ["Key*"]}])
    res["Reservations"][0]["Instances"].should.have.length_of(2)

    res = client.describe_instances(
        Filters=[{"Name": "tag-value", "Values": ["Value*"]}]
    )
    res["Reservations"][0]["Instances"].should.have.length_of(2)

    res = client.describe_instances(
        Filters=[{"Name": "tag-value", "Values": ["Value2*"]}]
    )
    res["Reservations"][0]["Instances"].should.have.length_of(1)


@mock_ec2
def test_create_volume_with_tags():
    client = boto3.client("ec2", "us-west-2")
    response = client.create_volume(
        AvailabilityZone="us-west-2",
        Encrypted=False,
        Size=40,
        TagSpecifications=[
            {
                "ResourceType": "volume",
                "Tags": [{"Key": "TEST_TAG", "Value": "TEST_VALUE"}],
            }
        ],
    )

    assert response["Tags"][0]["Key"] == "TEST_TAG"


@mock_ec2
def test_create_snapshot_with_tags():
    client = boto3.client("ec2", "us-west-2")
    volume_id = client.create_volume(
        AvailabilityZone="us-west-2",
        Encrypted=False,
        Size=40,
        TagSpecifications=[
            {
                "ResourceType": "volume",
                "Tags": [{"Key": "TEST_TAG", "Value": "TEST_VALUE"}],
            }
        ],
    )["VolumeId"]
    snapshot = client.create_snapshot(
        VolumeId=volume_id,
        TagSpecifications=[
            {
                "ResourceType": "snapshot",
                "Tags": [{"Key": "TEST_SNAPSHOT_TAG", "Value": "TEST_SNAPSHOT_VALUE"}],
            }
        ],
    )

    expected_tags = [{"Key": "TEST_SNAPSHOT_TAG", "Value": "TEST_SNAPSHOT_VALUE"}]

    assert snapshot["Tags"] == expected_tags


@mock_ec2
def test_create_tag_empty_resource():
    # create ec2 client in us-west-1
    client = boto3.client("ec2", region_name="us-west-1")
    # create tag with empty resource
    with pytest.raises(ClientError) as ex:
        client.create_tags(Resources=[], Tags=[{"Key": "Value"}])
    ex.value.response["Error"]["Code"].should.equal("MissingParameter")
    ex.value.response["Error"]["Message"].should.equal(
        "The request must contain the parameter resourceIdSet"
    )


@mock_ec2
def test_delete_tag_empty_resource():
    # create ec2 client in us-west-1
    client = boto3.client("ec2", region_name="us-west-1")
    # delete tag with empty resource
    with pytest.raises(ClientError) as ex:
        client.delete_tags(Resources=[], Tags=[{"Key": "Value"}])
    ex.value.response["Error"]["Code"].should.equal("MissingParameter")
    ex.value.response["Error"]["Message"].should.equal(
        "The request must contain the parameter resourceIdSet"
    )


@mock_ec2
def test_retrieve_resource_with_multiple_tags():
    ec2 = boto3.resource("ec2", region_name="us-west-1")
    blue, green = ec2.create_instances(ImageId=EXAMPLE_AMI_ID, MinCount=2, MaxCount=2)
    tag_val1 = str(uuid4())
    ec2.create_tags(
        Resources=[blue.instance_id],
        Tags=[
            {"Key": "environment", "Value": tag_val1},
            {"Key": "application", "Value": "api"},
        ],
    )
    tag_val2 = str(uuid4())
    ec2.create_tags(
        Resources=[green.instance_id],
        Tags=[
            {"Key": "environment", "Value": tag_val2},
            {"Key": "application", "Value": "api"},
        ],
    )
    green_instances = list(ec2.instances.filter(Filters=(get_filter(tag_val2))))
    green_instances.should.equal([green])
    blue_instances = list(ec2.instances.filter(Filters=(get_filter(tag_val1))))
    blue_instances.should.equal([blue])


def get_filter(tag_val):
    return [
        {"Name": "tag-key", "Values": ["application"]},
        {"Name": "tag-value", "Values": ["api"]},
        {"Name": "tag-key", "Values": ["environment"]},
        {"Name": "tag-value", "Values": [tag_val]},
    ]


def retrieve_all_tagged(client, filters=[]):  # pylint: disable=W0102
    resp = client.describe_tags(Filters=filters)
    tags = resp["Tags"]
    token = resp.get("NextToken")
    while token:
        resp = client.describe_tags(Filters=filters, NextToken=token)
        tags.extend(resp["Tags"])
        token = resp.get("Token")
    return tags
