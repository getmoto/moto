from __future__ import unicode_literals

# Ensure 'pytest.raises' context manager support for Python 2.6
import pytest

import boto3
from botocore.exceptions import ClientError
import sure  # noqa

from moto import mock_ec2, mock_iam


@mock_ec2
@mock_iam
def test_iam_instance_profile_associations():
    image_id = "ami-1234abcd"
    client = boto3.client("ec2", region_name="us-east-1")
    conn_ec2 = boto3.resource("ec2", "us-east-1")
    conn_iam = boto3.resource("iam", "us-east-1")
    test_instance = conn_ec2.create_instances(ImageId=image_id, MinCount=1, MaxCount=1)
    test_instance_profile = conn_iam.create_instance_profile(
        InstanceProfileName="test_profile", Path="/"
    )

    association = client.associate_iam_instance_profile(
        IamInstanceProfile={
            "Arn": test_instance_profile.arn,
            "Name": test_instance_profile.name,
        },
        InstanceId=test_instance[0].id,
    )

    association["IamInstanceProfileAssociation"]["InstanceId"].should.equal(
        test_instance[0].id
    )
    association["IamInstanceProfileAssociation"]["IamInstanceProfile"][
        "Arn"
    ].should.equal(test_instance_profile.arn)
    association["IamInstanceProfileAssociation"]["State"].should.equal("associating")

    # Describe
    test_instance = conn_ec2.create_instances(ImageId=image_id, MinCount=1, MaxCount=1)
    test_instance_profile = conn_iam.create_instance_profile(
        InstanceProfileName="test_profile2", Path="/"
    )

    associations = client.describe_iam_instance_profile_associations()

    associations["IamInstanceProfileAssociations"].should.have.length_of(1)

    second_association = client.associate_iam_instance_profile(
        IamInstanceProfile={
            "Arn": test_instance_profile.arn,
            "Name": test_instance_profile.name,
        },
        InstanceId=test_instance[0].id,
    )
    associations = client.describe_iam_instance_profile_associations()
    associations["IamInstanceProfileAssociations"].should.have.length_of(2)

    # Disassociate
    client.disassociate_iam_instance_profile(
        AssociationId=second_association["IamInstanceProfileAssociation"][
            "AssociationId"
        ]
    )
    associations = client.describe_iam_instance_profile_associations()
    associations["IamInstanceProfileAssociations"].should.have.length_of(1)

    # Re-associate
    new_instance_profile = conn_iam.create_instance_profile(
        InstanceProfileName="test_profile3", Path="/"
    )
    client.replace_iam_instance_profile_association(
        IamInstanceProfile={
            "Arn": new_instance_profile.arn,
            "Name": new_instance_profile.name,
        },
        AssociationId=associations["IamInstanceProfileAssociations"][0][
            "AssociationId"
        ],
    )
    # describe_iam_instance_profile_associations with filter test
    associations = client.describe_iam_instance_profile_associations(
        AssociationIds=[
            associations["IamInstanceProfileAssociations"][0]["AssociationId"],
        ]
    )
    associations["IamInstanceProfileAssociations"][0]["IamInstanceProfile"][
        "Arn"
    ].should.equal(new_instance_profile.arn)

    with pytest.raises(ClientError):
        client.associate_iam_instance_profile(
            IamInstanceProfile={"Arn": test_instance_profile.arn, "Name": "fake"},
            InstanceId=test_instance[0].id,
        )
