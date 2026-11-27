"""Tests against the AWS SDK for Python v4: https://github.com/aws/aws-sdk-python"""

from uuid import uuid4

import pytest

from moto import mock_aws

try:
    from aws_sdk_cloudtrail import CloudTrailClient, CloudTrailConfig
    from aws_sdk_cloudtrail.models import TrailNotFoundException
    from aws_sdk_s3 import S3Client, S3Config
except ImportError:  # Requires Python 3.12+
    pytest.skip(
        "aws-sdk-cloudtrail and aws-sdk-s3 are not installed", allow_module_level=True
    )


@pytest.mark.skip(
    reason="Every request returns an empty 404: the SDK sends 'X-Amz-Target: CloudTrail_20131101.<Operation>', "
    "but Moto's JSONRouter only recognizes botocore's targetPrefix 'com.amazonaws.cloudtrail.v20131101.CloudTrail_20131101'. "
    "Also, DescribeTrails always returns HasCustomEventSelectors=False, even after PutEventSelectors"
)
@mock_aws
def test_audit_trail_for_data_events():
    """Create an audit trail that records S3 data events, and toggle its logging."""
    suffix = str(uuid4())[:8]
    bucket = f"audit-logs-{suffix}"
    trail_name = f"audit-{suffix}"

    s3_config = S3Config.resolve(region="us-east-1")
    with S3Client(config=s3_config) as s3:
        s3.create_bucket(bucket=bucket)

    config = CloudTrailConfig.resolve(region="us-east-1")
    with CloudTrailClient(config=config) as client:
        trail = client.create_trail(
            name=trail_name,
            s3_bucket_name=bucket,
            s3_key_prefix="cloudtrail",
            is_multi_region_trail=True,
            enable_log_file_validation=True,
            tags_list=[{"key": "compliance", "value": "sox"}],
        )
        assert trail.name == trail_name
        assert trail.s3_bucket_name == bucket
        assert trail.is_multi_region_trail is True
        assert trail.log_file_validation_enabled is True

        assert client.get_trail_status(name=trail_name).is_logging is False
        client.start_logging(name=trail_name)
        assert client.get_trail_status(name=trail_name).is_logging is True

        client.put_event_selectors(
            trail_name=trail_name,
            event_selectors=[
                {
                    "read_write_type": "WriteOnly",
                    "include_management_events": True,
                    "data_resources": [
                        {
                            "type": "AWS::S3::Object",
                            "values": [f"arn:aws:s3:::{bucket}/"],
                        }
                    ],
                }
            ],
        )
        selectors = client.get_event_selectors(trail_name=trail_name)
        assert selectors.trail_arn == trail.trail_arn
        assert selectors.event_selectors[0].read_write_type == "WriteOnly"
        assert selectors.event_selectors[0].data_resources[0].values == [
            f"arn:aws:s3:::{bucket}/"
        ]

        described = client.describe_trails(trail_name_list=[trail_name])
        assert described.trail_list[0].has_custom_event_selectors is True

        tags = client.list_tags(resource_id_list=[trail.trail_arn])
        assert tags.resource_tag_list[0].tags_list[0].value == "sox"

        client.stop_logging(name=trail_name)
        assert client.get_trail_status(name=trail_name).is_logging is False

        client.delete_trail(name=trail_name)
        with pytest.raises(TrailNotFoundException):
            client.get_trail(name=trail_name)
