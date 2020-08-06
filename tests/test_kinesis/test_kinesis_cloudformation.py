import boto3
import sure  # noqa

from moto import mock_kinesis, mock_cloudformation


@mock_cloudformation
def test_kinesis_cloudformation_create_stream():
    cf_conn = boto3.client("cloudformation", region_name="us-east-1")

    stack_name = "MyStack"

    template = '{"Resources":{"MyStream":{"Type":"AWS::Kinesis::Stream"}}}'

    cf_conn.create_stack(StackName=stack_name, TemplateBody=template)

    provisioned_resource = cf_conn.list_stack_resources(StackName=stack_name)[
        "StackResourceSummaries"
    ][0]
    provisioned_resource["LogicalResourceId"].should.equal("MyStream")
    len(provisioned_resource["PhysicalResourceId"]).should.be.greater_than(0)


@mock_cloudformation
@mock_kinesis
def test_kinesis_cloudformation_get_attr():
    cf_conn = boto3.client("cloudformation", region_name="us-east-1")

    stack_name = "MyStack"

    template = """
Resources:
  TheStream:
    Type: AWS::Kinesis::Stream
Outputs:
  StreamName:
    Value: !Ref TheStream
  StreamArn:
    Value: !GetAtt TheStream.Arn
""".strip()

    cf_conn.create_stack(StackName=stack_name, TemplateBody=template)
    stack_description = cf_conn.describe_stacks(StackName=stack_name)["Stacks"][0]
    output_stream_name = [
        output["OutputValue"]
        for output in stack_description["Outputs"]
        if output["OutputKey"] == "StreamName"
    ][0]
    output_stream_arn = [
        output["OutputValue"]
        for output in stack_description["Outputs"]
        if output["OutputKey"] == "StreamArn"
    ][0]

    kinesis_conn = boto3.client("kinesis", region_name="us-east-1")
    stream_description = kinesis_conn.describe_stream(StreamName=output_stream_name)[
        "StreamDescription"
    ]
    output_stream_arn.should.equal(stream_description["StreamARN"])


@mock_cloudformation
@mock_kinesis
def test_kinesis_cloudformation_update():
    cf_conn = boto3.client("cloudformation", region_name="us-east-1")

    stack_name = "MyStack"

    template = """
Resources:
  TheStream:
    Type: AWS::Kinesis::Stream
    Properties:
      Name: MyStream
      ShardCount: 4
      RetentionPeriodHours: 48
      Tags:
      - Key: TagKey1
        Value: TagValue1
      - Key: TagKey2
        Value: TagValue2
""".strip()

    cf_conn.create_stack(StackName=stack_name, TemplateBody=template)
    stack_description = cf_conn.describe_stacks(StackName=stack_name)["Stacks"][0]
    stack_description["StackName"].should.equal(stack_name)

    kinesis_conn = boto3.client("kinesis", region_name="us-east-1")
    stream_description = kinesis_conn.describe_stream(StreamName="MyStream")[
        "StreamDescription"
    ]
    stream_description["RetentionPeriodHours"].should.equal(48)

    tags = kinesis_conn.list_tags_for_stream(StreamName="MyStream")["Tags"]
    tag1_value = [tag for tag in tags if tag["Key"] == "TagKey1"][0]["Value"]
    tag2_value = [tag for tag in tags if tag["Key"] == "TagKey2"][0]["Value"]
    tag1_value.should.equal("TagValue1")
    tag2_value.should.equal("TagValue2")

    shards_provisioned = len(
        [
            shard
            for shard in stream_description["Shards"]
            if "EndingSequenceNumber" not in shard["SequenceNumberRange"]
        ]
    )
    shards_provisioned.should.equal(4)

    template = """
    Resources:
      TheStream:
        Type: AWS::Kinesis::Stream
        Properties:
          ShardCount: 6
          RetentionPeriodHours: 24
          Tags:
          - Key: TagKey1
            Value: TagValue1a
          - Key: TagKey2
            Value: TagValue2a

    """.strip()
    cf_conn.update_stack(StackName=stack_name, TemplateBody=template)

    stream_description = kinesis_conn.describe_stream(StreamName="MyStream")[
        "StreamDescription"
    ]
    stream_description["RetentionPeriodHours"].should.equal(24)

    tags = kinesis_conn.list_tags_for_stream(StreamName="MyStream")["Tags"]
    tag1_value = [tag for tag in tags if tag["Key"] == "TagKey1"][0]["Value"]
    tag2_value = [tag for tag in tags if tag["Key"] == "TagKey2"][0]["Value"]
    tag1_value.should.equal("TagValue1a")
    tag2_value.should.equal("TagValue2a")

    shards_provisioned = len(
        [
            shard
            for shard in stream_description["Shards"]
            if "EndingSequenceNumber" not in shard["SequenceNumberRange"]
        ]
    )
    shards_provisioned.should.equal(6)


@mock_cloudformation
@mock_kinesis
def test_kinesis_cloudformation_delete():
    cf_conn = boto3.client("cloudformation", region_name="us-east-1")

    stack_name = "MyStack"

    template = """
Resources:
  TheStream:
    Type: AWS::Kinesis::Stream
    Properties:
      Name: MyStream
""".strip()

    cf_conn.create_stack(StackName=stack_name, TemplateBody=template)
    stack_description = cf_conn.describe_stacks(StackName=stack_name)["Stacks"][0]
    stack_description["StackName"].should.equal(stack_name)

    kinesis_conn = boto3.client("kinesis", region_name="us-east-1")
    stream_description = kinesis_conn.describe_stream(StreamName="MyStream")[
        "StreamDescription"
    ]
    stream_description["StreamName"].should.equal("MyStream")

    cf_conn.delete_stack(StackName=stack_name)
    streams = kinesis_conn.list_streams()["StreamNames"]
    len(streams).should.equal(0)
