import json

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
from moto.sns.models import (
    DEFAULT_EFFECTIVE_DELIVERY_POLICY,
    DEFAULT_PAGE_SIZE,
)


@mock_aws
def test_subscribe_sms():
    client = boto3.client("sns", region_name="us-east-1")
    client.create_topic(Name="some-topic")
    resp = client.create_topic(Name="some-topic")
    arn = resp["TopicArn"]

    resp = client.subscribe(TopicArn=arn, Protocol="sms", Endpoint="+15551234567")
    assert "SubscriptionArn" in resp

    resp = client.subscribe(TopicArn=arn, Protocol="sms", Endpoint="+15/55-123.4567")
    assert "SubscriptionArn" in resp


@mock_aws
def test_double_subscription():
    client = boto3.client("sns", region_name="us-east-1")
    client.create_topic(Name="some-topic")
    resp = client.create_topic(Name="some-topic")
    arn = resp["TopicArn"]

    resp1 = client.subscribe(
        TopicArn=arn, Protocol="sqs", Endpoint="arn:aws:sqs:elasticmq:000000000000:foo"
    )
    resp2 = client.subscribe(
        TopicArn=arn, Protocol="sqs", Endpoint="arn:aws:sqs:elasticmq:000000000000:foo"
    )

    assert resp1["SubscriptionArn"] == resp2["SubscriptionArn"]


@mock_aws
def test_subscribe_bad_sms():
    client = boto3.client("sns", region_name="us-east-1")
    client.create_topic(Name="some-topic")
    resp = client.create_topic(Name="some-topic")
    arn = resp["TopicArn"]

    try:
        # Test invalid number
        client.subscribe(TopicArn=arn, Protocol="sms", Endpoint="NAA+15551234567")
    except ClientError as err:
        assert err.response["Error"]["Code"] == "InvalidParameter"

    with pytest.raises(ClientError) as client_err:
        client.subscribe(TopicArn=arn, Protocol="sms", Endpoint="+15--551234567")
    assert (
        client_err.value.response["Error"]["Message"]
        == "Invalid SMS endpoint: +15--551234567"
    )

    with pytest.raises(ClientError) as client_err:
        client.subscribe(TopicArn=arn, Protocol="sms", Endpoint="+15551234567.")
    assert (
        client_err.value.response["Error"]["Message"]
        == "Invalid SMS endpoint: +15551234567."
    )

    with pytest.raises(ClientError) as client_err:
        assert client.subscribe(TopicArn=arn, Protocol="sms", Endpoint="/+15551234567")

    assert (
        client_err.value.response["Error"]["Message"]
        == "Invalid SMS endpoint: /+15551234567"
    )


@mock_aws
def test_creating_subscription():
    conn = boto3.client("sns", region_name="us-east-1")
    conn.create_topic(Name="some-topic")
    response = conn.list_topics()
    topic_arn = response["Topics"][0]["TopicArn"]

    conn.subscribe(TopicArn=topic_arn, Protocol="http", Endpoint="http://example.com/")

    subscriptions = conn.list_subscriptions()["Subscriptions"]
    assert len(subscriptions) == 1
    subscription = subscriptions[0]
    assert subscription["TopicArn"] == topic_arn
    assert subscription["Protocol"] == "http"
    assert topic_arn in subscription["SubscriptionArn"]
    assert subscription["Endpoint"] == "http://example.com/"

    # Now unsubscribe the subscription
    conn.unsubscribe(SubscriptionArn=subscription["SubscriptionArn"])

    # And there should be zero subscriptions left
    subscriptions = conn.list_subscriptions()["Subscriptions"]
    assert len(subscriptions) == 0


@mock_aws
def test_unsubscribe_from_deleted_topic():
    client = boto3.client("sns", region_name="us-east-1")
    client.create_topic(Name="some-topic")
    response = client.list_topics()
    topic_arn = response["Topics"][0]["TopicArn"]

    client.subscribe(
        TopicArn=topic_arn, Protocol="http", Endpoint="http://example.com/"
    )

    subscriptions = client.list_subscriptions()["Subscriptions"]
    assert len(subscriptions) == 1
    subscription = subscriptions[0]
    subscription_arn = subscription["SubscriptionArn"]
    assert subscription["TopicArn"] == topic_arn
    assert subscription["Protocol"] == "http"
    assert topic_arn in subscription_arn
    assert subscription["Endpoint"] == "http://example.com/"

    # Now delete the topic
    client.delete_topic(TopicArn=topic_arn)

    # And there should now be 0 topics
    topics_json = client.list_topics()
    topics = topics_json["Topics"]
    assert len(topics) == 0

    # as per the documentation deleting a topic deletes all the subscriptions
    subscriptions = client.list_subscriptions()["Subscriptions"]
    assert len(subscriptions) == 0

    # Now delete hanging subscription
    client.unsubscribe(SubscriptionArn=subscription_arn)

    subscriptions = client.list_subscriptions()["Subscriptions"]
    assert len(subscriptions) == 0

    # Deleting it again should not result in any error
    client.unsubscribe(SubscriptionArn=subscription_arn)


@mock_aws
def test_getting_subscriptions_by_topic():
    conn = boto3.client("sns", region_name="us-east-1")
    conn.create_topic(Name="topic1")
    conn.create_topic(Name="topic2")

    response = conn.list_topics()
    topics = response["Topics"]
    topic1_arn = topics[0]["TopicArn"]
    topic2_arn = topics[1]["TopicArn"]

    conn.subscribe(
        TopicArn=topic1_arn, Protocol="http", Endpoint="http://example1.com/"
    )
    conn.subscribe(
        TopicArn=topic2_arn, Protocol="http", Endpoint="http://example2.com/"
    )

    topic1_subscriptions = conn.list_subscriptions_by_topic(TopicArn=topic1_arn)[
        "Subscriptions"
    ]
    assert len(topic1_subscriptions) == 1
    assert topic1_subscriptions[0]["Endpoint"] == "http://example1.com/"


@mock_aws
def test_subscription_paging():
    conn = boto3.client("sns", region_name="us-east-1")
    conn.create_topic(Name="topic1")

    response = conn.list_topics()
    topics = response["Topics"]
    topic1_arn = topics[0]["TopicArn"]

    for index in range(DEFAULT_PAGE_SIZE + int(DEFAULT_PAGE_SIZE / 3)):
        conn.subscribe(
            TopicArn=topic1_arn,
            Protocol="email",
            Endpoint="email_" + str(index) + "@test.com",
        )

    all_subscriptions = conn.list_subscriptions()
    assert len(all_subscriptions["Subscriptions"]) == DEFAULT_PAGE_SIZE
    next_token = all_subscriptions["NextToken"]
    assert next_token == str(DEFAULT_PAGE_SIZE)

    all_subscriptions = conn.list_subscriptions(NextToken=next_token)
    assert len(all_subscriptions["Subscriptions"]) == int(DEFAULT_PAGE_SIZE / 3)
    assert "NextToken" not in all_subscriptions

    topic1_subscriptions = conn.list_subscriptions_by_topic(TopicArn=topic1_arn)
    assert len(topic1_subscriptions["Subscriptions"]) == DEFAULT_PAGE_SIZE
    next_token = topic1_subscriptions["NextToken"]
    assert next_token == str(DEFAULT_PAGE_SIZE)

    topic1_subscriptions = conn.list_subscriptions_by_topic(
        TopicArn=topic1_arn, NextToken=next_token
    )
    assert len(topic1_subscriptions["Subscriptions"]) == int(DEFAULT_PAGE_SIZE / 3)
    assert "NextToken" not in topic1_subscriptions


@mock_aws
def test_subscribe_attributes():
    client = boto3.client("sns", region_name="us-east-1")
    client.create_topic(Name="some-topic")
    resp = client.create_topic(Name="some-topic")
    arn = resp["TopicArn"]

    resp = client.subscribe(TopicArn=arn, Protocol="http", Endpoint="http://test.com")

    response = client.get_subscription_attributes(
        SubscriptionArn=resp["SubscriptionArn"]
    )

    assert "Attributes" in response
    attributes = response["Attributes"]
    assert attributes["PendingConfirmation"] == "false"
    assert attributes["ConfirmationWasAuthenticated"] == "true"
    assert attributes["Endpoint"] == "http://test.com"
    assert attributes["TopicArn"] == arn
    assert attributes["Protocol"] == "http"
    assert attributes["SubscriptionArn"] == resp["SubscriptionArn"]
    assert attributes["Owner"] == str(ACCOUNT_ID)
    assert attributes["RawMessageDelivery"] == "false"
    assert json.loads(attributes["EffectiveDeliveryPolicy"]) == (
        DEFAULT_EFFECTIVE_DELIVERY_POLICY
    )


@mock_aws
def test_creating_subscription_with_attributes():
    conn = boto3.client("sns", region_name="us-east-1")
    conn.create_topic(Name="some-topic")
    response = conn.list_topics()
    topic_arn = response["Topics"][0]["TopicArn"]

    delivery_policy = json.dumps(
        {
            "healthyRetryPolicy": {
                "numRetries": 10,
                "minDelayTarget": 1,
                "maxDelayTarget": 2,
            }
        }
    )

    filter_policy = json.dumps(
        {
            "store": ["example_corp"],
            "encrypted": [False],
            "customer_interests": ["basketball", "baseball"],
            "price": [100, 100.12],
            "error": [None],
        }
    )

    subscription_role_arn = "arn:aws:iam:000000000:role/test-role"

    conn.subscribe(
        TopicArn=topic_arn,
        Protocol="http",
        Endpoint="http://example.com/",
        Attributes={
            "RawMessageDelivery": "true",
            "DeliveryPolicy": delivery_policy,
            "FilterPolicy": filter_policy,
            "SubscriptionRoleArn": subscription_role_arn,
        },
    )

    subscriptions = conn.list_subscriptions()["Subscriptions"]
    assert len(subscriptions) == 1
    subscription = subscriptions[0]
    assert subscription["TopicArn"] == topic_arn
    assert subscription["Protocol"] == "http"
    assert topic_arn in subscription["SubscriptionArn"]
    assert subscription["Endpoint"] == "http://example.com/"

    # Test the subscription attributes have been set
    subscription_arn = subscription["SubscriptionArn"]
    attrs = conn.get_subscription_attributes(SubscriptionArn=subscription_arn)

    assert attrs["Attributes"]["RawMessageDelivery"] == "true"
    assert attrs["Attributes"]["DeliveryPolicy"] == delivery_policy
    assert attrs["Attributes"]["FilterPolicy"] == filter_policy
    assert attrs["Attributes"]["SubscriptionRoleArn"] == subscription_role_arn

    # Now unsubscribe the subscription
    conn.unsubscribe(SubscriptionArn=subscription["SubscriptionArn"])

    # And there should be zero subscriptions left
    subscriptions = conn.list_subscriptions()["Subscriptions"]
    assert len(subscriptions) == 0

    # invalid attr name
    with pytest.raises(ClientError):
        conn.subscribe(
            TopicArn=topic_arn,
            Protocol="http",
            Endpoint="http://example.com/",
            Attributes={"InvalidName": "true"},
        )


@mock_aws
def test_delete_subscriptions_on_delete_topic():
    sqs = boto3.client("sqs", region_name="us-east-1")
    conn = boto3.client("sns", region_name="us-east-1")

    queue = sqs.create_queue(QueueName="test-queue")
    topic = conn.create_topic(Name="some-topic")

    conn.subscribe(
        TopicArn=topic.get("TopicArn"), Protocol="sqs", Endpoint=queue.get("QueueUrl")
    )
    subscriptions = conn.list_subscriptions()["Subscriptions"]

    assert len(subscriptions) == 1

    conn.delete_topic(TopicArn=topic.get("TopicArn"))

    subscriptions = conn.list_subscriptions()["Subscriptions"]
    assert len(subscriptions) == 0


@mock_aws
def test_set_subscription_attributes():
    conn = boto3.client("sns", region_name="us-east-1")
    conn.create_topic(Name="some-topic")
    response = conn.list_topics()
    topic_arn = response["Topics"][0]["TopicArn"]

    conn.subscribe(TopicArn=topic_arn, Protocol="http", Endpoint="http://example.com/")

    subscriptions = conn.list_subscriptions()["Subscriptions"]
    assert len(subscriptions) == 1
    subscription = subscriptions[0]
    assert subscription["TopicArn"] == topic_arn
    assert subscription["Protocol"] == "http"
    assert topic_arn in subscription["SubscriptionArn"]
    assert subscription["Endpoint"] == "http://example.com/"

    subscription_arn = subscription["SubscriptionArn"]
    attrs = conn.get_subscription_attributes(SubscriptionArn=subscription_arn)
    assert "Attributes" in attrs
    conn.set_subscription_attributes(
        SubscriptionArn=subscription_arn,
        AttributeName="RawMessageDelivery",
        AttributeValue="true",
    )
    delivery_policy = json.dumps(
        {
            "healthyRetryPolicy": {
                "numRetries": 10,
                "minDelayTarget": 1,
                "maxDelayTarget": 2,
            }
        }
    )
    conn.set_subscription_attributes(
        SubscriptionArn=subscription_arn,
        AttributeName="DeliveryPolicy",
        AttributeValue=delivery_policy,
    )

    filter_policy = json.dumps(
        {
            "store": ["example_corp"],
            "encrypted": [False],
            "customer_interests": ["basketball", "baseball"],
            "price": [100, 100.12],
            "error": [None],
        }
    )
    conn.set_subscription_attributes(
        SubscriptionArn=subscription_arn,
        AttributeName="FilterPolicy",
        AttributeValue=filter_policy,
    )

    attrs = conn.get_subscription_attributes(SubscriptionArn=subscription_arn)

    assert attrs["Attributes"]["RawMessageDelivery"] == "true"
    assert attrs["Attributes"]["DeliveryPolicy"] == delivery_policy
    assert attrs["Attributes"]["FilterPolicy"] == filter_policy
    assert attrs["Attributes"]["FilterPolicyScope"] == "MessageAttributes"

    filter_policy_scope = "MessageBody"
    conn.set_subscription_attributes(
        SubscriptionArn=subscription_arn,
        AttributeName="FilterPolicyScope",
        AttributeValue=filter_policy_scope,
    )

    attrs = conn.get_subscription_attributes(SubscriptionArn=subscription_arn)

    assert attrs["Attributes"]["FilterPolicyScope"] == filter_policy_scope

    # test unsetting a filter policy
    conn.set_subscription_attributes(
        SubscriptionArn=subscription_arn,
        AttributeName="FilterPolicy",
        AttributeValue="",
    )

    attrs = conn.get_subscription_attributes(SubscriptionArn=subscription_arn)
    assert "FilterPolicy" not in attrs["Attributes"]
    assert "FilterPolicyScope" not in attrs["Attributes"]

    # not existing subscription
    with pytest.raises(ClientError):
        conn.set_subscription_attributes(
            SubscriptionArn="invalid",
            AttributeName="RawMessageDelivery",
            AttributeValue="true",
        )
    with pytest.raises(ClientError):
        conn.get_subscription_attributes(SubscriptionArn="invalid")

    # invalid attr name
    with pytest.raises(ClientError):
        conn.set_subscription_attributes(
            SubscriptionArn=subscription_arn,
            AttributeName="InvalidName",
            AttributeValue="true",
        )


@mock_aws
def test_subscribe_invalid_filter_policy():
    conn = boto3.client("sns", region_name="us-east-1")
    conn.create_topic(Name="some-topic")
    response = conn.list_topics()
    topic_arn = response["Topics"][0]["TopicArn"]

    with pytest.raises(ClientError) as err_info:
        conn.subscribe(
            TopicArn=topic_arn,
            Protocol="http",
            Endpoint="http://example.com/",
            Attributes={
                "FilterPolicy": json.dumps({"store": [str(i) for i in range(151)]})
            },
        )

    err = err_info.value
    assert err.response["Error"]["Code"] == "InvalidParameter"
    assert err.response["Error"]["Message"] == (
        "Invalid parameter: FilterPolicy: Filter policy is too complex"
    )

    with pytest.raises(ClientError) as err_info:
        conn.subscribe(
            TopicArn=topic_arn,
            Protocol="http",
            Endpoint="http://example.com/",
            Attributes={"FilterPolicy": json.dumps({"store": [["example_corp"]]})},
        )

    err = err_info.value
    assert err.response["Error"]["Code"] == "InvalidParameter"
    assert err.response["Error"]["Message"] == (
        "Invalid parameter: FilterPolicy: Match value must be String, number, true, false, or null"
    )

    with pytest.raises(ClientError) as err_info:
        conn.subscribe(
            TopicArn=topic_arn,
            Protocol="http",
            Endpoint="http://example.com/",
            Attributes={"FilterPolicy": json.dumps({"store": [{"exists": None}]})},
        )

    err = err_info.value
    assert err.response["Error"]["Code"] == "InvalidParameter"
    assert err.response["Error"]["Message"] == (
        "Invalid parameter: FilterPolicy: exists match pattern must be either true or false."
    )

    with pytest.raises(ClientError) as err_info:
        conn.subscribe(
            TopicArn=topic_arn,
            Protocol="http",
            Endpoint="http://example.com/",
            Attributes={"FilterPolicy": json.dumps({"store": [{"error": True}]})},
        )

    err = err_info.value
    assert err.response["Error"]["Code"] == "InvalidParameter"
    assert err.response["Error"]["Message"] == (
        "Invalid parameter: FilterPolicy: Unrecognized match type error"
    )

    with pytest.raises(ClientError) as err_info:
        conn.subscribe(
            TopicArn=topic_arn,
            Protocol="http",
            Endpoint="http://example.com/",
            Attributes={"FilterPolicy": json.dumps({"store": [1000000001]})},
        )

    err = err_info.value
    assert err.response["Error"]["Code"] == "InternalFailure"

    with pytest.raises(ClientError) as err_info:
        conn.subscribe(
            TopicArn=topic_arn,
            Protocol="http",
            Endpoint="http://example.com/",
            Attributes={
                "FilterPolicy": json.dumps({"price": [{"numeric": ["<", "100"]}]})
            },
        )

    err = err_info.value
    assert err.response["Error"]["Code"] == "InvalidParameter"
    assert err.response["Error"]["Message"] == (
        "Invalid parameter: Attributes Reason: FilterPolicy: Value of < must be numeric\n at ..."
    )

    with pytest.raises(ClientError) as err_info:
        conn.subscribe(
            TopicArn=topic_arn,
            Protocol="http",
            Endpoint="http://example.com/",
            Attributes={
                "FilterPolicy": json.dumps(
                    {"price": [{"numeric": [">", 50, "<=", "100"]}]}
                )
            },
        )

    err = err_info.value
    assert err.response["Error"]["Code"] == "InvalidParameter"
    assert err.response["Error"]["Message"] == (
        "Invalid parameter: Attributes Reason: FilterPolicy: Value of <= must be numeric\n at ..."
    )

    with pytest.raises(ClientError) as err_info:
        conn.subscribe(
            TopicArn=topic_arn,
            Protocol="http",
            Endpoint="http://example.com/",
            Attributes={"FilterPolicy": json.dumps({"price": [{"numeric": []}]})},
        )

    err = err_info.value
    assert err.response["Error"]["Code"] == "InvalidParameter"
    assert err.response["Error"]["Message"] == (
        "Invalid parameter: Attributes Reason: FilterPolicy: "
        "Invalid member in numeric match: ]\n at ..."
    )

    with pytest.raises(ClientError) as err_info:
        conn.subscribe(
            TopicArn=topic_arn,
            Protocol="http",
            Endpoint="http://example.com/",
            Attributes={
                "FilterPolicy": json.dumps({"price": [{"numeric": [50, "<=", "100"]}]})
            },
        )

    err = err_info.value
    assert err.response["Error"]["Code"] == "InvalidParameter"
    assert err.response["Error"]["Message"] == (
        "Invalid parameter: Attributes Reason: FilterPolicy: Invalid "
        "member in numeric match: 50\n at ..."
    )

    with pytest.raises(ClientError) as err_info:
        conn.subscribe(
            TopicArn=topic_arn,
            Protocol="http",
            Endpoint="http://example.com/",
            Attributes={"FilterPolicy": json.dumps({"price": [{"numeric": ["<"]}]})},
        )

    err = err_info.value
    assert err.response["Error"]["Code"] == "InvalidParameter"
    assert err.response["Error"]["Message"] == (
        "Invalid parameter: Attributes Reason: FilterPolicy: Value of < must be numeric\n at ..."
    )

    with pytest.raises(ClientError) as err_info:
        conn.subscribe(
            TopicArn=topic_arn,
            Protocol="http",
            Endpoint="http://example.com/",
            Attributes={"FilterPolicy": json.dumps({"price": [{"numeric": ["0"]}]})},
        )

    err = err_info.value
    assert err.response["Error"]["Code"] == "InvalidParameter"
    assert err.response["Error"]["Message"] == (
        "Invalid parameter: Attributes Reason: FilterPolicy: "
        "Unrecognized numeric range operator: 0\n at ..."
    )

    with pytest.raises(ClientError) as err_info:
        conn.subscribe(
            TopicArn=topic_arn,
            Protocol="http",
            Endpoint="http://example.com/",
            Attributes={
                "FilterPolicy": json.dumps({"price": [{"numeric": ["<", 20, ">", 1]}]})
            },
        )

    err = err_info.value
    assert err.response["Error"]["Code"] == "InvalidParameter"
    assert err.response["Error"]["Message"] == (
        "Invalid parameter: Attributes Reason: FilterPolicy: Too many "
        "elements in numeric expression\n at ..."
    )

    with pytest.raises(ClientError) as err_info:
        conn.subscribe(
            TopicArn=topic_arn,
            Protocol="http",
            Endpoint="http://example.com/",
            Attributes={
                "FilterPolicy": json.dumps({"price": [{"numeric": [">", 20, ">", 1]}]})
            },
        )

    err = err_info.value
    assert err.response["Error"]["Code"] == "InvalidParameter"
    assert err.response["Error"]["Message"] == (
        "Invalid parameter: Attributes Reason: FilterPolicy: Bad numeric range operator: >\n at ..."
    )

    with pytest.raises(ClientError) as err_info:
        conn.subscribe(
            TopicArn=topic_arn,
            Protocol="http",
            Endpoint="http://example.com/",
            Attributes={
                "FilterPolicy": json.dumps({"price": [{"numeric": [">", 20, "<", 1]}]})
            },
        )

    err = err_info.value
    assert err.response["Error"]["Code"] == "InvalidParameter"
    assert err.response["Error"]["Message"] == (
        "Invalid parameter: Attributes Reason: FilterPolicy: Bottom must be less than top\n at ..."
    )

    with pytest.raises(ClientError) as err_info:
        conn.subscribe(
            TopicArn=topic_arn,
            Protocol="http",
            Endpoint="http://example.com/",
            Attributes={
                "FilterPolicy": json.dumps({"price": [{"numeric": [">", 20, "<"]}]})
            },
        )

    err = err_info.value
    assert err.response["Error"]["Code"] == "InvalidParameter"
    assert err.response["Error"]["Message"] == (
        "Invalid parameter: Attributes Reason: FilterPolicy: Value of < must be numeric\n at ..."
    )

    with pytest.raises(ClientError) as err_info:
        conn.subscribe(
            TopicArn=topic_arn,
            Protocol="http",
            Endpoint="http://example.com/",
            Attributes={
                "FilterPolicy": json.dumps({"store": {"key": [{"exists": None}]}})
            },
        )
    assert err_info.value.response["Error"]["Code"] == "InvalidParameter"
    assert (
        err_info.value.response["Error"]["Message"]
        == "Invalid parameter: Filter policy scope MessageAttributes does not support nested filter policy"
    )

    with pytest.raises(ClientError) as err_info:
        filter_policy = {
            "key_a": ["value_one"],
            "key_b": ["value_two"],
            "key_c": ["value_three"],
            "key_d": ["value_four"],
            "key_e": ["value_five"],
            "key_f": ["value_six"],
        }
        conn.subscribe(
            TopicArn=topic_arn,
            Protocol="http",
            Endpoint="http://example.com/",
            Attributes={"FilterPolicy": json.dumps(filter_policy)},
        )
    assert err_info.value.response["Error"]["Code"] == "InvalidParameter"
    assert (
        err_info.value.response["Error"]["Message"]
        == "Invalid parameter: FilterPolicy: Filter policy can not have more than 5 keys"
    )

    with pytest.raises(ClientError) as err_info:
        nested_filter_policy = {
            "key_a": {
                "key_b": {
                    "key_c": ["value_one", "value_two", "value_three", "value_four"]
                },
            },
            "key_d": {"key_e": ["value_one", "value_two", "value_three"]},
            "key_f": ["value_one", "value_two", "value_three"],
        }
        # The first array has four values in a three-level nested key,
        # and the second has three values in a two-level nested key. The
        # total combination is calculated as follows:
        # 3 x 4 x 2 x 3 x 1 x 3 = 216
        conn.subscribe(
            TopicArn=topic_arn,
            Protocol="http",
            Endpoint="http://example.com/",
            Attributes={
                "FilterPolicyScope": "MessageBody",
                "FilterPolicy": json.dumps(nested_filter_policy),
            },
        )
    assert err_info.value.response["Error"]["Code"] == "InvalidParameter"
    assert err_info.value.response["Error"]["Message"] == (
        "Invalid parameter: FilterPolicy: Filter policy is too complex"
    )


@mock_aws
def test_check_not_opted_out():
    conn = boto3.client("sns", region_name="us-east-1")
    response = conn.check_if_phone_number_is_opted_out(phoneNumber="+447428545375")

    assert "isOptedOut" in response
    assert response["isOptedOut"] is False


@mock_aws
def test_check_opted_out():
    # Phone number ends in 99 so is hardcoded in the endpoint to return opted
    # out status
    conn = boto3.client("sns", region_name="us-east-1")
    response = conn.check_if_phone_number_is_opted_out(phoneNumber="+447428545399")

    assert "isOptedOut" in response
    assert response["isOptedOut"] is True


@mock_aws
def test_check_opted_out_invalid():
    conn = boto3.client("sns", region_name="us-east-1")

    # Invalid phone number
    with pytest.raises(ClientError):
        conn.check_if_phone_number_is_opted_out(phoneNumber="+44742LALALA")


@mock_aws
def test_list_opted_out():
    conn = boto3.client("sns", region_name="us-east-1")
    response = conn.list_phone_numbers_opted_out()

    assert "phoneNumbers" in response
    assert len(response["phoneNumbers"]) > 0


@mock_aws
def test_opt_in():
    conn = boto3.client("sns", region_name="us-east-1")
    response = conn.list_phone_numbers_opted_out()
    current_len = len(response["phoneNumbers"])
    assert current_len > 0

    conn.opt_in_phone_number(phoneNumber=response["phoneNumbers"][0])

    response = conn.list_phone_numbers_opted_out()
    assert len(response["phoneNumbers"]) > 0
    assert len(response["phoneNumbers"]) < current_len


@mock_aws
def test_confirm_subscription():
    conn = boto3.client("sns", region_name="us-east-1")
    response = conn.create_topic(Name="testconfirm")

    conn.confirm_subscription(
        TopicArn=response["TopicArn"],
        Token=(
            "2336412f37fb687f5d51e6e241d59b68c4e583a5cee0be6f95bbf97ab8d"
            "2441cf47b99e848408adaadf4c197e65f03473d53c4ba398f6abbf38ce2"
            "e8ebf7b4ceceb2cd817959bcde1357e58a2861b05288c535822eb88cac3"
            "db04f592285249971efc6484194fc4a4586147f16916692"
        ),
        AuthenticateOnUnsubscribe="true",
    )


@mock_aws
def test_get_subscription_attributes_error_not_exists():
    # given
    client = boto3.client("sns", region_name="us-east-1")
    sub_arn = (
        f"arn:aws:sqs:us-east-1:{ACCOUNT_ID}:test-queue"
        ":66d97e76-31e5-444f-8fa7-b60b680d0d39"
    )

    # when
    with pytest.raises(ClientError) as exc:
        client.get_subscription_attributes(SubscriptionArn=sub_arn)

    # then
    exc_value = exc.value
    assert exc_value.operation_name == "GetSubscriptionAttributes"
    assert exc_value.response["ResponseMetadata"]["HTTPStatusCode"] == 404
    assert "NotFound" in exc_value.response["Error"]["Code"]
    assert exc_value.response["Error"]["Message"] == "Subscription does not exist"
