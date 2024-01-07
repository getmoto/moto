import json

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
from moto.sns.models import DEFAULT_EFFECTIVE_DELIVERY_POLICY, DEFAULT_PAGE_SIZE


@mock_aws
def test_create_and_delete_topic():
    conn = boto3.client("sns", region_name="us-east-1")
    for topic_name in ("some-topic", "-some-topic-", "_some-topic_", "a" * 256):
        conn.create_topic(Name=topic_name)

        topics_json = conn.list_topics()
        topics = topics_json["Topics"]
        assert len(topics) == 1
        assert topics[0]["TopicArn"] == (
            f"arn:aws:sns:{conn._client_config.region_name}:{ACCOUNT_ID}:{topic_name}"
        )

        # Delete the topic
        conn.delete_topic(TopicArn=topics[0]["TopicArn"])

        # Ensure DeleteTopic is idempotent
        conn.delete_topic(TopicArn=topics[0]["TopicArn"])

        # And there should now be 0 topics
        topics_json = conn.list_topics()
        topics = topics_json["Topics"]
        assert len(topics) == 0


@mock_aws
def test_delete_non_existent_topic():
    conn = boto3.client("sns", region_name="us-east-1")

    # Ensure DeleteTopic does not throw an error for non-existent topics
    conn.delete_topic(
        TopicArn="arn:aws:sns:us-east-1:123456789012:this-topic-does-not-exist"
    )


@mock_aws
def test_create_topic_with_attributes():
    conn = boto3.client("sns", region_name="us-east-1")
    conn.create_topic(
        Name="some-topic-with-attribute", Attributes={"DisplayName": "test-topic"}
    )
    topics_json = conn.list_topics()
    topic_arn = topics_json["Topics"][0]["TopicArn"]

    attributes = conn.get_topic_attributes(TopicArn=topic_arn)["Attributes"]
    assert attributes["DisplayName"] == "test-topic"


@mock_aws
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

    assert conn.list_tags_for_resource(ResourceArn=topic_arn)["Tags"] == (
        [
            {"Key": "tag_key_1", "Value": "tag_value_1"},
            {"Key": "tag_key_2", "Value": "tag_value_2"},
        ]
    )


@mock_aws
def test_create_topic_should_be_indempodent():
    conn = boto3.client("sns", region_name="us-east-1")
    topic_arn = conn.create_topic(Name="some-topic")["TopicArn"]
    conn.set_topic_attributes(
        TopicArn=topic_arn, AttributeName="DisplayName", AttributeValue="should_be_set"
    )
    topic_display_name = conn.get_topic_attributes(TopicArn=topic_arn)["Attributes"][
        "DisplayName"
    ]
    assert topic_display_name == "should_be_set"

    # recreate topic to prove indempodentcy
    topic_arn = conn.create_topic(Name="some-topic")["TopicArn"]
    topic_display_name = conn.get_topic_attributes(TopicArn=topic_arn)["Attributes"][
        "DisplayName"
    ]
    assert topic_display_name == "should_be_set"


@mock_aws
def test_get_missing_topic():
    conn = boto3.client("sns", region_name="us-east-1")
    with pytest.raises(ClientError):
        conn.get_topic_attributes(
            TopicArn="arn:aws:sns:us-east-1:424242424242:a-fake-arn"
        )


@mock_aws
def test_create_topic_must_meet_constraints():
    conn = boto3.client("sns", region_name="us-east-1")
    common_random_chars = [":", ";", "!", "@", "|", "^", "%"]
    for char in common_random_chars:
        with pytest.raises(ClientError):
            conn.create_topic(Name=f"no{char}_invalidchar")
    with pytest.raises(ClientError):
        conn.create_topic(Name="no spaces allowed")


@mock_aws
def test_create_topic_should_be_of_certain_length():
    conn = boto3.client("sns", region_name="us-east-1")
    too_short = ""
    with pytest.raises(ClientError):
        conn.create_topic(Name=too_short)
    too_long = "x" * 257
    with pytest.raises(ClientError):
        conn.create_topic(Name=too_long)


@mock_aws
def test_create_topic_in_multiple_regions():
    for region in ["us-west-1", "us-west-2"]:
        conn = boto3.client("sns", region_name=region)
        topic_arn = conn.create_topic(Name="some-topic")["TopicArn"]
        # We can find the topic
        assert len(list(conn.list_topics()["Topics"])) == 1

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


@mock_aws
def test_topic_corresponds_to_region():
    for region in ["us-east-1", "us-west-2"]:
        conn = boto3.client("sns", region_name=region)
        conn.create_topic(Name="some-topic")
        topics_json = conn.list_topics()
        topic_arn = topics_json["Topics"][0]["TopicArn"]
        assert topic_arn == f"arn:aws:sns:{region}:{ACCOUNT_ID}:some-topic"


@mock_aws
def test_topic_attributes():
    conn = boto3.client("sns", region_name="us-east-1")
    conn.create_topic(Name="some-topic")

    topics_json = conn.list_topics()
    topic_arn = topics_json["Topics"][0]["TopicArn"]

    attributes = conn.get_topic_attributes(TopicArn=topic_arn)["Attributes"]
    assert attributes["TopicArn"] == (
        f"arn:aws:sns:{conn._client_config.region_name}:{ACCOUNT_ID}:some-topic"
    )
    assert attributes["Owner"] == ACCOUNT_ID
    assert json.loads(attributes["Policy"]) == {
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
    assert attributes["DisplayName"] == ""
    assert attributes["SubscriptionsPending"] == "0"
    assert attributes["SubscriptionsConfirmed"] == "0"
    assert attributes["SubscriptionsDeleted"] == "0"
    assert attributes["DeliveryPolicy"] == ""
    assert json.loads(attributes["EffectiveDeliveryPolicy"]) == (
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
    assert attributes["Policy"] == '{"foo":"bar"}'
    assert attributes["DisplayName"] == "My display name"
    assert attributes["DeliveryPolicy"] == (
        '{"http": {"defaultHealthyRetryPolicy": {"numRetries": 5}}}'
    )


@mock_aws
def test_topic_paging():
    conn = boto3.client("sns", region_name="us-east-1")
    for index in range(DEFAULT_PAGE_SIZE + int(DEFAULT_PAGE_SIZE / 2)):
        conn.create_topic(Name="some-topic_" + str(index))

    response = conn.list_topics()
    topics_list = response["Topics"]
    next_token = response["NextToken"]

    assert len(topics_list) == DEFAULT_PAGE_SIZE
    assert int(next_token) == DEFAULT_PAGE_SIZE

    response = conn.list_topics(NextToken=next_token)
    topics_list = response["Topics"]
    assert "NextToken" not in response

    assert len(topics_list) == int(DEFAULT_PAGE_SIZE / 2)


@mock_aws
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
    assert json.loads(response["Attributes"]["Policy"]) == {
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

    client.remove_permission(TopicArn=topic_arn, Label="test")

    response = client.get_topic_attributes(TopicArn=topic_arn)
    assert json.loads(response["Attributes"]["Policy"]) == {
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

    client.add_permission(
        TopicArn=topic_arn,
        Label="test",
        AWSAccountId=["888888888888", "999999999999"],
        ActionName=["Publish", "Subscribe"],
    )

    response = client.get_topic_attributes(TopicArn=topic_arn)
    assert json.loads(response["Attributes"]["Policy"])["Statement"][1] == {
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

    # deleting non existing permission should be successful
    client.remove_permission(TopicArn=topic_arn, Label="non-existing")


@mock_aws
def test_add_permission_errors():
    client = boto3.client("sns", region_name="us-east-1")
    topic_arn = client.create_topic(Name="test-permissions")["TopicArn"]
    client.add_permission(
        TopicArn=topic_arn,
        Label="test",
        AWSAccountId=["999999999999"],
        ActionName=["Publish"],
    )

    with pytest.raises(ClientError) as client_err:
        client.add_permission(
            TopicArn=topic_arn,
            Label="test",
            AWSAccountId=["999999999999"],
            ActionName=["AddPermission"],
        )
    assert client_err.value.response["Error"]["Message"] == "Statement already exists"

    with pytest.raises(ClientError) as client_err:
        client.add_permission(
            TopicArn=topic_arn + "-not-existing",
            Label="test-2",
            AWSAccountId=["999999999999"],
            ActionName=["AddPermission"],
        )
    assert client_err.value.response["Error"]["Code"] == "NotFound"
    assert client_err.value.response["Error"]["Message"] == "Topic does not exist"

    with pytest.raises(ClientError) as client_err:
        client.add_permission(
            TopicArn=topic_arn,
            Label="test-2",
            AWSAccountId=["999999999999"],
            ActionName=["NotExistingAction"],
        )
    assert client_err.value.response["Error"]["Message"] == (
        "Policy statement action out of service scope!"
    )


@mock_aws
def test_remove_permission_errors():
    client = boto3.client("sns", region_name="us-east-1")
    topic_arn = client.create_topic(Name="test-permissions")["TopicArn"]
    client.add_permission(
        TopicArn=topic_arn,
        Label="test",
        AWSAccountId=["999999999999"],
        ActionName=["Publish"],
    )

    with pytest.raises(ClientError) as client_err:
        client.remove_permission(TopicArn=topic_arn + "-not-existing", Label="test")

    assert client_err.value.response["Error"]["Code"] == "NotFound"
    assert client_err.value.response["Error"]["Message"] == "Topic does not exist"


@mock_aws
def test_tag_topic():
    conn = boto3.client("sns", region_name="us-east-1")
    response = conn.create_topic(Name="some-topic-with-tags")
    topic_arn = response["TopicArn"]

    conn.tag_resource(
        ResourceArn=topic_arn, Tags=[{"Key": "tag_key_1", "Value": "tag_value_1"}]
    )
    assert conn.list_tags_for_resource(ResourceArn=topic_arn)["Tags"] == (
        [{"Key": "tag_key_1", "Value": "tag_value_1"}]
    )

    conn.tag_resource(
        ResourceArn=topic_arn, Tags=[{"Key": "tag_key_2", "Value": "tag_value_2"}]
    )
    assert conn.list_tags_for_resource(ResourceArn=topic_arn)["Tags"] == (
        [
            {"Key": "tag_key_1", "Value": "tag_value_1"},
            {"Key": "tag_key_2", "Value": "tag_value_2"},
        ]
    )

    conn.tag_resource(
        ResourceArn=topic_arn, Tags=[{"Key": "tag_key_1", "Value": "tag_value_X"}]
    )
    assert conn.list_tags_for_resource(ResourceArn=topic_arn)["Tags"] == (
        [
            {"Key": "tag_key_1", "Value": "tag_value_X"},
            {"Key": "tag_key_2", "Value": "tag_value_2"},
        ]
    )


@mock_aws
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
    assert conn.list_tags_for_resource(ResourceArn=topic_arn)["Tags"] == (
        [{"Key": "tag_key_2", "Value": "tag_value_2"}]
    )

    # removing a non existing tag should not raise any error
    conn.untag_resource(ResourceArn=topic_arn, TagKeys=["not-existing-tag"])
    assert conn.list_tags_for_resource(ResourceArn=topic_arn)["Tags"] == (
        [{"Key": "tag_key_2", "Value": "tag_value_2"}]
    )


@mock_aws
def test_list_tags_for_resource_error():
    conn = boto3.client("sns", region_name="us-east-1")
    conn.create_topic(
        Name="some-topic-with-tags", Tags=[{"Key": "tag_key_1", "Value": "tag_value_X"}]
    )

    with pytest.raises(ClientError) as client_err:
        conn.list_tags_for_resource(ResourceArn="not-existing-topic")
    assert client_err.value.response["Error"]["Message"] == "Resource does not exist"


@mock_aws
def test_tag_resource_errors():
    conn = boto3.client("sns", region_name="us-east-1")
    response = conn.create_topic(
        Name="some-topic-with-tags", Tags=[{"Key": "tag_key_1", "Value": "tag_value_X"}]
    )
    topic_arn = response["TopicArn"]

    with pytest.raises(ClientError) as client_err:
        conn.tag_resource(
            ResourceArn="not-existing-topic",
            Tags=[{"Key": "tag_key_1", "Value": "tag_value_1"}],
        )
    assert client_err.value.response["Error"]["Message"] == "Resource does not exist"

    too_many_tags = [
        {"Key": f"tag_key_{i}", "Value": f"tag_value_{i}"} for i in range(51)
    ]
    with pytest.raises(ClientError) as client_err:
        conn.tag_resource(ResourceArn=topic_arn, Tags=too_many_tags)
    assert client_err.value.response["Error"]["Message"] == (
        "Could not complete request: tag quota of per resource exceeded"
    )

    # when the request fails, the tags should not be updated
    assert conn.list_tags_for_resource(ResourceArn=topic_arn)["Tags"] == (
        [{"Key": "tag_key_1", "Value": "tag_value_X"}]
    )


@mock_aws
def test_untag_resource_error():
    conn = boto3.client("sns", region_name="us-east-1")
    conn.create_topic(
        Name="some-topic-with-tags", Tags=[{"Key": "tag_key_1", "Value": "tag_value_X"}]
    )

    with pytest.raises(ClientError) as client_err:
        conn.untag_resource(ResourceArn="not-existing-topic", TagKeys=["tag_key_1"])
    assert client_err.value.response["Error"]["Message"] == "Resource does not exist"


@mock_aws
def test_create_fifo_topic():
    conn = boto3.client("sns", region_name="us-east-1")
    response = conn.create_topic(
        Name="test_topic.fifo", Attributes={"FifoTopic": "true"}
    )

    assert "TopicArn" in response

    try:
        conn.create_topic(Name="test_topic", Attributes={"FifoTopic": "true"})
    except ClientError as err:
        assert err.response["Error"]["Code"] == "InvalidParameterValue"
        assert err.response["Error"]["Message"] == (
            "Fifo Topic names must end with .fifo and must be made up of only "
            "uppercase and lowercase ASCII letters, numbers, underscores, "
            "and hyphens, and must be between 1 and 256 characters long."
        )
        assert err.response["Error"]["Type"] == "Sender"

    try:
        conn.create_topic(Name="test_topic.fifo")
    except ClientError as err:
        assert err.response["Error"]["Code"] == "InvalidParameterValue"
        assert err.response["Error"]["Message"] == (
            "Topic names must be made up of only uppercase and lowercase "
            "ASCII letters, numbers, underscores, "
            "and hyphens, and must be between 1 and 256 characters long."
        )

    try:
        conn.create_topic(Name="topic.name.fifo", Attributes={"FifoTopic": "true"})
    except ClientError as err:
        assert err.response["Error"]["Code"] == "InvalidParameterValue"
        assert err.response["Error"]["Message"] == (
            "Fifo Topic names must end with .fifo and must be made up of only "
            "uppercase and lowercase ASCII letters, numbers, underscores, "
            "and hyphens, and must be between 1 and 256 characters long."
        )


@mock_aws
def test_topic_kms_master_key_id_attribute():
    client = boto3.client("sns", region_name="us-west-2")
    resp = client.create_topic(Name="test-sns-no-key-attr")
    topic_arn = resp["TopicArn"]
    resp = client.get_topic_attributes(TopicArn=topic_arn)
    assert "KmsMasterKeyId" not in resp["Attributes"]

    client.set_topic_attributes(
        TopicArn=topic_arn, AttributeName="KmsMasterKeyId", AttributeValue="test-key"
    )
    resp = client.get_topic_attributes(TopicArn=topic_arn)
    assert "KmsMasterKeyId" in resp["Attributes"]
    assert resp["Attributes"]["KmsMasterKeyId"] == "test-key"

    resp = client.create_topic(
        Name="test-sns-with-key-attr", Attributes={"KmsMasterKeyId": "key-id"}
    )
    topic_arn = resp["TopicArn"]
    resp = client.get_topic_attributes(TopicArn=topic_arn)
    assert "KmsMasterKeyId" in resp["Attributes"]
    assert resp["Attributes"]["KmsMasterKeyId"] == "key-id"


@mock_aws
def test_topic_fifo_get_attributes():
    client = boto3.client("sns", region_name="us-east-1")
    resp = client.create_topic(
        Name="test-topic-fifo-get-attr.fifo", Attributes={"FifoTopic": "true"}
    )
    topic_arn = resp["TopicArn"]
    attributes = client.get_topic_attributes(TopicArn=topic_arn)["Attributes"]

    assert "FifoTopic" in attributes
    assert "ContentBasedDeduplication" in attributes

    assert attributes["FifoTopic"] == "true"
    assert attributes["ContentBasedDeduplication"] == "false"

    client.set_topic_attributes(
        TopicArn=topic_arn,
        AttributeName="ContentBasedDeduplication",
        AttributeValue="true",
    )
    attributes = client.get_topic_attributes(TopicArn=topic_arn)["Attributes"]
    assert attributes["ContentBasedDeduplication"] == "true"


@mock_aws
def test_topic_get_attributes():
    client = boto3.client("sns", region_name="us-east-1")
    resp = client.create_topic(Name="test-topic-get-attr")
    topic_arn = resp["TopicArn"]
    attributes = client.get_topic_attributes(TopicArn=topic_arn)["Attributes"]

    assert "FifoTopic" not in attributes
    assert "ContentBasedDeduplication" not in attributes


@mock_aws
def test_topic_get_attributes_with_fifo_false():
    client = boto3.client("sns", region_name="us-east-1")
    resp = client.create_topic(
        Name="test-topic-get-attr-with-fifo-false", Attributes={"FifoTopic": "false"}
    )
    topic_arn = resp["TopicArn"]
    attributes = client.get_topic_attributes(TopicArn=topic_arn)["Attributes"]

    assert "FifoTopic" not in attributes
    assert "ContentBasedDeduplication" not in attributes
