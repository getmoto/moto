import pytest

import boto3
from botocore.exceptions import ClientError
import sure  # noqa # pylint: disable=unused-import

from moto import mock_ec2, mock_iam
from tests import EXAMPLE_AMI_ID
from uuid import uuid4


def quick_instance_creation():
    conn_ec2 = boto3.resource("ec2", "us-east-1")
    test_instance = conn_ec2.create_instances(
        ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1
    )
    # We only need instance id for this tests
    return test_instance[0].id


def quick_instance_profile_creation(name):
    conn_iam = boto3.resource("iam", "us-east-1")
    test_instance_profile = conn_iam.create_instance_profile(
        InstanceProfileName=name, Path="/"
    )
    return test_instance_profile.arn, test_instance_profile.name


@mock_ec2
@mock_iam
def test_associate():
    client = boto3.client("ec2", region_name="us-east-1")
    instance_id = quick_instance_creation()
    instance_profile_arn, instance_profile_name = quick_instance_profile_creation(
        str(uuid4())
    )

    association = client.associate_iam_instance_profile(
        IamInstanceProfile={
            "Arn": instance_profile_arn,
            "Name": instance_profile_name,
        },
        InstanceId=instance_id,
    )
    association["IamInstanceProfileAssociation"]["InstanceId"].should.equal(instance_id)
    association["IamInstanceProfileAssociation"]["IamInstanceProfile"][
        "Arn"
    ].should.equal(instance_profile_arn)
    association["IamInstanceProfileAssociation"]["State"].should.equal("associating")


@mock_ec2
@mock_iam
def test_invalid_associate():
    client = boto3.client("ec2", region_name="us-east-1")
    instance_id = quick_instance_creation()
    instance_profile_arn, instance_profile_name = quick_instance_profile_creation(
        str(uuid4())
    )

    client.associate_iam_instance_profile(
        IamInstanceProfile={
            "Arn": instance_profile_arn,
            "Name": instance_profile_name,
        },
        InstanceId=instance_id,
    )

    # Duplicate
    with pytest.raises(ClientError) as ex:
        client.associate_iam_instance_profile(
            IamInstanceProfile={
                "Arn": instance_profile_arn,
                "Name": instance_profile_name,
            },
            InstanceId=instance_id,
        )
    ex.value.response["Error"]["Code"].should.equal("IncorrectState")
    ex.value.response["Error"]["Message"].should.contain(
        "There is an existing association for"
    )

    # Wrong instance profile
    with pytest.raises(ClientError) as ex:
        client.associate_iam_instance_profile(
            IamInstanceProfile={"Arn": "fake", "Name": "fake"}, InstanceId=instance_id,
        )
    ex.value.response["Error"]["Code"].should.equal("NoSuchEntity")
    ex.value.response["Error"]["Message"].should.contain("not found")

    # Wrong instance id
    with pytest.raises(ClientError) as ex:
        client.associate_iam_instance_profile(
            IamInstanceProfile={
                "Arn": instance_profile_arn,
                "Name": instance_profile_name,
            },
            InstanceId="fake",
        )
    ex.value.response["Error"]["Code"].should.equal("InvalidInstanceID.NotFound")
    ex.value.response["Error"]["Message"].should.contain("does not exist")


@mock_ec2
@mock_iam
def test_describe():
    client = boto3.client("ec2", region_name="us-east-1")

    instance_id1 = quick_instance_creation()
    instance_profile_arn1, instance_profile_name1 = quick_instance_profile_creation(
        str(uuid4())
    )
    client.associate_iam_instance_profile(
        IamInstanceProfile={
            "Arn": instance_profile_arn1,
            "Name": instance_profile_name1,
        },
        InstanceId=instance_id1,
    )
    associations = client.describe_iam_instance_profile_associations()
    associations = associations["IamInstanceProfileAssociations"]
    [a["IamInstanceProfile"]["Arn"] for a in associations].should.contain(
        instance_profile_arn1
    )
    my_assoc = [
        a
        for a in associations
        if a["IamInstanceProfile"]["Arn"] == instance_profile_arn1
    ][0]
    my_assoc["InstanceId"].should.equal(instance_id1)
    my_assoc["State"].should.equal("associated")

    instance_id2 = quick_instance_creation()
    instance_profile_arn2, instance_profile_name2 = quick_instance_profile_creation(
        str(uuid4())
    )
    client.associate_iam_instance_profile(
        IamInstanceProfile={
            "Arn": instance_profile_arn2,
            "Name": instance_profile_name2,
        },
        InstanceId=instance_id2,
    )

    associations = client.describe_iam_instance_profile_associations()
    associations = associations["IamInstanceProfileAssociations"]
    [a["IamInstanceProfile"]["Arn"] for a in associations].should.contain(
        instance_profile_arn1
    )
    [a["IamInstanceProfile"]["Arn"] for a in associations].should.contain(
        instance_profile_arn2
    )
    my_assoc = [
        a
        for a in associations
        if a["IamInstanceProfile"]["Arn"] == instance_profile_arn1
    ][0]

    associations = client.describe_iam_instance_profile_associations(
        AssociationIds=[my_assoc["AssociationId"],]
    )
    associations["IamInstanceProfileAssociations"].should.have.length_of(1)
    associations["IamInstanceProfileAssociations"][0]["IamInstanceProfile"][
        "Arn"
    ].should.equal(my_assoc["IamInstanceProfile"]["Arn"])

    associations = client.describe_iam_instance_profile_associations(
        Filters=[
            {"Name": "instance-id", "Values": [my_assoc["InstanceId"],],},
            {"Name": "state", "Values": ["associated"]},
        ]
    )
    associations["IamInstanceProfileAssociations"].should.have.length_of(1)
    associations["IamInstanceProfileAssociations"][0]["IamInstanceProfile"][
        "Arn"
    ].should.equal(my_assoc["IamInstanceProfile"]["Arn"])


@mock_ec2
@mock_iam
def test_replace():
    client = boto3.client("ec2", region_name="us-east-1")
    instance_id1 = quick_instance_creation()
    instance_profile_arn1, instance_profile_name1 = quick_instance_profile_creation(
        str(uuid4())
    )
    instance_profile_arn2, instance_profile_name2 = quick_instance_profile_creation(
        str(uuid4())
    )

    association = client.associate_iam_instance_profile(
        IamInstanceProfile={
            "Arn": instance_profile_arn1,
            "Name": instance_profile_name1,
        },
        InstanceId=instance_id1,
    )

    association = client.replace_iam_instance_profile_association(
        IamInstanceProfile={
            "Arn": instance_profile_arn2,
            "Name": instance_profile_name2,
        },
        AssociationId=association["IamInstanceProfileAssociation"]["AssociationId"],
    )

    association["IamInstanceProfileAssociation"]["IamInstanceProfile"][
        "Arn"
    ].should.equal(instance_profile_arn2)
    association["IamInstanceProfileAssociation"]["State"].should.equal("associating")


@mock_ec2
@mock_iam
def test_invalid_replace():
    client = boto3.client("ec2", region_name="us-east-1")
    instance_id = quick_instance_creation()
    instance_profile_arn, instance_profile_name = quick_instance_profile_creation(
        str(uuid4())
    )
    instance_profile_arn2, instance_profile_name2 = quick_instance_profile_creation(
        str(uuid4())
    )

    association = client.associate_iam_instance_profile(
        IamInstanceProfile={
            "Arn": instance_profile_arn,
            "Name": instance_profile_name,
        },
        InstanceId=instance_id,
    )

    # Wrong id
    with pytest.raises(ClientError) as ex:
        client.replace_iam_instance_profile_association(
            IamInstanceProfile={
                "Arn": instance_profile_arn2,
                "Name": instance_profile_name2,
            },
            AssociationId="fake",
        )
    ex.value.response["Error"]["Code"].should.equal("InvalidAssociationID.NotFound")
    ex.value.response["Error"]["Message"].should.contain("An invalid association-id of")

    # Wrong instance profile
    with pytest.raises(ClientError) as ex:
        client.replace_iam_instance_profile_association(
            IamInstanceProfile={"Arn": "fake", "Name": "fake",},
            AssociationId=association["IamInstanceProfileAssociation"]["AssociationId"],
        )
    ex.value.response["Error"]["Code"].should.equal("NoSuchEntity")
    ex.value.response["Error"]["Message"].should.contain("not found")


@mock_ec2
@mock_iam
def test_disassociate():
    client = boto3.client("ec2", region_name="us-east-1")
    instance_id = quick_instance_creation()
    instance_profile_arn, instance_profile_name = quick_instance_profile_creation(
        str(uuid4())
    )

    association = client.associate_iam_instance_profile(
        IamInstanceProfile={
            "Arn": instance_profile_arn,
            "Name": instance_profile_name,
        },
        InstanceId=instance_id,
    )

    associations = client.describe_iam_instance_profile_associations()
    associations = associations["IamInstanceProfileAssociations"]
    [a["IamInstanceProfile"]["Arn"] for a in associations].should.contain(
        instance_profile_arn
    )

    disassociation = client.disassociate_iam_instance_profile(
        AssociationId=association["IamInstanceProfileAssociation"]["AssociationId"],
    )

    disassociation["IamInstanceProfileAssociation"]["IamInstanceProfile"][
        "Arn"
    ].should.equal(instance_profile_arn)
    disassociation["IamInstanceProfileAssociation"]["State"].should.equal(
        "disassociating"
    )

    associations = client.describe_iam_instance_profile_associations()
    associations = associations["IamInstanceProfileAssociations"]
    [a["IamInstanceProfile"]["Arn"] for a in associations].shouldnt.contain(
        instance_profile_arn
    )


@mock_ec2
@mock_iam
def test_invalid_disassociate():
    client = boto3.client("ec2", region_name="us-east-1")

    # Wrong id
    with pytest.raises(ClientError) as ex:
        client.disassociate_iam_instance_profile(AssociationId="fake",)
    ex.value.response["Error"]["Code"].should.equal("InvalidAssociationID.NotFound")
    ex.value.response["Error"]["Message"].should.contain("An invalid association-id of")
