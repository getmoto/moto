import boto3
import os
from functools import wraps
from moto import mock_glue, mock_lakeformation, mock_s3, mock_sts
from uuid import uuid4


def lakeformation_aws_verified(func):
    """
    Function that is verified to work against AWS.
    Can be run against AWS at any time by setting:
      MOTO_TEST_ALLOW_AWS_REQUEST=true

    If this environment variable is not set, the function runs in a `mock_lakeformation`/`mock_sts`/`mock_s3` context.

    Note that LakeFormation is not enabled by default - visit the AWS Console to permit access to the user who executes these tests.
    """

    @wraps(func)
    def pagination_wrapper():
        glue = boto3.client("glue", region_name="eu-west-2")
        lf = boto3.client("lakeformation", region_name="eu-west-2")
        s3 = boto3.client("s3", region_name="us-east-1")
        bucket_name = str(uuid4())

        allow_aws_request = (
            os.environ.get("MOTO_TEST_ALLOW_AWS_REQUEST", "false").lower() == "true"
        )

        if allow_aws_request:
            resp = create_glue_infra_and_test(bucket_name, s3, glue, lf)
        else:
            with mock_glue(), mock_lakeformation(), mock_s3(), mock_sts():
                resp = create_glue_infra_and_test(bucket_name, s3, glue, lf)
        return resp

    def create_glue_infra_and_test(bucket_name, s3, glue, lf):
        s3.create_bucket(Bucket=bucket_name)
        s3.put_bucket_tagging(
            Bucket=bucket_name,
            Tagging={"TagSet": [{"Key": "environment", "Value": "moto_tests"}]},
        )
        lf.register_resource(
            ResourceArn=f"arn:aws:s3:::{bucket_name}", UseServiceLinkedRole=True
        )

        db_name = str(uuid4())[0:6]
        table_name = str(uuid4())[0:6]
        column_name = str(uuid4())[0:6]
        glue.create_database(
            DatabaseInput={"Name": db_name}, Tags={"environment": "moto_tests"}
        )
        glue.create_table(
            DatabaseName=db_name,
            TableInput={
                "Name": table_name,
                "StorageDescriptor": {
                    "Columns": [{"Name": column_name, "Type": "string"}]
                },
            },
        )

        try:
            resp = func(bucket_name, db_name, table_name, column_name)
        finally:
            ### CLEANUP ###

            glue.delete_table(DatabaseName=db_name, Name=table_name)
            glue.delete_database(Name=db_name)

            lf.deregister_resource(ResourceArn=f"arn:aws:s3:::{bucket_name}")

            versions = s3.list_object_versions(Bucket=bucket_name).get("Versions", [])
            for key in versions:
                s3.delete_object(
                    Bucket=bucket_name, Key=key["Key"], VersionId=key.get("VersionId")
                )
            delete_markers = s3.list_object_versions(Bucket=bucket_name).get(
                "DeleteMarkers", []
            )
            for key in delete_markers:
                s3.delete_object(
                    Bucket=bucket_name, Key=key["Key"], VersionId=key.get("VersionId")
                )
            s3.delete_bucket(Bucket=bucket_name)

        return resp

    return pagination_wrapper
