import boto3
import json
import pytest

import sure  # noqa # pylint: disable=unused-import

from botocore.exceptions import ClientError
from moto import mock_sns
from moto.sns.models import DEFAULT_EFFECTIVE_DELIVERY_POLICY, DEFAULT_PAGE_SIZE
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID


@mock_sns
def test_create_and_delete_topic():
    conn = boto3.client("sns", region_name="us-east-1")
    for topic_name in ("some-topic", "-some-topic-", "_some-topic_", "a" * 256):
        conn.create_topic(Name=topic_name)

        topics_json = conn.list_topics()
        topics = topics_json["Topics"]
        topics.should.have.length_of(1)
        topics[0]["TopicArn"].should.equal(
            f"arn:aws:sns:{conn._client_config.region_name}:{ACCOUNT_ID}:{topic_name}"
        )

        # Delete the topic
        conn.delete_topic(TopicArn=topics[0]["TopicArn"])

        # Ensure DeleteTopic is idempotent
        conn.delete_topic(TopicArn=topics[0]["TopicArn"])

        # And there should now be 0 topics
        topics_json = conn.list_topics()
        topics = topics_json["Topics"]
        topics.should.have.length_of(0)


@mock_sns
def test_delete_non_existent_topic():
    conn = boto3.client("sns", region_name="us-east-1")

    # Ensure DeleteTopic does not throw an error for non-existent topics
    conn.delete_topic(
        TopicArn="arn:aws:sns:us-east-1:123456789012:this-topic-does-not-exist"
    )


@mock_sns
def test_create_topic_with_attributes():
    conn = boto3.client("sns", region_name="us-east-1")
    conn.create_topic(
        Name="some-topic-with-attribute", Attributes={"DisplayName": "test-topic"}
    )
    topics_json = conn.list_topics()
    topic_arn = topics_json["Topics"][0]["TopicArn"]

    attributes = conn.get_topic_attributes(TopicArn=topic_arn)["Attributes"]
    attributes["DisplayName"].should.equal("test-topic")


@mock_sns
def test_create_topic_with_tags():
    conn = boto3.client("sns", region_name="us-east-1")
    response = conn.create_topic(
        Name="some-topic-with-tags",
        Tags=[
            {"Key": "tag_key_1", "Value": "tag_value_1"},
            {"Key": "tag_key_2", "Value": "tag_value_2"},
        ],
    )
    topic_arn = response["TopicArn"]

    conn.list_tags_for_resource(ResourceArn=topic_arn)["Tags"].should.equal(
        [
            {"Key": "tag_key_1", "Value": "tag_value_1"},
            {"Key": "tag_key_2", "Value": "tag_value_2"},
        ]
    )


@mock_sns
def test_create_topic_should_be_indempodent():
    conn = boto3.client("sns", region_name="us-east-1")
    topic_arn = conn.create_topic(Name="some-topic")["TopicArn"]
    conn.set_topic_attributes(
        TopicArn=topic_arn, AttributeName="DisplayName", AttributeValue="should_be_set"
    )
    topic_display_name = conn.get_topic_attributes(TopicArn=topic_arn)["Attributes"][
        "DisplayName"
    ]
    topic_display_name.should.be.equal("should_be_set")

    # recreate topic to prove indempodentcy
    topic_arn = conn.create_topic(Name="some-topic")["TopicArn"]
    topic_display_name = conn.get_topic_attributes(TopicArn=topic_arn)["Attributes"][
        "DisplayName"
    ]
    topic_display_name.should.be.equal("should_be_set")


@mock_sns
def test_get_missing_topic():
    conn = boto3.client("sns", region_name="us-east-1")
    conn.get_topic_attributes.when.called_with(
        TopicArn="arn:aws:sns:us-east-1:424242424242:a-fake-arn"
    ).should.throw(ClientError)


@mock_sns
def test_create_topic_must_meet_constraints():
    conn = boto3.client("sns", region_name="us-east-1")
    common_random_chars = [":", ";", "!", "@", "|", "^", "%"]
    for char in common_random_chars:
        conn.create_topic.when.called_with(Name=f"no{char}_invalidchar").should.throw(
            ClientError
        )
    conn.create_topic.when.called_with(Name="no spaces allowed").should.throw(
        ClientError
    )


@mock_sns
def test_create_topic_should_be_of_certain_length():
    conn = boto3.client("sns", region_name="us-east-1")
    too_short = ""
    conn.create_topic.when.called_with(Name=too_short).should.throw(ClientError)
    too_long = "x" * 257
    conn.create_topic.when.called_with(Name=too_long).should.throw(ClientError)


@mock_sns
def test_create_topic_in_multiple_regions():
    for region in ["us-west-1", "us-west-2"]:
        conn = boto3.client("sns", region_name=region)
        topic_arn = conn.create_topic(Name="some-topic")["TopicArn"]
        # We can find the topic
        list(conn.list_topics()["Topics"]).should.have.length_of(1)

        # We can read the Topic details
        topic = boto3.resource("sns", region_name=region).Topic(topic_arn)
        topic.load()

    # Topic does not exist in different region though
    with pytest.raises(ClientError) as exc:
        sns_resource = boto3.resource("sns", region_name="eu-north-1")
        topic = sns_resource.Topic(topic_arn)
        topic.load()
    err = exc.value.response["Error"]
    assert err["Code"] == "NotFound"
    assert err["Message"] == "Topic does not exist"
    assert err["Type"] == "Sender"


@mock_sns
def test_topic_corresponds_to_region():
    for region in ["us-east-1", "us-west-2"]:
        conn = boto3.client("sns", region_name=region)
        conn.create_topic(Name="some-topic")
        topics_json = conn.list_topics()
        topic_arn = topics_json["Topics"][0]["TopicArn"]
        topic_arn.should.equal(f"arn:aws:sns:{region}:{ACCOUNT_ID}:some-topic")


@mock_sns
def test_topic_attributes():
    conn = boto3.client("sns", region_name="us-east-1")
    conn.create_topic(Name="some-topic")

    topics_json = conn.list_topics()
    topic_arn = topics_json["Topics"][0]["TopicArn"]

    attributes = conn.get_topic_attributes(TopicArn=topic_arn)["Attributes"]
    attributes["TopicArn"].should.equal(
        f"arn:aws:sns:{conn._client_config.region_name}:{ACCOUNT_ID}:some-topic"
    )
    attributes["Owner"].should.equal(ACCOUNT_ID)
    json.loads(attributes["Policy"]).should.equal(
        {
            "Version": "2008-10-17",
            "Id": "__default_policy_ID",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Sid": "__default_statement_ID",
                    "Principal": {"AWS": "*"},
                    "Action": [
                        "SNS:GetTopicAttributes",
                        "SNS:SetTopicAttributes",
                        "SNS:AddPermission",
                        "SNS:RemovePermission",
                        "SNS:DeleteTopic",
                        "SNS:Subscribe",
                        "SNS:ListSubscriptionsByTopic",
                        "SNS:Publish",
                        "SNS:Receive",
                    ],
                    "Resource": f"arn:aws:sns:us-east-1:{ACCOUNT_ID}:some-topic",
                    "Condition": {"StringEquals": {"AWS:SourceOwner": ACCOUNT_ID}},
                }
            ],
        }
    )
    attributes["DisplayName"].should.equal("")
    attributes["SubscriptionsPending"].should.equal("0")
    attributes["SubscriptionsConfirmed"].should.equal("0")
    attributes["SubscriptionsDeleted"].should.equal("0")
    attributes["DeliveryPolicy"].should.equal("")
    json.loads(attributes["EffectiveDeliveryPolicy"]).should.equal(
        DEFAULT_EFFECTIVE_DELIVERY_POLICY
    )

    # boto can't handle prefix-mandatory strings:
    # i.e. unicode on Python 2 -- u"foobar"
    # and bytes on Python 3 -- b"foobar"
    policy = json.dumps({"foo": "bar"})
    displayname = "My display name"
    delivery = json.dumps({"http": {"defaultHealthyRetryPolicy": {"numRetries": 5}}})
    conn.set_topic_attributes(
        TopicArn=topic_arn, AttributeName="Policy", AttributeValue=policy
    )
    conn.set_topic_attributes(
        TopicArn=topic_arn, AttributeName="DisplayName", AttributeValue=displayname
    )
    conn.set_topic_attributes(
        TopicArn=topic_arn, AttributeName="DeliveryPolicy", AttributeValue=delivery
    )

    attributes = conn.get_topic_attributes(TopicArn=topic_arn)["Attributes"]
    attributes["Policy"].should.equal('{"foo":"bar"}')
    attributes["DisplayName"].should.equal("My display name")
    attributes["DeliveryPolicy"].should.equal(
        '{"http": {"defaultHealthyRetryPolicy": {"numRetries": 5}}}'
    )


@mock_sns
def test_topic_paging():
    conn = boto3.client("sns", region_name="us-east-1")
    for index in range(DEFAULT_PAGE_SIZE + int(DEFAULT_PAGE_SIZE / 2)):
        conn.create_topic(Name="some-topic_" + str(index))

    response = conn.list_topics()
    topics_list = response["Topics"]
    next_token = response["NextToken"]

    len(topics_list).should.equal(DEFAULT_PAGE_SIZE)
    int(next_token).should.equal(DEFAULT_PAGE_SIZE)

    response = conn.list_topics(NextToken=next_token)
    topics_list = response["Topics"]
    response.shouldnt.have("NextToken")

    topics_list.should.have.length_of(int(DEFAULT_PAGE_SIZE / 2))


@mock_sns
def test_add_remove_permissions():
    client = boto3.client("sns", region_name="us-east-1")
    topic_arn = client.create_topic(Name="test-permissions")["TopicArn"]

    client.add_permission(
        TopicArn=topic_arn,
        Label="test",
        AWSAccountId=["999999999999"],
        ActionName=["Publish"],
    )

    response = client.get_topic_attributes(TopicArn=topic_arn)
    json.loads(response["Attributes"]["Policy"]).should.equal(
        {
            "Version": "2008-10-17",
            "Id": "__default_policy_ID",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Sid": "__default_statement_ID",
                    "Principal": {"AWS": "*"},
                    "Action": [
                        "SNS:GetTopicAttributes",
                        "SNS:SetTopicAttributes",
                        "SNS:AddPermission",
                        "SNS:RemovePermission",
                        "SNS:DeleteTopic",
                        "SNS:Subscribe",
                        "SNS:ListSubscriptionsByTopic",
                        "SNS:Publish",
                        "SNS:Receive",
                    ],
                    "Resource": f"arn:aws:sns:us-east-1:{ACCOUNT_ID}:test-permissions",
                    "Condition": {"StringEquals": {"AWS:SourceOwner": ACCOUNT_ID}},
                },
                {
                    "Sid": "test",
                    "Effect": "Allow",
                    "Principal": {"AWS": "arn:aws:iam::999999999999:root"},
                    "Action": "SNS:Publish",
                    "Resource": f"arn:aws:sns:us-east-1:{ACCOUNT_ID}:test-permissions",
                },
            ],
        }
    )

    client.remove_permission(TopicArn=topic_arn, Label="test")

    response = client.get_topic_attributes(TopicArn=topic_arn)
    json.loads(response["Attributes"]["Policy"]).should.equal(
        {
            "Version": "2008-10-17",
            "Id": "__default_policy_ID",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Sid": "__default_statement_ID",
                    "Principal": {"AWS": "*"},
                    "Action": [
                        "SNS:GetTopicAttributes",
                        "SNS:SetTopicAttributes",
                        "SNS:AddPermission",
                        "SNS:RemovePermission",
                        "SNS:DeleteTopic",
                        "SNS:Subscribe",
                        "SNS:ListSubscriptionsByTopic",
                        "SNS:Publish",
                        "SNS:Receive",
                    ],
                    "Resource": f"arn:aws:sns:us-east-1:{ACCOUNT_ID}:test-permissions",
                    "Condition": {"StringEquals": {"AWS:SourceOwner": ACCOUNT_ID}},
                }
            ],
        }
    )

    client.add_permission(
        TopicArn=topic_arn,
        Label="test",
        AWSAccountId=["888888888888", "999999999999"],
        ActionName=["Publish", "Subscribe"],
    )

    response = client.get_topic_attributes(TopicArn=topic_arn)
    json.loads(response["Attributes"]["Policy"])["Statement"][1].should.equal(
        {
            "Sid": "test",
            "Effect": "Allow",
            "Principal": {
                "AWS": [
                    "arn:aws:iam::888888888888:root",
                    "arn:aws:iam::999999999999:root",
                ]
            },
            "Action": ["SNS:Publish", "SNS:Subscribe"],
            "Resource": f"arn:aws:sns:us-east-1:{ACCOUNT_ID}:test-permissions",
        }
    )

    # deleting non existing permission should be successful
    client.remove_permission(TopicArn=topic_arn, Label="non-existing")


@mock_sns
def test_add_permission_errors():
    client = boto3.client("sns", region_name="us-east-1")
    topic_arn = client.create_topic(Name="test-permissions")["TopicArn"]
    client.add_permission(
        TopicArn=topic_arn,
        Label="test",
        AWSAccountId=["999999999999"],
        ActionName=["Publish"],
    )

    client.add_permission.when.called_with(
        TopicArn=topic_arn,
        Label="test",
        AWSAccountId=["999999999999"],
        ActionName=["AddPermission"],
    ).should.throw(ClientError, "Statement already exists")

    client.add_permission.when.called_with(
        TopicArn=topic_arn + "-not-existing",
        Label="test-2",
        AWSAccountId=["999999999999"],
        ActionName=["AddPermission"],
    ).should.throw(
        ClientError,
        "An error occurred (NotFound) when calling the AddPermission operation: Topic does not exist",
    )

    client.add_permission.when.called_with(
        TopicArn=topic_arn,
        Label="test-2",
        AWSAccountId=["999999999999"],
        ActionName=["NotExistingAction"],
    ).should.throw(ClientError, "Policy statement action out of service scope!")


@mock_sns
def test_remove_permission_errors():
    client = boto3.client("sns", region_name="us-east-1")
    topic_arn = client.create_topic(Name="test-permissions")["TopicArn"]
    client.add_permission(
        TopicArn=topic_arn,
        Label="test",
        AWSAccountId=["999999999999"],
        ActionName=["Publish"],
    )

    client.remove_permission.when.called_with(
        TopicArn=topic_arn + "-not-existing", Label="test"
    ).should.throw(
        ClientError,
        "An error occurred (NotFound) when calling the RemovePermission operation: Topic does not exist",
    )


@mock_sns
def test_tag_topic():
    conn = boto3.client("sns", region_name="us-east-1")
    response = conn.create_topic(Name="some-topic-with-tags")
    topic_arn = response["TopicArn"]

    conn.tag_resource(
        ResourceArn=topic_arn, Tags=[{"Key": "tag_key_1", "Value": "tag_value_1"}]
    )
    conn.list_tags_for_resource(ResourceArn=topic_arn)["Tags"].should.equal(
        [{"Key": "tag_key_1", "Value": "tag_value_1"}]
    )

    conn.tag_resource(
        ResourceArn=topic_arn, Tags=[{"Key": "tag_key_2", "Value": "tag_value_2"}]
    )
    conn.list_tags_for_resource(ResourceArn=topic_arn)["Tags"].should.equal(
        [
            {"Key": "tag_key_1", "Value": "tag_value_1"},
            {"Key": "tag_key_2", "Value": "tag_value_2"},
        ]
    )

    conn.tag_resource(
        ResourceArn=topic_arn, Tags=[{"Key": "tag_key_1", "Value": "tag_value_X"}]
    )
    conn.list_tags_for_resource(ResourceArn=topic_arn)["Tags"].should.equal(
        [
            {"Key": "tag_key_1", "Value": "tag_value_X"},
            {"Key": "tag_key_2", "Value": "tag_value_2"},
        ]
    )


@mock_sns
def test_untag_topic():
    conn = boto3.client("sns", region_name="us-east-1")
    response = conn.create_topic(
        Name="some-topic-with-tags",
        Tags=[
            {"Key": "tag_key_1", "Value": "tag_value_1"},
            {"Key": "tag_key_2", "Value": "tag_value_2"},
        ],
    )
    topic_arn = response["TopicArn"]

    conn.untag_resource(ResourceArn=topic_arn, TagKeys=["tag_key_1"])
    conn.list_tags_for_resource(ResourceArn=topic_arn)["Tags"].should.equal(
        [{"Key": "tag_key_2", "Value": "tag_value_2"}]
    )

    # removing a non existing tag should not raise any error
    conn.untag_resource(ResourceArn=topic_arn, TagKeys=["not-existing-tag"])
    conn.list_tags_for_resource(ResourceArn=topic_arn)["Tags"].should.equal(
        [{"Key": "tag_key_2", "Value": "tag_value_2"}]
    )


@mock_sns
def test_list_tags_for_resource_error():
    conn = boto3.client("sns", region_name="us-east-1")
    conn.create_topic(
        Name="some-topic-with-tags", Tags=[{"Key": "tag_key_1", "Value": "tag_value_X"}]
    )

    conn.list_tags_for_resource.when.called_with(
        ResourceArn="not-existing-topic"
    ).should.throw(ClientError, "Resource does not exist")


@mock_sns
def test_tag_resource_errors():
    conn = boto3.client("sns", region_name="us-east-1")
    response = conn.create_topic(
        Name="some-topic-with-tags", Tags=[{"Key": "tag_key_1", "Value": "tag_value_X"}]
    )
    topic_arn = response["TopicArn"]

    conn.tag_resource.when.called_with(
        ResourceArn="not-existing-topic",
        Tags=[{"Key": "tag_key_1", "Value": "tag_value_1"}],
    ).should.throw(ClientError, "Resource does not exist")

    too_many_tags = [
        {"Key": f"tag_key_{i}", "Value": f"tag_value_{i}"} for i in range(51)
    ]
    conn.tag_resource.when.called_with(
        ResourceArn=topic_arn, Tags=too_many_tags
    ).should.throw(
        ClientError, "Could not complete request: tag quota of per resource exceeded"
    )

    # when the request fails, the tags should not be updated
    conn.list_tags_for_resource(ResourceArn=topic_arn)["Tags"].should.equal(
        [{"Key": "tag_key_1", "Value": "tag_value_X"}]
    )


@mock_sns
def test_untag_resource_error():
    conn = boto3.client("sns", region_name="us-east-1")
    conn.create_topic(
        Name="some-topic-with-tags", Tags=[{"Key": "tag_key_1", "Value": "tag_value_X"}]
    )

    conn.untag_resource.when.called_with(
        ResourceArn="not-existing-topic", TagKeys=["tag_key_1"]
    ).should.throw(ClientError, "Resource does not exist")


@mock_sns
def test_create_fifo_topic():
    conn = boto3.client("sns", region_name="us-east-1")
    response = conn.create_topic(
        Name="test_topic.fifo", Attributes={"FifoTopic": "true"}
    )

    assert "TopicArn" in response

    try:
        conn.create_topic(Name="test_topic", Attributes={"FifoTopic": "true"})
    except ClientError as err:
        err.response["Error"]["Code"].should.equal("InvalidParameterValue")
        err.response["Error"]["Message"].should.equal(
            "Fifo Topic names must end with .fifo and must be made up of only uppercase and lowercase ASCII letters, "
            "numbers, underscores, and hyphens, and must be between 1 and 256 characters long."
        )
        err.response["Error"]["Type"].should.equal("Sender")

    try:
        conn.create_topic(Name="test_topic.fifo")
    except ClientError as err:
        err.response["Error"]["Code"].should.equal("InvalidParameterValue")
        err.response["Error"]["Message"].should.equal(
            "Topic names must be made up of only uppercase and lowercase ASCII letters, numbers, underscores, "
            "and hyphens, and must be between 1 and 256 characters long."
        )

    try:
        conn.create_topic(Name="topic.name.fifo", Attributes={"FifoTopic": "true"})
    except ClientError as err:
        err.response["Error"]["Code"].should.equal("InvalidParameterValue")
        err.response["Error"]["Message"].should.equal(
            "Fifo Topic names must end with .fifo and must be made up of only uppercase and lowercase ASCII letters, "
            "numbers, underscores, and hyphens, and must be between 1 and 256 characters long."
        )


@mock_sns
def test_topic_kms_master_key_id_attribute():
    client = boto3.client("sns", region_name="us-west-2")
    resp = client.create_topic(Name="test-sns-no-key-attr")
    topic_arn = resp["TopicArn"]
    resp = client.get_topic_attributes(TopicArn=topic_arn)
    resp["Attributes"].should_not.have.key("KmsMasterKeyId")

    client.set_topic_attributes(
        TopicArn=topic_arn, AttributeName="KmsMasterKeyId", AttributeValue="test-key"
    )
    resp = client.get_topic_attributes(TopicArn=topic_arn)
    resp["Attributes"].should.have.key("KmsMasterKeyId")
    resp["Attributes"]["KmsMasterKeyId"].should.equal("test-key")

    resp = client.create_topic(
        Name="test-sns-with-key-attr", Attributes={"KmsMasterKeyId": "key-id"}
    )
    topic_arn = resp["TopicArn"]
    resp = client.get_topic_attributes(TopicArn=topic_arn)
    resp["Attributes"].should.have.key("KmsMasterKeyId")
    resp["Attributes"]["KmsMasterKeyId"].should.equal("key-id")


@mock_sns
def test_topic_fifo_get_attributes():
    client = boto3.client("sns", region_name="us-east-1")
    resp = client.create_topic(
        Name="test-topic-fifo-get-attr.fifo", Attributes={"FifoTopic": "true"}
    )
    topic_arn = resp["TopicArn"]
    attributes = client.get_topic_attributes(TopicArn=topic_arn)["Attributes"]

    attributes.should.have.key("FifoTopic")
    attributes.should.have.key("ContentBasedDeduplication")

    attributes["FifoTopic"].should.equal("true")
    attributes["ContentBasedDeduplication"].should.equal("false")

    client.set_topic_attributes(
        TopicArn=topic_arn,
        AttributeName="ContentBasedDeduplication",
        AttributeValue="true",
    )
    attributes = client.get_topic_attributes(TopicArn=topic_arn)["Attributes"]
    attributes["ContentBasedDeduplication"].should.equal("true")


@mock_sns
def test_topic_get_attributes():
    client = boto3.client("sns", region_name="us-east-1")
    resp = client.create_topic(Name="test-topic-get-attr")
    topic_arn = resp["TopicArn"]
    attributes = client.get_topic_attributes(TopicArn=topic_arn)["Attributes"]

    attributes.should_not.have.key("FifoTopic")
    attributes.should_not.have.key("ContentBasedDeduplication")


@mock_sns
def test_topic_get_attributes_with_fifo_false():
    client = boto3.client("sns", region_name="us-east-1")
    resp = client.create_topic(
        Name="test-topic-get-attr-with-fifo-false", Attributes={"FifoTopic": "false"}
    )
    topic_arn = resp["TopicArn"]
    attributes = client.get_topic_attributes(TopicArn=topic_arn)["Attributes"]

    attributes.should_not.have.key("FifoTopic")
    attributes.should_not.have.key("ContentBasedDeduplication")
