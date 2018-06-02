from __future__ import unicode_literals

import json
from collections import OrderedDict

import boto3
from botocore.exceptions import ClientError
import sure  # noqa
# Ensure 'assert_raises' context manager support for Python 2.6
from nose.tools import assert_raises

from moto import mock_cloudformation, mock_s3, mock_sqs, mock_ec2

dummy_template = {
    "AWSTemplateFormatVersion": "2010-09-09",
    "Description": "Stack 1",
    "Resources": {
        "EC2Instance1": {
            "Type": "AWS::EC2::Instance",
            "Properties": {
                "ImageId": "ami-d3adb33f",
                "KeyName": "dummy",
                "InstanceType": "t2.micro",
                "Tags": [
                    {
                        "Key": "Description",
                        "Value": "Test tag"
                    },
                    {
                        "Key": "Name",
                        "Value": "Name tag for tests"
                    }
                ]
            }
        }
    }
}

dummy_template_yaml = """---
AWSTemplateFormatVersion: 2010-09-09
Description: Stack1 with yaml template
Resources:
  EC2Instance1:
    Type: AWS::EC2::Instance
    Properties:
      ImageId: ami-d3adb33f
      KeyName: dummy
      InstanceType: t2.micro
      Tags:
        - Key: Description
          Value: Test tag
        - Key: Name
          Value: Name tag for tests
"""

dummy_template_yaml_with_short_form_func = """---
AWSTemplateFormatVersion: 2010-09-09
Description: Stack1 with yaml template
Resources:
  EC2Instance1:
    Type: AWS::EC2::Instance
    Properties:
      ImageId: ami-d3adb33f
      KeyName: !Join [ ":", [ du, m, my ] ]
      InstanceType: t2.micro
      Tags:
        - Key: Description
          Value: Test tag
        - Key: Name
          Value: Name tag for tests
"""

dummy_template_yaml_with_ref = """---
AWSTemplateFormatVersion: 2010-09-09
Description: Stack1 with yaml template
Parameters:
  TagDescription:
    Type: String
  TagName:
    Type: String

Resources:
  EC2Instance1:
    Type: AWS::EC2::Instance
    Properties:
      ImageId: ami-d3adb33f
      KeyName: dummy
      InstanceType: t2.micro
      Tags:
        - Key: Description
          Value:
            Ref: TagDescription
        - Key: Name
          Value: !Ref TagName
"""

dummy_update_template = {
    "AWSTemplateFormatVersion": "2010-09-09",
    "Parameters": {
        "KeyName": {
            "Description": "Name of an existing EC2 KeyPair",
            "Type": "AWS::EC2::KeyPair::KeyName",
            "ConstraintDescription": "must be the name of an existing EC2 KeyPair."
        }
    },
    "Resources": {
        "Instance": {
            "Type": "AWS::EC2::Instance",
            "Properties": {
                "ImageId": "ami-08111162"
            }
        }
    }
}

dummy_output_template = {
    "AWSTemplateFormatVersion": "2010-09-09",
    "Description": "Stack 1",
    "Resources": {
        "Instance": {
            "Type": "AWS::EC2::Instance",
            "Properties": {
                "ImageId": "ami-08111162"
            }
        }
    },
    "Outputs": {
        "StackVPC": {
            "Description": "The ID of the VPC",
            "Value": "VPCID",
            "Export": {
                "Name": "My VPC ID"
            }
        }
    }
}

dummy_import_template = {
    "AWSTemplateFormatVersion": "2010-09-09",
    "Resources": {
        "Queue": {
            "Type": "AWS::SQS::Queue",
            "Properties": {
                "QueueName": {"Fn::ImportValue": 'My VPC ID'},
                "VisibilityTimeout": 60,
            }
        }
    }
}

dummy_redrive_template = {
    "AWSTemplateFormatVersion": "2010-09-09",
    "Resources": {
        "MainQueue": {
            "Type": "AWS::SQS::Queue",
            "Properties": {
                "QueueName": "mainqueue.fifo",
                "FifoQueue": True,
                "ContentBasedDeduplication": False,
                "RedrivePolicy": {
                    "deadLetterTargetArn": {
                        "Fn::GetAtt": [
                            "DeadLetterQueue",
                            "Arn"
                        ]
                    },
                    "maxReceiveCount": 5
                }
            }
        },
        "DeadLetterQueue": {
            "Type": "AWS::SQS::Queue",
            "Properties": {
                "FifoQueue": True
            }
        },
    }
}

dummy_template_json = json.dumps(dummy_template)
dummy_update_template_json = json.dumps(dummy_update_template)
dummy_output_template_json = json.dumps(dummy_output_template)
dummy_import_template_json = json.dumps(dummy_import_template)
dummy_redrive_template_json = json.dumps(dummy_redrive_template)



@mock_cloudformation
def test_boto3_create_stack():
    cf_conn = boto3.client('cloudformation', region_name='us-east-1')
    cf_conn.create_stack(
        StackName="test_stack",
        TemplateBody=dummy_template_json,
    )

    cf_conn.get_template(StackName="test_stack")['TemplateBody'].should.equal(
        json.loads(dummy_template_json, object_pairs_hook=OrderedDict))


@mock_cloudformation
def test_boto3_create_stack_with_yaml():
    cf_conn = boto3.client('cloudformation', region_name='us-east-1')
    cf_conn.create_stack(
        StackName="test_stack",
        TemplateBody=dummy_template_yaml,
    )

    cf_conn.get_template(StackName="test_stack")['TemplateBody'].should.equal(
        dummy_template_yaml)


@mock_cloudformation
def test_boto3_create_stack_with_short_form_func_yaml():
    cf_conn = boto3.client('cloudformation', region_name='us-east-1')
    cf_conn.create_stack(
        StackName="test_stack",
        TemplateBody=dummy_template_yaml_with_short_form_func,
    )

    cf_conn.get_template(StackName="test_stack")['TemplateBody'].should.equal(
        dummy_template_yaml_with_short_form_func)


@mock_cloudformation
def test_boto3_create_stack_with_ref_yaml():
    cf_conn = boto3.client('cloudformation', region_name='us-east-1')
    params = [
        {'ParameterKey': 'TagDescription', 'ParameterValue': 'desc_ref'},
        {'ParameterKey': 'TagName', 'ParameterValue': 'name_ref'},
    ]
    cf_conn.create_stack(
        StackName="test_stack",
        TemplateBody=dummy_template_yaml_with_ref,
        Parameters=params
    )

    cf_conn.get_template(StackName="test_stack")['TemplateBody'].should.equal(
        dummy_template_yaml_with_ref)


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
    stack.notification_arns.should.contain(
        'arn:aws:sns:us-east-1:123456789012:fake-queue')


@mock_cloudformation
def test_create_stack_with_role_arn():
    cf = boto3.resource('cloudformation', region_name='us-east-1')
    cf.create_stack(
        StackName="test_stack_with_notifications",
        TemplateBody=dummy_template_json,
        RoleARN='arn:aws:iam::123456789012:role/moto',
    )
    stack = list(cf.stacks.all())[0]
    stack.role_arn.should.equal('arn:aws:iam::123456789012:role/moto')


@mock_cloudformation
@mock_s3
def test_create_stack_from_s3_url():
    s3 = boto3.client('s3')
    s3_conn = boto3.resource('s3')
    bucket = s3_conn.create_bucket(Bucket="foobar")

    key = s3_conn.Object(
        'foobar', 'template-key').put(Body=dummy_template_json)
    key_url = s3.generate_presigned_url(
        ClientMethod='get_object',
        Params={
            'Bucket': 'foobar',
            'Key': 'template-key'
        }
    )

    cf_conn = boto3.client('cloudformation', region_name='us-west-1')
    cf_conn.create_stack(
        StackName='stack_from_url',
        TemplateURL=key_url,
    )
    cf_conn.get_template(StackName="stack_from_url")['TemplateBody'].should.equal(
        json.loads(dummy_template_json, object_pairs_hook=OrderedDict))


@mock_cloudformation
def test_update_stack_with_previous_value():
    name = 'update_stack_with_previous_value'
    cf_conn = boto3.client('cloudformation', region_name='us-east-1')
    cf_conn.create_stack(
        StackName=name, TemplateBody=dummy_template_yaml_with_ref,
        Parameters=[
            {'ParameterKey': 'TagName', 'ParameterValue': 'foo'},
            {'ParameterKey': 'TagDescription', 'ParameterValue': 'bar'},
        ]
    )
    cf_conn.update_stack(
        StackName=name, UsePreviousTemplate=True,
        Parameters=[
            {'ParameterKey': 'TagName', 'UsePreviousValue': True},
            {'ParameterKey': 'TagDescription', 'ParameterValue': 'not bar'},
        ]
    )
    stack = cf_conn.describe_stacks(StackName=name)['Stacks'][0]
    tag_name = [x['ParameterValue'] for x in stack['Parameters']
                if x['ParameterKey'] == 'TagName'][0]
    tag_desc = [x['ParameterValue'] for x in stack['Parameters']
                if x['ParameterKey'] == 'TagDescription'][0]
    assert tag_name == 'foo'
    assert tag_desc == 'not bar'


@mock_cloudformation
@mock_s3
@mock_ec2
def test_update_stack_from_s3_url():
    s3 = boto3.client('s3')
    s3_conn = boto3.resource('s3')

    cf_conn = boto3.client('cloudformation', region_name='us-east-1')
    cf_conn.create_stack(
        StackName="update_stack_from_url",
        TemplateBody=dummy_template_json,
        Tags=[{'Key': 'foo', 'Value': 'bar'}],
    )

    s3_conn.create_bucket(Bucket="foobar")

    s3_conn.Object(
        'foobar', 'template-key').put(Body=dummy_update_template_json)
    key_url = s3.generate_presigned_url(
        ClientMethod='get_object',
        Params={
            'Bucket': 'foobar',
            'Key': 'template-key'
        }
    )

    cf_conn.update_stack(
        StackName="update_stack_from_url",
        TemplateURL=key_url,
    )

    cf_conn.get_template(StackName="update_stack_from_url")[ 'TemplateBody'].should.equal(
        json.loads(dummy_update_template_json, object_pairs_hook=OrderedDict))


@mock_cloudformation
@mock_s3
def test_create_change_set_from_s3_url():
    s3 = boto3.client('s3')
    s3_conn = boto3.resource('s3')
    bucket = s3_conn.create_bucket(Bucket="foobar")

    key = s3_conn.Object(
        'foobar', 'template-key').put(Body=dummy_template_json)
    key_url = s3.generate_presigned_url(
        ClientMethod='get_object',
        Params={
            'Bucket': 'foobar',
            'Key': 'template-key'
        }
    )
    cf_conn = boto3.client('cloudformation', region_name='us-west-1')
    response = cf_conn.create_change_set(
        StackName='NewStack',
        TemplateURL=key_url,
        ChangeSetName='NewChangeSet',
        ChangeSetType='CREATE',
    )
    assert 'arn:aws:cloudformation:us-west-1:123456789:changeSet/NewChangeSet/' in response['Id']
    assert 'arn:aws:cloudformation:us-east-1:123456789:stack/NewStack' in response['StackId']


@mock_cloudformation
def test_execute_change_set_w_arn():
    cf_conn = boto3.client('cloudformation', region_name='us-east-1')
    change_set = cf_conn.create_change_set(
        StackName='NewStack',
        TemplateBody=dummy_template_json,
        ChangeSetName='NewChangeSet',
        ChangeSetType='CREATE',
    )
    cf_conn.execute_change_set(ChangeSetName=change_set['Id'])


@mock_cloudformation
def test_execute_change_set_w_name():
    cf_conn = boto3.client('cloudformation', region_name='us-east-1')
    change_set = cf_conn.create_change_set(
        StackName='NewStack',
        TemplateBody=dummy_template_json,
        ChangeSetName='NewChangeSet',
        ChangeSetType='CREATE',
    )
    cf_conn.execute_change_set(ChangeSetName='NewStack', StackName='NewStack')


@mock_cloudformation
def test_describe_stack_pagination():
    conn = boto3.client('cloudformation', region_name='us-east-1')
    for i in range(100):
        conn.create_stack(
            StackName="test_stack",
            TemplateBody=dummy_template_json,
        )

    resp = conn.describe_stacks()
    stacks = resp['Stacks']
    stacks.should.have.length_of(50)
    next_token = resp['NextToken']
    next_token.should_not.be.none
    resp2 = conn.describe_stacks(NextToken=next_token)
    stacks.extend(resp2['Stacks'])
    stacks.should.have.length_of(100)
    assert 'NextToken' not in resp2.keys()


@mock_cloudformation
def test_describe_stack_resources():
    cf_conn = boto3.client('cloudformation', region_name='us-east-1')
    cf_conn.create_stack(
        StackName="test_stack",
        TemplateBody=dummy_template_json,
    )

    stack = cf_conn.describe_stacks(StackName="test_stack")['Stacks'][0]

    response = cf_conn.describe_stack_resources(StackName=stack['StackName'])
    resource = response['StackResources'][0]
    resource['LogicalResourceId'].should.equal('EC2Instance1')
    resource['ResourceStatus'].should.equal('CREATE_COMPLETE')
    resource['ResourceType'].should.equal('AWS::EC2::Instance')
    resource['StackId'].should.equal(stack['StackId'])


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
    stack_by_id = cf_conn.describe_stacks(StackName=stack['StackId'])['Stacks'][
        0]

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
@mock_ec2
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
@mock_ec2
def test_describe_updated_stack():
    cf_conn = boto3.client('cloudformation', region_name='us-east-1')
    cf_conn.create_stack(
        StackName="test_stack",
        TemplateBody=dummy_template_json,
        Tags=[{'Key': 'foo', 'Value': 'bar'}],
    )

    cf_conn.update_stack(
        StackName="test_stack",
        RoleARN='arn:aws:iam::123456789012:role/moto',
        TemplateBody=dummy_update_template_json,
        Tags=[{'Key': 'foo', 'Value': 'baz'}],
    )

    stack = cf_conn.describe_stacks(StackName="test_stack")['Stacks'][0]
    stack_id = stack['StackId']
    stack_by_id = cf_conn.describe_stacks(StackName=stack_id)['Stacks'][0]
    stack_by_id['StackId'].should.equal(stack['StackId'])
    stack_by_id['StackName'].should.equal("test_stack")
    stack_by_id['StackStatus'].should.equal("UPDATE_COMPLETE")
    stack_by_id['RoleARN'].should.equal('arn:aws:iam::123456789012:role/moto')
    stack_by_id['Tags'].should.equal([{'Key': 'foo', 'Value': 'baz'}])


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
    observed_tag_items = set(
        item for items in [tag.items() for tag in stack.tags] for item in items)
    expected_tag_items = set(
        item for items in [tag.items() for tag in tags] for item in items)
    observed_tag_items.should.equal(expected_tag_items)


@mock_cloudformation
@mock_ec2
def test_stack_events():
    cf = boto3.resource('cloudformation', region_name='us-east-1')
    stack = cf.create_stack(
        StackName="test_stack",
        TemplateBody=dummy_template_json,
    )
    stack.update(TemplateBody=dummy_update_template_json)
    stack = cf.Stack(stack.stack_id)
    stack.delete()

    # assert begins and ends with stack events
    events = list(stack.events.all())
    events[0].resource_type.should.equal("AWS::CloudFormation::Stack")
    events[-1].resource_type.should.equal("AWS::CloudFormation::Stack")

    # testing ordering of stack events without assuming resource events will not exist
    # the AWS API returns events in reverse chronological order
    stack_events_to_look_for = iter([
        ("DELETE_COMPLETE", None),
        ("DELETE_IN_PROGRESS", "User Initiated"),
        ("UPDATE_COMPLETE", None),
        ("UPDATE_IN_PROGRESS", "User Initiated"),
        ("CREATE_COMPLETE", None),
        ("CREATE_IN_PROGRESS", "User Initiated"),
    ])
    try:
        for event in events:
            event.stack_id.should.equal(stack.stack_id)
            event.stack_name.should.equal("test_stack")
            event.event_id.should.match(r"[0-9a-f]{8}-([0-9a-f]{4}-){3}[0-9a-f]{12}")

            if event.resource_type == "AWS::CloudFormation::Stack":
                event.logical_resource_id.should.equal("test_stack")
                event.physical_resource_id.should.equal(stack.stack_id)

                status_to_look_for, reason_to_look_for = next(
                    stack_events_to_look_for)
                event.resource_status.should.equal(status_to_look_for)
                if reason_to_look_for is not None:
                    event.resource_status_reason.should.equal(
                        reason_to_look_for)
    except StopIteration:
        assert False, "Too many stack events"

    list(stack_events_to_look_for).should.be.empty


@mock_cloudformation
def test_list_exports():
    cf_client = boto3.client('cloudformation', region_name='us-east-1')
    cf_resource = boto3.resource('cloudformation', region_name='us-east-1')
    stack = cf_resource.create_stack(
        StackName="test_stack",
        TemplateBody=dummy_output_template_json,
    )
    output_value = 'VPCID'
    exports = cf_client.list_exports()['Exports']

    stack.outputs.should.have.length_of(1)
    stack.outputs[0]['OutputValue'].should.equal(output_value)

    exports.should.have.length_of(1)
    exports[0]['ExportingStackId'].should.equal(stack.stack_id)
    exports[0]['Name'].should.equal('My VPC ID')
    exports[0]['Value'].should.equal(output_value)


@mock_cloudformation
def test_list_exports_with_token():
    cf = boto3.client('cloudformation', region_name='us-east-1')
    for i in range(101):
        # Add index to ensure name is unique
        dummy_output_template['Outputs']['StackVPC']['Export']['Name'] += str(i)
        cf.create_stack(
            StackName="test_stack",
            TemplateBody=json.dumps(dummy_output_template),
        )
    exports = cf.list_exports()
    exports['Exports'].should.have.length_of(100)
    exports.get('NextToken').should_not.be.none

    more_exports = cf.list_exports(NextToken=exports['NextToken'])
    more_exports['Exports'].should.have.length_of(1)
    more_exports.get('NextToken').should.be.none


@mock_cloudformation
def test_delete_stack_with_export():
    cf = boto3.client('cloudformation', region_name='us-east-1')
    stack = cf.create_stack(
        StackName="test_stack",
        TemplateBody=dummy_output_template_json,
    )

    stack_id = stack['StackId']
    exports = cf.list_exports()['Exports']
    exports.should.have.length_of(1)

    cf.delete_stack(StackName=stack_id)
    cf.list_exports()['Exports'].should.have.length_of(0)


@mock_cloudformation
def test_export_names_must_be_unique():
    cf = boto3.resource('cloudformation', region_name='us-east-1')
    first_stack = cf.create_stack(
        StackName="test_stack",
        TemplateBody=dummy_output_template_json,
    )
    with assert_raises(ClientError):
        cf.create_stack(
            StackName="test_stack",
            TemplateBody=dummy_output_template_json,
        )


@mock_sqs
@mock_cloudformation
def test_stack_with_imports():
    cf = boto3.resource('cloudformation', region_name='us-east-1')
    ec2_resource = boto3.resource('sqs', region_name='us-east-1')

    output_stack = cf.create_stack(
        StackName="test_stack1",
        TemplateBody=dummy_output_template_json,
    )
    import_stack = cf.create_stack(
        StackName="test_stack2",
        TemplateBody=dummy_import_template_json
    )

    output_stack.outputs.should.have.length_of(1)
    output = output_stack.outputs[0]['OutputValue']
    queue = ec2_resource.get_queue_by_name(QueueName=output)
    queue.should_not.be.none


@mock_sqs
@mock_cloudformation
def test_non_json_redrive_policy():
    cf = boto3.resource('cloudformation', region_name='us-east-1')

    stack = cf.create_stack(
        StackName="test_stack1",
        TemplateBody=dummy_redrive_template_json
    )

    stack.Resource('MainQueue').resource_status\
        .should.equal("CREATE_COMPLETE")
    stack.Resource('DeadLetterQueue').resource_status\
        .should.equal("CREATE_COMPLETE")
