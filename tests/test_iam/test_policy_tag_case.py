import json

import boto3

from moto import mock_aws

POLICY = json.dumps(
    {
        "Version": "2012-10-17",
        "Statement": [{"Effect": "Allow", "Action": "s3:ListBucket", "Resource": "*"}],
    }
)


@mock_aws
def test_create_policy_allows_case_distinct_tag_keys():
    client = boto3.client("iam", region_name="us-east-1")
    tags = [
        {"Key": "Costcenter", "Value": "1234"},
        {"Key": "costcenter", "Value": "5678"},
    ]
    policy = client.create_policy(
        PolicyName="case-sensitive", PolicyDocument=POLICY, Tags=tags
    )["Policy"]
    assert {tag["Key"]: tag["Value"] for tag in policy["Tags"]} == {
        "Costcenter": "1234",
        "costcenter": "5678",
    }


@mock_aws
def test_tag_policy_updates_only_the_exact_key():
    client = boto3.client("iam", region_name="us-east-1")
    arn = client.create_policy(
        PolicyName="case-sensitive",
        PolicyDocument=POLICY,
        Tags=[{"Key": "Costcenter", "Value": "1234"}],
    )["Policy"]["Arn"]
    client.tag_policy(PolicyArn=arn, Tags=[{"Key": "costcenter", "Value": "5678"}])
    client.tag_policy(PolicyArn=arn, Tags=[{"Key": "Costcenter", "Value": "updated"}])
    assert {
        tag["Key"]: tag["Value"]
        for tag in client.list_policy_tags(PolicyArn=arn)["Tags"]
    } == {"Costcenter": "updated", "costcenter": "5678"}


@mock_aws
def test_untag_policy_does_not_match_a_different_case():
    client = boto3.client("iam", region_name="us-east-1")
    tags = [{"Key": "Costcenter", "Value": "1234"}]
    arn = client.create_policy(
        PolicyName="case-sensitive", PolicyDocument=POLICY, Tags=tags
    )["Policy"]["Arn"]
    client.untag_policy(PolicyArn=arn, TagKeys=["costcenter"])
    assert client.list_policy_tags(PolicyArn=arn)["Tags"] == tags
    client.untag_policy(PolicyArn=arn, TagKeys=["Costcenter"])
    assert client.list_policy_tags(PolicyArn=arn)["Tags"] == []
