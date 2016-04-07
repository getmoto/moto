from __future__ import unicode_literals

import boto3
import boto
import boto.s3
import boto.s3.key
from botocore.exceptions import ClientError
from moto import mock_cloudformation, mock_s3

import json
import sure  # noqa
# Ensure 'assert_raises' context manager support for Python 2.6
import tests.backport_assert_raises  # noqa
from nose.tools import assert_raises

dummy_template = {
    "AWSTemplateFormatVersion": "2010-09-09",
    "Description": "Stack 1",
    "Resources": {},
}

dummy_template_json = json.dumps(dummy_template)

@mock_cloudformation
def test_boto3_create_stack():
    cf_conn = boto3.client('cloudformation', region_name='us-east-1')
    cf_conn.create_stack(
        StackName="test_stack",
        TemplateBody=dummy_template_json,
    )

    cf_conn.get_template(StackName="test_stack")['TemplateBody'].should.equal(dummy_template)


@mock_cloudformation
def test_creating_stacks_across_regions():
    west1_cf = boto3.resource('cloudformation', region_name='us-west-1')
    west2_cf = boto3.resource('cloudformation', region_name='us-west-2')
    west1_cf.create_stack(
        StackName="test_stack",
        TemplateBody=dummy_template_json,
    )
    west2_cf.create_stack(
        StackName="test_stack",
        TemplateBody=dummy_template_json,
    )

    list(west1_cf.stacks.all()).should.have.length_of(1)
    list(west2_cf.stacks.all()).should.have.length_of(1)


@mock_cloudformation
def test_create_stack_with_notification_arn():
    cf = boto3.resource('cloudformation', region_name='us-east-1')
    cf.create_stack(
        StackName="test_stack_with_notifications",
        TemplateBody=dummy_template_json,
        NotificationARNs=['arn:aws:sns:us-east-1:123456789012:fake-queue'],
    )

    stack = list(cf.stacks.all())[0]
    stack.notification_arns.should.contain('arn:aws:sns:us-east-1:123456789012:fake-queue')


@mock_cloudformation
@mock_s3
def test_create_stack_from_s3_url():
    s3_conn = boto.s3.connect_to_region('us-west-1')
    bucket = s3_conn.create_bucket("foobar")
    key = boto.s3.key.Key(bucket)
    key.key = "template-key"
    key.set_contents_from_string(dummy_template_json)
    key_url = key.generate_url(expires_in=0, query_auth=False)

    cf_conn = boto3.client('cloudformation', region_name='us-west-1')
    cf_conn.create_stack(
        StackName='stack_from_url',
        TemplateURL=key_url,
    )

    cf_conn.get_template(StackName="stack_from_url")['TemplateBody'].should.equal(dummy_template)


@mock_cloudformation
def test_describe_stack_by_name():
    cf_conn = boto3.client('cloudformation', region_name='us-east-1')
    cf_conn.create_stack(
        StackName="test_stack",
        TemplateBody=dummy_template_json,
    )

    stack = cf_conn.describe_stacks(StackName="test_stack")['Stacks'][0]
    stack['StackName'].should.equal('test_stack')


@mock_cloudformation
def test_describe_stack_by_stack_id():
    cf_conn = boto3.client('cloudformation', region_name='us-east-1')
    cf_conn.create_stack(
        StackName="test_stack",
        TemplateBody=dummy_template_json,
    )

    stack = cf_conn.describe_stacks(StackName="test_stack")['Stacks'][0]
    stack_by_id = cf_conn.describe_stacks(StackName=stack['StackId'])['Stacks'][0]

    stack_by_id['StackId'].should.equal(stack['StackId'])
    stack_by_id['StackName'].should.equal("test_stack")


@mock_cloudformation
def test_list_stacks():
    cf = boto3.resource('cloudformation', region_name='us-east-1')
    cf.create_stack(
        StackName="test_stack",
        TemplateBody=dummy_template_json,
    )
    cf.create_stack(
        StackName="test_stack2",
        TemplateBody=dummy_template_json,
    )

    stacks = list(cf.stacks.all())
    stacks.should.have.length_of(2)
    stack_names = [stack.stack_name for stack in stacks]
    stack_names.should.contain("test_stack")
    stack_names.should.contain("test_stack2")


@mock_cloudformation
def test_delete_stack_from_resource():
    cf = boto3.resource('cloudformation', region_name='us-east-1')
    stack = cf.create_stack(
        StackName="test_stack",
        TemplateBody=dummy_template_json,
    )

    list(cf.stacks.all()).should.have.length_of(1)
    stack.delete()
    list(cf.stacks.all()).should.have.length_of(0)


@mock_cloudformation
def test_delete_stack_by_name():
    cf_conn = boto3.client('cloudformation', region_name='us-east-1')
    cf_conn.create_stack(
        StackName="test_stack",
        TemplateBody=dummy_template_json,
    )

    cf_conn.describe_stacks()['Stacks'].should.have.length_of(1)
    cf_conn.delete_stack(StackName="test_stack")
    cf_conn.describe_stacks()['Stacks'].should.have.length_of(0)


@mock_cloudformation
def test_describe_deleted_stack():
    cf_conn = boto3.client('cloudformation', region_name='us-east-1')
    cf_conn.create_stack(
        StackName="test_stack",
        TemplateBody=dummy_template_json,
    )

    stack = cf_conn.describe_stacks(StackName="test_stack")['Stacks'][0]
    stack_id = stack['StackId']
    cf_conn.delete_stack(StackName=stack['StackId'])
    stack_by_id = cf_conn.describe_stacks(StackName=stack_id)['Stacks'][0]
    stack_by_id['StackId'].should.equal(stack['StackId'])
    stack_by_id['StackName'].should.equal("test_stack")
    stack_by_id['StackStatus'].should.equal("DELETE_COMPLETE")


@mock_cloudformation
def test_bad_describe_stack():
    cf_conn = boto3.client('cloudformation', region_name='us-east-1')
    with assert_raises(ClientError):
        cf_conn.describe_stacks(StackName="non_existent_stack")


@mock_cloudformation()
def test_cloudformation_params():
    dummy_template_with_params = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Description": "Stack 1",
        "Resources": {},
        "Parameters": {
            "APPNAME": {
                "Default": "app-name",
                "Description": "The name of the app",
                "Type": "String"
            }
        }
    }
    dummy_template_with_params_json = json.dumps(dummy_template_with_params)

    cf = boto3.resource('cloudformation', region_name='us-east-1')
    stack = cf.create_stack(
        StackName='test_stack',
        TemplateBody=dummy_template_with_params_json,
        Parameters=[{
            "ParameterKey": "APPNAME",
            "ParameterValue": "testing123",
        }],
    )

    stack.parameters.should.have.length_of(1)
    param = stack.parameters[0]
    param['ParameterKey'].should.equal('APPNAME')
    param['ParameterValue'].should.equal('testing123')


@mock_cloudformation
def test_stack_tags():
    tags = [
        {
            "Key": "foo",
            "Value": "bar"
        },
        {
            "Key": "baz",
            "Value": "bleh"
        }
    ]
    cf = boto3.resource('cloudformation', region_name='us-east-1')
    stack = cf.create_stack(
        StackName="test_stack",
        TemplateBody=dummy_template_json,
        Tags=tags,
    )
    observed_tag_items = set(item for items in [tag.items() for tag in stack.tags] for item in items)
    expected_tag_items = set(item for items in [tag.items() for tag in tags] for item in items)
    observed_tag_items.should.equal(expected_tag_items)
