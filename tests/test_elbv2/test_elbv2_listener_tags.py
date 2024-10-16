import pytest
from botocore.exceptions import ClientError

from moto import mock_aws

from .test_elbv2 import create_load_balancer


@mock_aws
def test_create_listener_with_tags():
    response, _, _, _, _, elbv2 = create_load_balancer()

    load_balancer_arn = response.get("LoadBalancers")[0].get("LoadBalancerArn")

    listener_arn = elbv2.create_listener(
        LoadBalancerArn=load_balancer_arn,
        Protocol="HTTP",
        Port=80,
        DefaultActions=[],
        Tags=[{"Key": "k1", "Value": "v1"}],
    )["Listeners"][0]["ListenerArn"]

    # Ensure the tags persisted
    response = elbv2.describe_tags(ResourceArns=[listener_arn])
    tags = {d["Key"]: d["Value"] for d in response["TagDescriptions"][0]["Tags"]}
    assert tags == {"k1": "v1"}


@mock_aws
def test_listener_add_remove_tags():
    response, _, _, _, _, elbv2 = create_load_balancer()

    load_balancer_arn = response.get("LoadBalancers")[0].get("LoadBalancerArn")

    listener_arn = elbv2.create_listener(
        LoadBalancerArn=load_balancer_arn,
        Protocol="HTTP",
        Port=80,
        DefaultActions=[],
        Tags=[{"Key": "k1", "Value": "v1"}],
    )["Listeners"][0]["ListenerArn"]

    elbv2.add_tags(ResourceArns=[listener_arn], Tags=[{"Key": "a", "Value": "b"}])

    tags = elbv2.describe_tags(ResourceArns=[listener_arn])["TagDescriptions"][0][
        "Tags"
    ]
    assert tags == [{"Key": "k1", "Value": "v1"}, {"Key": "a", "Value": "b"}]

    elbv2.add_tags(
        ResourceArns=[listener_arn],
        Tags=[
            {"Key": "a", "Value": "b"},
            {"Key": "b", "Value": "b"},
            {"Key": "c", "Value": "b"},
        ],
    )

    tags = elbv2.describe_tags(ResourceArns=[listener_arn])["TagDescriptions"][0][
        "Tags"
    ]
    assert tags == [
        {"Key": "k1", "Value": "v1"},
        {"Key": "a", "Value": "b"},
        {"Key": "b", "Value": "b"},
        {"Key": "c", "Value": "b"},
    ]

    elbv2.remove_tags(ResourceArns=[listener_arn], TagKeys=["a"])

    tags = elbv2.describe_tags(ResourceArns=[listener_arn])["TagDescriptions"][0][
        "Tags"
    ]
    assert tags == [
        {"Key": "k1", "Value": "v1"},
        {"Key": "b", "Value": "b"},
        {"Key": "c", "Value": "b"},
    ]


@mock_aws
def test_remove_tags_to_invalid_listener():
    response, _, _, _, _, elbv2 = create_load_balancer()
    load_balancer_arn = response.get("LoadBalancers")[0].get("LoadBalancerArn")

    listener_arn = elbv2.create_listener(
        LoadBalancerArn=load_balancer_arn,
        Protocol="HTTP",
        Port=80,
        DefaultActions=[],
    )["Listeners"][0]["ListenerArn"]

    # add a random string in the ARN to make the resource non-existent
    BAD_ARN = listener_arn + "randomstring"

    # test for exceptions on remove tags
    with pytest.raises(ClientError) as err:
        elbv2.remove_tags(ResourceArns=[BAD_ARN], TagKeys=["a"])

    assert err.value.response["Error"]["Code"] == "ListenerNotFound"
    assert (
        err.value.response["Error"]["Message"]
        == "The specified listener does not exist."
    )
