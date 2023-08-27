from moto.logs.models import LogGroup
from tests import DEFAULT_ACCOUNT_ID


def test_log_group_to_describe_dict():
    # Given
    region = "us-east-1"
    name = "test-log-group"
    kms_key_id = (
        "arn:aws:kms:us-east-1:000000000000:key/51d81fab-b138-4bd2-8a09-07fd6d37224d"
    )
    kwargs = dict(kmsKeyId=kms_key_id)

    # When
    log_group = LogGroup(DEFAULT_ACCOUNT_ID, region, name, **kwargs)
    describe_dict = log_group.to_describe_dict()

    # Then
    expected_dict = dict(logGroupName=name, kmsKeyId=kms_key_id)

    for attr, value in expected_dict.items():
        assert describe_dict[attr] == value
