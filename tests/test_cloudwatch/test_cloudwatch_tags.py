from operator import itemgetter

import boto3
from botocore.exceptions import ClientError
import pytest
import sure  # noqa # pylint: disable=unused-import

from moto import mock_cloudwatch
from moto.cloudwatch.utils import make_arn_for_alarm
from moto.core import ACCOUNT_ID


@mock_cloudwatch
def test_list_tags_for_resource():
    # given
    client = boto3.client("cloudwatch", region_name="eu-central-1")
    alarm_name = "test-alarm"
    client.put_metric_alarm(
        AlarmName=alarm_name,
        AlarmDescription="test alarm",
        ActionsEnabled=True,
        MetricName="5XXError",
        Namespace="AWS/ApiGateway",
        Statistic="Sum",
        Dimensions=[
            {"Name": "ApiName", "Value": "test-api"},
            {"Name": "Stage", "Value": "default"},
        ],
        Period=60,
        Unit="Seconds",
        EvaluationPeriods=1,
        DatapointsToAlarm=1,
        Threshold=1.0,
        ComparisonOperator="GreaterThanOrEqualToThreshold",
        Tags=[{"Key": "key-1", "Value": "value-1"}],
    )
    arn = client.describe_alarms(AlarmNames=[alarm_name])["MetricAlarms"][0]["AlarmArn"]

    # when
    response = client.list_tags_for_resource(ResourceARN=arn)

    # then
    response["Tags"].should.equal([{"Key": "key-1", "Value": "value-1"}])


@mock_cloudwatch
def test_list_tags_for_resource_with_unknown_resource():
    # given
    region_name = "eu-central-1"
    client = boto3.client("cloudwatch", region_name=region_name)

    # when
    response = client.list_tags_for_resource(
        ResourceARN=make_arn_for_alarm(
            region=region_name, account_id=ACCOUNT_ID, alarm_name="unknown"
        )
    )

    # then
    response["Tags"].should.be.empty


@mock_cloudwatch
def test_tag_resource():
    # given
    client = boto3.client("cloudwatch", region_name="eu-central-1")
    alarm_name = "test-alarm"
    client.put_metric_alarm(
        AlarmName=alarm_name,
        AlarmDescription="test alarm",
        ActionsEnabled=True,
        MetricName="5XXError",
        Namespace="AWS/ApiGateway",
        Statistic="Sum",
        Dimensions=[
            {"Name": "ApiName", "Value": "test-api"},
            {"Name": "Stage", "Value": "default"},
        ],
        Period=60,
        Unit="Seconds",
        EvaluationPeriods=1,
        DatapointsToAlarm=1,
        Threshold=1.0,
        ComparisonOperator="GreaterThanOrEqualToThreshold",
        Tags=[{"Key": "key-1", "Value": "value-1"}],
    )
    arn = client.describe_alarms(AlarmNames=[alarm_name])["MetricAlarms"][0]["AlarmArn"]

    # when
    client.tag_resource(ResourceARN=arn, Tags=[{"Key": "key-2", "Value": "value-2"}])

    # then
    response = client.list_tags_for_resource(ResourceARN=arn)
    sorted(response["Tags"], key=itemgetter("Key")).should.equal(
        sorted(
            [
                {"Key": "key-1", "Value": "value-1"},
                {"Key": "key-2", "Value": "value-2"},
            ],
            key=itemgetter("Key"),
        )
    )


@mock_cloudwatch
def test_tag_resource_error_not_exists():
    # given
    region_name = "eu-central-1"
    client = boto3.client("cloudwatch", region_name=region_name)

    # when
    with pytest.raises(ClientError) as e:
        client.tag_resource(
            ResourceARN=make_arn_for_alarm(
                region=region_name, account_id=ACCOUNT_ID, alarm_name="unknown"
            ),
            Tags=[{"Key": "key-1", "Value": "value-1"},],
        )

    # then
    ex = e.value
    ex.operation_name.should.equal("TagResource")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(404)
    ex.response["Error"]["Code"].should.contain("ResourceNotFoundException")
    ex.response["Error"]["Message"].should.equal("Unknown")


@mock_cloudwatch
def test_untag_resource():
    # given
    client = boto3.client("cloudwatch", region_name="eu-central-1")
    alarm_name = "test-alarm"
    client.put_metric_alarm(
        AlarmName=alarm_name,
        AlarmDescription="test alarm",
        ActionsEnabled=True,
        MetricName="5XXError",
        Namespace="AWS/ApiGateway",
        Statistic="Sum",
        Dimensions=[
            {"Name": "ApiName", "Value": "test-api"},
            {"Name": "Stage", "Value": "default"},
        ],
        Period=60,
        Unit="Seconds",
        EvaluationPeriods=1,
        DatapointsToAlarm=1,
        Threshold=1.0,
        ComparisonOperator="GreaterThanOrEqualToThreshold",
        Tags=[
            {"Key": "key-1", "Value": "value-1"},
            {"Key": "key-2", "Value": "value-2"},
        ],
    )
    arn = client.describe_alarms(AlarmNames=[alarm_name])["MetricAlarms"][0]["AlarmArn"]

    # when
    client.untag_resource(ResourceARN=arn, TagKeys=["key-2"])

    # then
    response = client.list_tags_for_resource(ResourceARN=arn)
    response["Tags"].should.equal([{"Key": "key-1", "Value": "value-1"}])


@mock_cloudwatch
def test_untag_resource_error_not_exists():
    # given
    region_name = "eu-central-1"
    client = boto3.client("cloudwatch", region_name=region_name)

    # when
    with pytest.raises(ClientError) as e:
        client.untag_resource(
            ResourceARN=make_arn_for_alarm(
                region=region_name, account_id=ACCOUNT_ID, alarm_name="unknown"
            ),
            TagKeys=["key-1"],
        )

    # then
    ex = e.value
    ex.operation_name.should.equal("UntagResource")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(404)
    ex.response["Error"]["Code"].should.contain("ResourceNotFoundException")
    ex.response["Error"]["Message"].should.equal("Unknown")
