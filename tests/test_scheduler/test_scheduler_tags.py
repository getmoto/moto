import boto3

from moto import mock_scheduler


@mock_scheduler
def test_schedule_tags():
    client = boto3.client("scheduler", "us-east-1")
    arn = client.create_schedule(
        Name="my-schedule",
        ScheduleExpression="some cron",
        FlexibleTimeWindow={
            "MaximumWindowInMinutes": 4,
            "Mode": "OFF",
        },
        Target={
            "Arn": "not supported yet",
            "RoleArn": "n/a",
        },
    )["ScheduleArn"]

    resp = client.list_tags_for_resource(ResourceArn=arn)
    assert resp["Tags"] == []

    client.tag_resource(
        ResourceArn=arn,
        Tags=[{"Key": "k1", "Value": "v1"}, {"Key": "k2", "Value": "v2"}],
    )

    resp = client.list_tags_for_resource(ResourceArn=arn)
    assert resp["Tags"] == [{"Key": "k1", "Value": "v1"}, {"Key": "k2", "Value": "v2"}]

    client.untag_resource(ResourceArn=arn, TagKeys=["k1"])

    resp = client.list_tags_for_resource(ResourceArn=arn)
    assert resp["Tags"] == [{"Key": "k2", "Value": "v2"}]


@mock_scheduler
def test_schedule_group_tags():
    client = boto3.client("scheduler", "us-east-1")
    arn = client.create_schedule_group(
        Name="my-schedule", Tags=[{"Key": "k1", "Value": "v1"}]
    )["ScheduleGroupArn"]

    resp = client.list_tags_for_resource(ResourceArn=arn)
    assert resp["Tags"] == [{"Key": "k1", "Value": "v1"}]

    client.tag_resource(ResourceArn=arn, Tags=[{"Key": "k2", "Value": "v2"}])

    resp = client.list_tags_for_resource(ResourceArn=arn)
    assert resp["Tags"] == [{"Key": "k1", "Value": "v1"}, {"Key": "k2", "Value": "v2"}]

    client.untag_resource(ResourceArn=arn, TagKeys=["k1"])

    resp = client.list_tags_for_resource(ResourceArn=arn)
    assert resp["Tags"] == [{"Key": "k2", "Value": "v2"}]
