from __future__ import unicode_literals

import json

import boto
import boto.s3
import boto.s3.key
import boto.cloudformation
from boto.exception import BotoServerError
import sure  # noqa
# Ensure 'assert_raises' context manager support for Python 2.6
import tests.backport_assert_raises  # noqa
from nose.tools import assert_raises

from moto import mock_cloudformation, mock_s3
from moto.cloudformation import cloudformation_backends

dummy_template = {
    "AWSTemplateFormatVersion": "2010-09-09",
    "Description": "Stack 1",
    "Resources": {},
}

dummy_template2 = {
    "AWSTemplateFormatVersion": "2010-09-09",
    "Description": "Stack 2",
    "Resources": {},
}

# template with resource which has no delete attribute defined
dummy_template3 = {
    "AWSTemplateFormatVersion": "2010-09-09",
    "Description": "Stack 3",
    "Resources": {
        "VPC": {
            "Properties": {
                "CidrBlock": "192.168.0.0/16",
        },
        "Type": "AWS::EC2::VPC"
        }
    },
}

dummy_template_json = json.dumps(dummy_template)
dummy_template_json2 = json.dumps(dummy_template2)
dummy_template_json3 = json.dumps(dummy_template3)


@mock_cloudformation
def test_create_stack():
    conn = boto.connect_cloudformation()
    conn.create_stack(
        "test_stack",
        template_body=dummy_template_json,
    )

    stack = conn.describe_stacks()[0]
    stack.stack_name.should.equal('test_stack')
    stack.get_template().should.equal({
        'GetTemplateResponse': {
            'GetTemplateResult': {
                'TemplateBody': dummy_template_json,
                'ResponseMetadata': {
                    'RequestId': '2d06e36c-ac1d-11e0-a958-f9382b6eb86bEXAMPLE'
                }
            }
        }

    })


@mock_cloudformation
def test_creating_stacks_across_regions():
    west1_conn = boto.cloudformation.connect_to_region("us-west-1")
    west1_conn.create_stack("test_stack", template_body=dummy_template_json)

    west2_conn = boto.cloudformation.connect_to_region("us-west-2")
    west2_conn.create_stack("test_stack", template_body=dummy_template_json)

    list(west1_conn.describe_stacks()).should.have.length_of(1)
    list(west2_conn.describe_stacks()).should.have.length_of(1)


@mock_cloudformation
def test_create_stack_with_notification_arn():
    conn = boto.connect_cloudformation()
    conn.create_stack(
        "test_stack_with_notifications",
        template_body=dummy_template_json,
        notification_arns='arn:aws:sns:us-east-1:123456789012:fake-queue'
    )

    stack = conn.describe_stacks()[0]
    [n.value for n in stack.notification_arns].should.contain('arn:aws:sns:us-east-1:123456789012:fake-queue')


@mock_cloudformation
@mock_s3
def test_create_stack_from_s3_url():
    s3_conn = boto.s3.connect_to_region('us-west-1')
    bucket = s3_conn.create_bucket("foobar")
    key = boto.s3.key.Key(bucket)
    key.key = "template-key"
    key.set_contents_from_string(dummy_template_json)
    key_url = key.generate_url(expires_in=0, query_auth=False)

    conn = boto.cloudformation.connect_to_region('us-west-1')
    conn.create_stack('new-stack', template_url=key_url)

    stack = conn.describe_stacks()[0]
    stack.stack_name.should.equal('new-stack')
    stack.get_template().should.equal(
        {
        'GetTemplateResponse': {
            'GetTemplateResult': {
                'TemplateBody': dummy_template_json,
                'ResponseMetadata': {
                    'RequestId': '2d06e36c-ac1d-11e0-a958-f9382b6eb86bEXAMPLE'
                }
            }
        }

    })


@mock_cloudformation
def test_describe_stack_by_name():
    conn = boto.connect_cloudformation()
    conn.create_stack(
        "test_stack",
        template_body=dummy_template_json,
    )

    stack = conn.describe_stacks("test_stack")[0]
    stack.stack_name.should.equal('test_stack')


@mock_cloudformation
def test_describe_stack_by_stack_id():
    conn = boto.connect_cloudformation()
    conn.create_stack(
        "test_stack",
        template_body=dummy_template_json,
    )

    stack = conn.describe_stacks("test_stack")[0]
    stack_by_id = conn.describe_stacks(stack.stack_id)[0]
    stack_by_id.stack_id.should.equal(stack.stack_id)
    stack_by_id.stack_name.should.equal("test_stack")


@mock_cloudformation
def test_describe_deleted_stack():
    conn = boto.connect_cloudformation()
    conn.create_stack(
        "test_stack",
        template_body=dummy_template_json,
    )

    stack = conn.describe_stacks("test_stack")[0]
    stack_id = stack.stack_id
    conn.delete_stack(stack.stack_id)
    stack_by_id = conn.describe_stacks(stack_id)[0]
    stack_by_id.stack_id.should.equal(stack.stack_id)
    stack_by_id.stack_name.should.equal("test_stack")
    stack_by_id.stack_status.should.equal("DELETE_COMPLETE")


@mock_cloudformation
def test_get_template_by_name():
    conn = boto.connect_cloudformation()
    conn.create_stack(
        "test_stack",
        template_body=dummy_template_json,
    )

    template = conn.get_template("test_stack")
    template.should.equal({
        'GetTemplateResponse': {
            'GetTemplateResult': {
                'TemplateBody': dummy_template_json,
                'ResponseMetadata': {
                    'RequestId': '2d06e36c-ac1d-11e0-a958-f9382b6eb86bEXAMPLE'
                }
            }
        }

    })


@mock_cloudformation
def test_list_stacks():
    conn = boto.connect_cloudformation()
    conn.create_stack(
        "test_stack",
        template_body=dummy_template_json,
    )
    conn.create_stack(
        "test_stack2",
        template_body=dummy_template_json,
    )

    stacks = conn.list_stacks()
    stacks.should.have.length_of(2)
    stacks[0].template_description.should.equal("Stack 1")


@mock_cloudformation
def test_delete_stack_by_name():
    conn = boto.connect_cloudformation()
    conn.create_stack(
        "test_stack",
        template_body=dummy_template_json,
    )

    conn.list_stacks().should.have.length_of(1)
    conn.delete_stack("test_stack")
    conn.list_stacks().should.have.length_of(0)


@mock_cloudformation
def test_delete_stack_by_id():
    conn = boto.connect_cloudformation()
    stack_id = conn.create_stack(
        "test_stack",
        template_body=dummy_template_json,
    )

    conn.list_stacks().should.have.length_of(1)
    conn.delete_stack(stack_id)
    conn.list_stacks().should.have.length_of(0)
    with assert_raises(BotoServerError):
        conn.describe_stacks("test_stack")

    conn.describe_stacks(stack_id).should.have.length_of(1)


@mock_cloudformation
def test_delete_stack_with_resource_missing_delete_attr():
    conn = boto.connect_cloudformation()
    conn.create_stack(
        "test_stack",
        template_body=dummy_template_json3,
    )

    conn.list_stacks().should.have.length_of(1)
    conn.delete_stack("test_stack")
    conn.list_stacks().should.have.length_of(0)


@mock_cloudformation
def test_bad_describe_stack():
    conn = boto.connect_cloudformation()
    with assert_raises(BotoServerError):
        conn.describe_stacks("bad_stack")


@mock_cloudformation()
def test_cloudformation_params():
    dummy_template = {
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
    dummy_template_json = json.dumps(dummy_template)
    cfn = boto.connect_cloudformation()
    cfn.create_stack('test_stack1', template_body=dummy_template_json, parameters=[('APPNAME', 'testing123')])
    stack = cfn.describe_stacks('test_stack1')[0]
    stack.parameters.should.have.length_of(1)
    param = stack.parameters[0]
    param.key.should.equal('APPNAME')
    param.value.should.equal('testing123')


@mock_cloudformation
def test_stack_tags():
    conn = boto.connect_cloudformation()
    conn.create_stack(
        "test_stack",
        template_body=dummy_template_json,
        tags={"foo": "bar", "baz": "bleh"},
    )

    stack = conn.describe_stacks()[0]
    dict(stack.tags).should.equal({"foo": "bar", "baz": "bleh"})


@mock_cloudformation
def test_update_stack():
    conn = boto.connect_cloudformation()
    conn.create_stack(
        "test_stack",
        template_body=dummy_template_json,
    )

    conn.update_stack("test_stack", dummy_template_json2)

    stack = conn.describe_stacks()[0]
    stack.stack_status.should.equal("UPDATE_COMPLETE")
    stack.get_template().should.equal({
        'GetTemplateResponse': {
            'GetTemplateResult': {
                'TemplateBody': dummy_template_json2,
                'ResponseMetadata': {
                    'RequestId': '2d06e36c-ac1d-11e0-a958-f9382b6eb86bEXAMPLE'
                }
            }
        }
    })


@mock_cloudformation
def test_update_stack():
    conn = boto.connect_cloudformation()
    conn.create_stack(
        "test_stack",
        template_body=dummy_template_json,
    )
    conn.update_stack("test_stack", use_previous_template=True)

    stack = conn.describe_stacks()[0]
    stack.stack_status.should.equal("UPDATE_COMPLETE")
    stack.get_template().should.equal({
        'GetTemplateResponse': {
            'GetTemplateResult': {
                'TemplateBody': dummy_template_json,
                'ResponseMetadata': {
                    'RequestId': '2d06e36c-ac1d-11e0-a958-f9382b6eb86bEXAMPLE'
                }
            }
        }
    })


@mock_cloudformation
def test_update_stack_when_rolled_back():
    conn = boto.connect_cloudformation()
    stack_id = conn.create_stack("test_stack", template_body=dummy_template_json)

    cloudformation_backends[conn.region.name].stacks[stack_id].status = 'ROLLBACK_COMPLETE'

    with assert_raises(BotoServerError) as err:
        conn.update_stack("test_stack", dummy_template_json)

    ex = err.exception
    ex.body.should.match(r'is in ROLLBACK_COMPLETE state and can not be updated')
    ex.error_code.should.equal('ValidationError')
    ex.reason.should.equal('Bad Request')
    ex.status.should.equal(400)

@mock_cloudformation
def test_describe_stack_events_shows_create_update_and_delete():
    conn = boto.connect_cloudformation()
    stack_id = conn.create_stack("test_stack", template_body=dummy_template_json)
    conn.update_stack(stack_id, template_body=dummy_template_json2)
    conn.delete_stack(stack_id)

    # assert begins and ends with stack events
    events = conn.describe_stack_events(stack_id)
    events[0].resource_type.should.equal("AWS::CloudFormation::Stack")
    events[-1].resource_type.should.equal("AWS::CloudFormation::Stack")

    # testing ordering of stack events without assuming resource events will not exist
    stack_events_to_look_for = iter([
        ("CREATE_IN_PROGRESS", "User Initiated"), ("CREATE_COMPLETE", None),
        ("UPDATE_IN_PROGRESS", "User Initiated"), ("UPDATE_COMPLETE", None),
        ("DELETE_IN_PROGRESS", "User Initiated"), ("DELETE_COMPLETE", None)])
    try:
        for event in events:
            event.stack_id.should.equal(stack_id)
            event.stack_name.should.equal("test_stack")

            if event.resource_type == "AWS::CloudFormation::Stack":
                event.logical_resource_id.should.equal("test_stack")
                event.physical_resource_id.should.equal(stack_id)

                status_to_look_for, reason_to_look_for = next(stack_events_to_look_for)
                event.resource_status.should.equal(status_to_look_for)
                if reason_to_look_for is not None:
                    event.resource_status_reason.should.equal(reason_to_look_for)
    except StopIteration:
        assert False, "Too many stack events"

    list(stack_events_to_look_for).should.be.empty

