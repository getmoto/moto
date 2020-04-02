from __future__ import unicode_literals

import datetime

from botocore.exceptions import ClientError
import boto3
import sure  # noqa

from moto import mock_athena


@mock_athena
def test_create_work_group():
    client = boto3.client("athena", region_name="us-east-1")

    response = client.create_work_group(
        Name="athena_workgroup",
        Description="Test work group",
        Configuration={
            "ResultConfiguration": {
                "OutputLocation": "s3://bucket-name/prefix/",
                "EncryptionConfiguration": {
                    "EncryptionOption": "SSE_KMS",
                    "KmsKey": "aws:arn:kms:1233456789:us-east-1:key/number-1",
                },
            }
        },
        Tags=[],
    )

    try:
        # The second time should throw an error
        response = client.create_work_group(
            Name="athena_workgroup",
            Description="duplicate",
            Configuration={
                "ResultConfiguration": {
                    "OutputLocation": "s3://bucket-name/prefix/",
                    "EncryptionConfiguration": {
                        "EncryptionOption": "SSE_KMS",
                        "KmsKey": "aws:arn:kms:1233456789:us-east-1:key/number-1",
                    },
                }
            },
        )
    except ClientError as err:
        err.response["Error"]["Code"].should.equal("InvalidRequestException")
        err.response["Error"]["Message"].should.equal("WorkGroup already exists")
    else:
        raise RuntimeError("Should have raised ResourceNotFoundException")

    # Then test the work group appears in the work group list
    response = client.list_work_groups()

    response["WorkGroups"].should.have.length_of(1)
    work_group = response["WorkGroups"][0]
    work_group["Name"].should.equal("athena_workgroup")
    work_group["Description"].should.equal("Test work group")
    work_group["State"].should.equal("ENABLED")
