import sure  # noqa # pylint: disable=unused-import

from moto.logs.models import LogGroup


def test_log_group_to_describe_dict():
    # Given
    region = "us-east-1"
    name = "test-log-group"
    tags = {"TestTag": "TestValue"}
    kms_key_id = (
        "arn:aws:kms:us-east-1:000000000000:key/51d81fab-b138-4bd2-8a09-07fd6d37224d"
    )
    kwargs = dict(kmsKeyId=kms_key_id,)

    # When
    log_group = LogGroup(region, name, tags, **kwargs)
    describe_dict = log_group.to_describe_dict()

    # Then
    expected_dict = dict(logGroupName=name, kmsKeyId=kms_key_id)

    for attr, value in expected_dict.items():
        describe_dict.should.have.key(attr)
        describe_dict[attr].should.equal(value)
