import boto3
import pytest

from tests.test_s3 import s3_aws_verified


@s3_aws_verified
@pytest.mark.aws_verified
def test_list_tags_for_regular_bucket(account_id, bucket_name=None):
    s3control = boto3.client("s3control", "us-east-1")

    bucket_arn = f"arn:aws:s3:::{bucket_name}"
    existing_tags = s3control.list_tags_for_resource(
        AccountId=account_id, ResourceArn=bucket_arn
    )["Tags"]
    assert existing_tags == [{"Key": "environment", "Value": "moto_tests"}]

    s3control.tag_resource(
        AccountId=account_id,
        ResourceArn=bucket_arn,
        Tags=[{"Key": "tag1", "Value": "val"}],
    )

    new_tags = s3control.list_tags_for_resource(
        AccountId=account_id, ResourceArn=bucket_arn
    )["Tags"]
    assert len(new_tags) == 2
    assert {"Key": "tag1", "Value": "val"} in new_tags
    assert {"Key": "environment", "Value": "moto_tests"} in new_tags

    # Multiple tags at once
    s3control.tag_resource(
        AccountId=account_id,
        ResourceArn=bucket_arn,
        Tags=[{"Key": "tag2", "Value": "val"}, {"Key": "tag3", "Value": "val"}],
    )

    # Untag once
    s3control.untag_resource(
        AccountId=account_id, ResourceArn=bucket_arn, TagKeys=["tag1"]
    )

    updated_tags = s3control.list_tags_for_resource(
        AccountId=account_id, ResourceArn=bucket_arn
    )["Tags"]
    assert len(updated_tags) == 3
    assert {"Key": "tag1", "Value": "val"} not in updated_tags

    # Untag multiple
    s3control.untag_resource(
        AccountId=account_id, ResourceArn=bucket_arn, TagKeys=["tag2", "tag3"]
    )

    original_tags = s3control.list_tags_for_resource(
        AccountId=account_id, ResourceArn=bucket_arn
    )["Tags"]
    assert original_tags == [{"Key": "environment", "Value": "moto_tests"}]
