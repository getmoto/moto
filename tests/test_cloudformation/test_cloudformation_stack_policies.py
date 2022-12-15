import boto3
import json

import pytest

from botocore.exceptions import ClientError
from moto import mock_cloudformation, mock_s3
from .test_cloudformation_stack_crud_boto3 import dummy_template_json


@mock_cloudformation
def test_set_stack_policy_on_nonexisting_stack():
    cf_conn = boto3.client("cloudformation", region_name="us-east-1")

    with pytest.raises(ClientError) as exc:
        cf_conn.set_stack_policy(StackName="unknown", StackPolicyBody="{}")
    err = exc.value.response["Error"]
    err["Code"].should.equal("ValidationError")
    err["Message"].should.equal("Stack: unknown does not exist")
    err["Type"].should.equal("Sender")


@mock_cloudformation
def test_get_stack_policy_on_nonexisting_stack():
    cf_conn = boto3.client("cloudformation", region_name="us-east-1")

    with pytest.raises(ClientError) as exc:
        cf_conn.get_stack_policy(StackName="unknown")
    err = exc.value.response["Error"]
    err["Code"].should.equal("ValidationError")
    err["Message"].should.equal("Stack: unknown does not exist")
    err["Type"].should.equal("Sender")


@mock_cloudformation
def test_get_stack_policy_on_stack_without_policy():
    cf_conn = boto3.client("cloudformation", region_name="us-east-1")
    cf_conn.create_stack(StackName="test_stack", TemplateBody=dummy_template_json)

    resp = cf_conn.get_stack_policy(StackName="test_stack")
    resp.shouldnt.have.key("StackPolicyBody")


@mock_cloudformation
def test_set_stack_policy_with_both_body_and_url():
    cf_conn = boto3.client("cloudformation", region_name="us-east-1")
    cf_conn.create_stack(StackName="test_stack", TemplateBody=dummy_template_json)

    with pytest.raises(ClientError) as exc:
        cf_conn.set_stack_policy(
            StackName="test_stack", StackPolicyBody="{}", StackPolicyURL="..."
        )
    err = exc.value.response["Error"]
    err["Code"].should.equal("ValidationError")
    err["Message"].should.equal(
        "You cannot specify both StackPolicyURL and StackPolicyBody"
    )
    err["Type"].should.equal("Sender")


@mock_cloudformation
def test_set_stack_policy_with_body():
    cf_conn = boto3.client("cloudformation", region_name="us-east-1")
    cf_conn.create_stack(StackName="test_stack", TemplateBody=dummy_template_json)

    policy = json.dumps({"policy": "yes"})

    cf_conn.set_stack_policy(StackName="test_stack", StackPolicyBody=policy)

    resp = cf_conn.get_stack_policy(StackName="test_stack")
    resp.should.have.key("StackPolicyBody").equals(policy)


@mock_cloudformation
def test_set_stack_policy_on_create():
    cf_conn = boto3.client("cloudformation", region_name="us-east-1")
    cf_conn.create_stack(
        StackName="test_stack",
        TemplateBody=dummy_template_json,
        StackPolicyBody="stack_policy_body",
    )

    resp = cf_conn.get_stack_policy(StackName="test_stack")
    resp.should.have.key("StackPolicyBody").equals("stack_policy_body")


@mock_cloudformation
@mock_s3
def test_set_stack_policy_with_url():
    cf_conn = boto3.client("cloudformation", region_name="us-east-1")
    cf_conn.create_stack(StackName="test_stack", TemplateBody=dummy_template_json)

    policy = json.dumps({"policy": "yes"})
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket="foobar")
    s3.put_object(Bucket="foobar", Key="test", Body=policy)
    key_url = s3.generate_presigned_url(
        ClientMethod="get_object", Params={"Bucket": "foobar", "Key": "test"}
    )

    cf_conn.set_stack_policy(StackName="test_stack", StackPolicyURL=key_url)

    resp = cf_conn.get_stack_policy(StackName="test_stack")
    resp.should.have.key("StackPolicyBody").equals(policy)


@mock_cloudformation
@mock_s3
def test_set_stack_policy_with_url_pointing_to_unknown_key():
    cf_conn = boto3.client("cloudformation", region_name="us-east-1")
    cf_conn.create_stack(StackName="test_stack", TemplateBody=dummy_template_json)

    with pytest.raises(ClientError) as exc:
        cf_conn.set_stack_policy(StackName="test_stack", StackPolicyURL="...")
    err = exc.value.response["Error"]
    err["Code"].should.equal("ValidationError")
    err["Message"].should.contain("S3 error: Access Denied")
    err["Type"].should.equal("Sender")
