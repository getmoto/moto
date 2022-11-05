import boto3
import sure  # noqa # pylint: disable=unused-import
import pytest

from botocore.exceptions import ClientError
from moto import mock_ec2

from tests import EXAMPLE_AMI_ID
from .test_instances import retrieve_all_instances
from uuid import uuid4


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


@mock_ec2
def test_get_all_tags_with_special_characters():
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


@mock_ec2
def test_create_tags():
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


@mock_ec2
def test_tag_limit_exceeded():
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


@mock_ec2
def test_invalid_id():
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


@mock_ec2
def test_get_all_tags_resource_filter():
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    client = boto3.client("ec2", region_name="us-east-1")
    instance = ec2.create_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)[0]
    inst_tag_key = str(uuid4())[0:6]
    client.create_tags(
        Resources=[instance.id], Tags=[{"Key": inst_tag_key, "Value": "some value"}]
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


@mock_ec2
def test_get_all_tags_value_filter():
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


@mock_ec2
def test_retrieved_instances_must_contain_their_tags():
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


@mock_ec2
def test_retrieved_volumes_must_contain_their_tags():
    tag_key = "Tag name"
    tag_value = "Tag value"
    tags_to_be_set = {"Key": tag_key, "Value": tag_value}

    ec2 = boto3.resource("ec2", region_name="eu-west-1")
    client = boto3.client("ec2", region_name="eu-west-1")
    volume = ec2.create_volume(Size=80, AvailabilityZone="us-east-1a")
    volume.tags.should.equal(None)

    client.create_tags(Resources=[volume.id], Tags=[tags_to_be_set])

    volume.reload()
    volume.tags.should.equal([{"Key": tag_key, "Value": tag_value}])


@mock_ec2
def test_retrieved_snapshots_must_contain_their_tags():
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


@mock_ec2
def test_filter_instances_by_wildcard_tags():
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
def test_create_volume_without_tags():
    client = boto3.client("ec2", "us-east-1")
    with pytest.raises(ClientError) as exc:
        client.create_volume(
            AvailabilityZone="us-east-1a",
            Encrypted=False,
            Size=40,
            TagSpecifications=[
                {
                    "ResourceType": "volume",
                    "Tags": [],
                }
            ],
        )
    err = exc.value.response["Error"]
    err["Code"].should.equal("InvalidParameterValue")
    err["Message"].should.equal("Tag specification must have at least one tag")


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
