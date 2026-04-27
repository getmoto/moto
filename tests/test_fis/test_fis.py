"""Unit tests for fis-supported APIs."""

import boto3

from moto import mock_aws

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_aws
def test_create_experiment_template():
    client = boto3.client("fis", region_name="ap-southeast-1")
    resp = client.create_experiment_template(
        clientToken="token-123",
        description="my template",
        stopConditions=[{"source": "none"}],
        targets={
            "t1": {
                "resourceType": "aws:ec2:instance",
                "resourceArns": [
                    "arn:aws:ec2:ap-southeast-1:123456789012:instance/i-123"
                ],
                "selectionMode": "ALL",
            }
        },
        actions={
            "a1": {
                "actionId": "aws:ec2:stop-instances",
                "parameters": {},
                "targets": {"Instances": "t1"},
            }
        },
        roleArn="arn:aws:iam::123456789012:role/FISRole",
        tags={"env": "test"},
    )

    tmpl = resp["experimentTemplate"]
    assert tmpl["id"]
    assert tmpl["arn"].endswith(f"experiment-template/{tmpl['id']}")
    assert tmpl["description"] == "my template"
    assert tmpl["roleArn"] == "arn:aws:iam::123456789012:role/FISRole"
    assert tmpl["targets"]["t1"]["selectionMode"] == "ALL"
    assert tmpl["actions"]["a1"]["actionId"] == "aws:ec2:stop-instances"
    assert tmpl["stopConditions"][0]["source"] == "none"
    assert tmpl["tags"]["env"] == "test"


@mock_aws
def test_delete_experiment_template():
    client = boto3.client("fis", region_name="eu-west-1")
    created = client.create_experiment_template(
        clientToken="token-del",
        description="to delete",
        stopConditions=[{"source": "none"}],
        targets={
            "t1": {
                "resourceType": "aws:ec2:instance",
                "resourceArns": ["arn:aws:ec2:eu-west-1:123456789012:instance/i-abc"],
                "selectionMode": "ALL",
            }
        },
        actions={
            "a1": {
                "actionId": "aws:ec2:stop-instances",
                "parameters": {},
                "targets": {"Instances": "t1"},
            }
        },
        roleArn="arn:aws:iam::123456789012:role/FISRole",
    )
    template_id = created["experimentTemplate"]["id"]
    resp = client.delete_experiment_template(id=template_id)
    assert resp["experimentTemplate"]["id"] == template_id


@mock_aws
def test_tag_resource():
    client = boto3.client("fis", region_name="eu-west-1")
    created = client.create_experiment_template(
        clientToken="token-tag",
        description="tag me",
        stopConditions=[{"source": "none"}],
        targets={
            "t1": {
                "resourceType": "aws:ec2:instance",
                "resourceArns": ["arn:aws:ec2:eu-west-1:123456789012:instance/i-def"],
                "selectionMode": "ALL",
            }
        },
        actions={
            "a1": {
                "actionId": "aws:ec2:stop-instances",
                "parameters": {},
                "targets": {"Instances": "t1"},
            }
        },
        roleArn="arn:aws:iam::123456789012:role/FISRole",
    )
    arn = created["experimentTemplate"]["arn"]
    client.tag_resource(resourceArn=arn, tags={"k1": "v1", "k2": "v2"})
    tags = client.list_tags_for_resource(resourceArn=arn)["tags"]
    assert tags["k1"] == "v1"
    assert tags["k2"] == "v2"


@mock_aws
def test_untag_resource():
    client = boto3.client("fis", region_name="us-east-2")
    created = client.create_experiment_template(
        clientToken="token-untag",
        description="untag me",
        stopConditions=[{"source": "none"}],
        targets={
            "t1": {
                "resourceType": "aws:ec2:instance",
                "resourceArns": ["arn:aws:ec2:us-east-2:123456789012:instance/i-ghi"],
                "selectionMode": "ALL",
            }
        },
        actions={
            "a1": {
                "actionId": "aws:ec2:stop-instances",
                "parameters": {},
                "targets": {"Instances": "t1"},
            }
        },
        roleArn="arn:aws:iam::123456789012:role/FISRole",
    )
    arn = created["experimentTemplate"]["arn"]
    client.tag_resource(resourceArn=arn, tags={"k1": "v1", "k2": "v2"})
    client.untag_resource(resourceArn=arn, tagKeys=["k1"])
    tags = client.list_tags_for_resource(resourceArn=arn)["tags"]
    assert "k1" not in tags
    assert tags["k2"] == "v2"


@mock_aws
def test_list_tags_for_resource():
    client = boto3.client("fis", region_name="us-east-2")
    created = client.create_experiment_template(
        clientToken="token-list",
        description="list tags",
        stopConditions=[{"source": "none"}],
        targets={
            "t1": {
                "resourceType": "aws:ec2:instance",
                "resourceArns": ["arn:aws:ec2:us-east-2:123456789012:instance/i-jkl"],
                "selectionMode": "ALL",
            }
        },
        actions={
            "a1": {
                "actionId": "aws:ec2:stop-instances",
                "parameters": {},
                "targets": {"Instances": "t1"},
            }
        },
        roleArn="arn:aws:iam::123456789012:role/FISRole",
    )
    arn = created["experimentTemplate"]["arn"]
    client.tag_resource(resourceArn=arn, tags={"env": "test"})
    resp = client.list_tags_for_resource(resourceArn=arn)
    assert resp["tags"]["env"] == "test"
