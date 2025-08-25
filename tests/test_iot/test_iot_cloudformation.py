import json
from datetime import datetime

import boto3
from dateutil.tz import tzlocal

from moto import mock_aws

TEST_REGION = "us-west-1"


@mock_aws
def test_create_thing_with_simple_cloudformation():
    # given
    stack_name = "test_stack"
    template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Description": "IOT Thing CloudFormation",
        "Resources": {
            "testThing": {
                "Type": "AWS::IoT::Thing",
            },
        },
        "Outputs": {
            "ThingArn": {"Value": {"Fn::GetAtt": ["testThing", "Arn"]}},
            "ThingId": {"Value": {"Fn::GetAtt": ["testThing", "Id"]}},
        },
    }

    # when
    template_json = json.dumps(template)
    cfn_conn = boto3.client("cloudformation", region_name=TEST_REGION)
    cfn_conn.create_stack(StackName=stack_name, TemplateBody=template_json)

    # then check list of things
    iot_conn = boto3.client("iot", region_name=TEST_REGION)
    things = iot_conn.list_things()["things"]
    assert len(things) == 1
    assert things[0]["thingName"].startswith("test_stack-testThing-")
    assert things[0]["thingArn"].startswith(
        "arn:aws:iot:us-west-1:123456789012:thing/test_stack-testThing-"
    )
    assert things[0]["attributes"] == {}


@mock_aws
def test_create_thing_with_attributes_through_cloudformation():
    # given
    test_thing_name = "Test_Thing"
    stack_name = "test_stack"

    thing_attributes = {"attributes": {"attr1": "value1", "attr2": "value2"}}
    template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Description": "IOT Thing CloudFormation",
        "Resources": {
            "testThing": {
                "Type": "AWS::IoT::Thing",
                "Properties": {
                    "ThingName": test_thing_name,
                    "AttributePayload": json.dumps(thing_attributes),
                },
            },
        },
        "Outputs": {
            "ThingArn": {"Value": {"Fn::GetAtt": ["testThing", "Arn"]}},
            "ThingId": {"Value": {"Fn::GetAtt": ["testThing", "Id"]}},
        },
    }

    # when
    template_json = json.dumps(template)
    cfn_conn = boto3.client("cloudformation", region_name=TEST_REGION)
    cfn_conn.create_stack(StackName=stack_name, TemplateBody=template_json)

    # then check list of things
    iot_conn = boto3.client("iot", region_name=TEST_REGION)
    assert len(iot_conn.list_things()["things"]) == 1

    # describe thing
    resp = iot_conn.describe_thing(thingName=test_thing_name)
    assert resp["thingName"] == test_thing_name
    assert resp["thingArn"] == "arn:aws:iot:us-west-1:123456789012:thing/Test_Thing"
    assert resp["attributes"] == thing_attributes["attributes"]

    # Check stack outputs
    stack = cfn_conn.describe_stacks(StackName=stack_name)["Stacks"][0]
    outputs = {
        Output["OutputKey"]: Output["OutputValue"] for Output in stack["Outputs"]
    }
    assert outputs["ThingArn"] == resp["thingArn"]
    assert outputs["ThingId"] == resp["thingId"]


@mock_aws
def test_update_thing_name_should_recreate_thing_and_change_id():
    # given
    test_thing_name = "Test_Thing"
    updated_thing_name = "Updated_Thing"
    stack_name = "test_stack"

    first_template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Description": "IOT Thing CloudFormation",
        "Resources": {
            "testThing": {
                "Type": "AWS::IoT::Thing",
                "Properties": {"ThingName": test_thing_name},
            },
        },
    }
    updated_template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Description": "IOT Thing CloudFormation",
        "Resources": {
            "testThing": {
                "Type": "AWS::IoT::Thing",
                "Properties": {"ThingName": updated_thing_name},
            },
        },
    }

    # when
    cfn_conn = boto3.client("cloudformation", region_name=TEST_REGION)
    cfn_conn.create_stack(StackName=stack_name, TemplateBody=json.dumps(first_template))

    # then check list of things and the only one thing
    iot_conn = boto3.client("iot", region_name=TEST_REGION)
    assert len(iot_conn.list_things()["things"]) == 1
    first_resp = iot_conn.describe_thing(thingName=test_thing_name)
    assert first_resp["thingName"] == test_thing_name
    assert (
        first_resp["thingArn"] == "arn:aws:iot:us-west-1:123456789012:thing/Test_Thing"
    )

    # and
    cfn_conn.update_stack(
        StackName=stack_name, TemplateBody=json.dumps(updated_template)
    )
    assert len(iot_conn.list_things()["things"]) == 1
    updated_resp = iot_conn.describe_thing(thingName=updated_thing_name)
    assert updated_resp["thingName"] == updated_thing_name
    assert (
        updated_resp["thingArn"]
        == "arn:aws:iot:us-west-1:123456789012:thing/Updated_Thing"
    )

    # and it's a different thing
    assert first_resp["thingId"] != updated_resp["thingId"]


@mock_aws
def test_delete_resource_should_delete_thing():
    # given
    test_thing_name = "Test_Thing"
    stack_name = "test_stack"

    first_template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Description": "IOT Thing CloudFormation",
        "Resources": {
            "testThing": {
                "Type": "AWS::IoT::Thing",
                "Properties": {
                    "ThingName": test_thing_name,
                },
            },
        },
    }

    # when
    cfn_conn = boto3.client("cloudformation", region_name=TEST_REGION)
    cfn_conn.create_stack(StackName=stack_name, TemplateBody=json.dumps(first_template))

    # then check list of things and the only one thing
    iot_conn = boto3.client("iot", region_name=TEST_REGION)
    assert len(iot_conn.list_things()["things"]) == 1

    # and
    cfn_conn.delete_stack(StackName=stack_name)
    assert len(iot_conn.list_things()["things"]) == 0


@mock_aws
def test_create_thingtype_with_simple_cloudformation():
    # given
    stack_name = "test_stack"
    template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Description": "IOT ThingType CloudFormation",
        "Resources": {
            "testThingType": {
                "Type": "AWS::IoT::ThingType",
            },
        },
        "Outputs": {
            "ThingTypeArn": {"Value": {"Fn::GetAtt": ["testThingType", "Arn"]}},
            "ThingTypeId": {"Value": {"Fn::GetAtt": ["testThingType", "Id"]}},
        },
    }

    # when
    cfn_conn = boto3.client("cloudformation", region_name=TEST_REGION)
    cfn_conn.create_stack(StackName=stack_name, TemplateBody=json.dumps(template))

    # then check list of things
    iot_conn = boto3.client("iot", region_name=TEST_REGION)
    thing_types = iot_conn.list_thing_types()["thingTypes"]
    assert len(thing_types) == 1
    assert thing_types[0]["thingTypeName"].startswith("test_stack-testThingType-")
    assert thing_types[0]["thingTypeArn"].startswith(
        "arn:aws:iot:us-west-1:123456789012:thingtype/test_stack-testThingType-"
    )

    # and check if they are the same as in a stack outputs
    stack = cfn_conn.describe_stacks(StackName=stack_name)["Stacks"][0]
    outputs = {
        Output["OutputKey"]: Output["OutputValue"] for Output in stack["Outputs"]
    }
    assert outputs["ThingTypeArn"] == thing_types[0]["thingTypeArn"]


@mock_aws
def test_update_thingtype_using_cloudformation_should_recreate_id():
    # given
    stack_name = "test_stack"
    initial_template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Description": "IOT ThingType CloudFormation",
        "Resources": {
            "testThingType": {
                "Type": "AWS::IoT::ThingType",
                "Properties": {"ThingTypeName": "TestThing1"},
            },
        },
    }

    updated_template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Description": "IOT ThingType CloudFormation",
        "Resources": {
            "testThingType": {
                "Type": "AWS::IoT::ThingType",
                "Properties": {"ThingTypeName": "TestThing2"},
            },
        },
    }

    # when
    cfn_conn = boto3.client("cloudformation", region_name=TEST_REGION)
    cfn_conn.create_stack(
        StackName=stack_name, TemplateBody=json.dumps(initial_template)
    )

    # then check list of things
    iot_conn = boto3.client("iot", region_name=TEST_REGION)
    initial_thing_types = iot_conn.list_thing_types()["thingTypes"]
    assert len(initial_thing_types) == 1
    assert initial_thing_types[0]["thingTypeName"] == "TestThing1"

    # then update
    cfn_conn.update_stack(
        StackName=stack_name, TemplateBody=json.dumps(updated_template)
    )
    updated_thing_types = iot_conn.list_thing_types()["thingTypes"]
    assert len(updated_thing_types) == 1
    assert updated_thing_types[0]["thingTypeName"] == "TestThing2"

    # and ids are different
    assert (
        initial_thing_types[0]["thingTypeArn"] != updated_thing_types[0]["thingTypeArn"]
    )


@mock_aws
def test_cloudformation_stack_delete_should_remove_thingtype():
    # given
    stack_name = "test_stack"
    template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Description": "IOT ThingType CloudFormation",
        "Resources": {
            "testThingType": {
                "Type": "AWS::IoT::ThingType",
                "Properties": {"ThingTypeName": "TestThingType"},
            },
        },
    }

    # when
    cfn_conn = boto3.client("cloudformation", region_name=TEST_REGION)
    cfn_conn.create_stack(StackName=stack_name, TemplateBody=json.dumps(template))

    # then check list of things
    iot_conn = boto3.client("iot", region_name=TEST_REGION)
    assert len(iot_conn.list_thing_types()["thingTypes"]) == 1

    # then update
    cfn_conn.delete_stack(StackName=stack_name)
    assert len(iot_conn.list_thing_types()["thingTypes"]) == 0


@mock_aws
def test_create_policy_with_simple_cloudformation():
    # given
    stack_name = "test_stack"
    policy_name = "Test_Policy"
    template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Description": "IOT Policy CloudFormation",
        "Resources": {
            "testPolicy": {
                "Type": "AWS::IoT::Policy",
                "Properties": {
                    "PolicyName": policy_name,
                    "PolicyDocument": json.dumps(
                        {
                            "Version": "2012-10-17",
                            "Statement": [
                                {
                                    "Effect": "Allow",
                                    "Action": ["iot:Connect"],
                                    "Resource": [
                                        "arn:aws:iot:us-east-1:123456789012:client/client1"
                                    ],
                                }
                            ],
                        }
                    ),
                },
            },
        },
        "Outputs": {
            "PolicyArn": {"Value": {"Fn::GetAtt": ["testPolicy", "Arn"]}},
            "PolicyId": {"Value": {"Fn::GetAtt": ["testPolicy", "Id"]}},
        },
    }

    # when
    cfn_conn = boto3.client("cloudformation", region_name=TEST_REGION)
    cfn_conn.create_stack(StackName=stack_name, TemplateBody=json.dumps(template))

    # then check list of things
    iot_conn = boto3.client("iot", region_name=TEST_REGION)
    policies = iot_conn.list_policies()["policies"]
    assert len(policies) == 1
    assert policies[0]["policyName"] == policy_name
    assert (
        policies[0]["policyArn"]
        == "arn:aws:iot:us-west-1:123456789012:policy/Test_Policy"
    )

    # then check stack
    stack = cfn_conn.describe_stacks(StackName=stack_name)["Stacks"][0]
    outputs = {
        Output["OutputKey"]: Output["OutputValue"] for Output in stack["Outputs"]
    }
    assert outputs["PolicyArn"] == policies[0]["policyArn"]


@mock_aws
def test_update_policy_with_the_same_name_should_update_policy_document():
    # given
    stack_name = "test_stack"
    policy_name = "Test_Policy"
    initial_template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Description": "IOT Policy CloudFormation",
        "Resources": {
            "testPolicy": {
                "Type": "AWS::IoT::Policy",
                "Properties": {
                    "PolicyName": policy_name,
                    "PolicyDocument": json.dumps(
                        {
                            "Version": "2012-10-17",
                            "Statement": [
                                {
                                    "Effect": "Allow",
                                    "Action": ["iot:Connect"],
                                    "Resource": [
                                        "arn:aws:iot:us-east-1:123456789012:client/client1"
                                    ],
                                }
                            ],
                        }
                    ),
                },
            },
        },
    }
    updated_template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Description": "IOT Policy CloudFormation",
        "Resources": {
            "testPolicy": {
                "Type": "AWS::IoT::Policy",
                "Properties": {
                    "PolicyName": policy_name,
                    "PolicyDocument": json.dumps(
                        {
                            "Version": "2012-10-17",
                            "Statement": [
                                {
                                    "Effect": "Allow",
                                    "Action": ["iot:Connect", "iot:Subscribe"],
                                    "Resource": ["*"],
                                }
                            ],
                        }
                    ),
                },
            },
        },
    }
    # when
    cfn_conn = boto3.client("cloudformation", region_name=TEST_REGION)
    cfn_conn.create_stack(
        StackName=stack_name, TemplateBody=json.dumps(initial_template)
    )

    # then update stack
    cfn_conn.update_stack(
        StackName=stack_name, TemplateBody=json.dumps(updated_template)
    )

    iot_conn = boto3.client("iot", region_name=TEST_REGION)
    policy = iot_conn.get_policy(policyName=policy_name)

    assert policy["policyName"] == policy_name
    policyDocument = json.loads(policy["policyDocument"])
    assert policyDocument["Statement"][0]["Resource"] == ["*"]


@mock_aws
def test_update_policy_with_different_name_should_recreate_whole_policy():
    # given
    stack_name = "test_stack"
    initial_policy_name = "Test_Policy"
    updated_policy_name = "New_Test_Policy"
    initial_template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Description": "IOT Policy CloudFormation",
        "Resources": {
            "testPolicy": {
                "Type": "AWS::IoT::Policy",
                "Properties": {
                    "PolicyName": initial_policy_name,
                    "PolicyDocument": json.dumps(
                        {
                            "Version": "2012-10-17",
                            "Statement": [
                                {
                                    "Effect": "Allow",
                                    "Action": ["iot:Connect"],
                                    "Resource": [
                                        "arn:aws:iot:us-east-1:123456789012:client/client1"
                                    ],
                                }
                            ],
                        }
                    ),
                },
            },
        },
    }
    updated_template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Description": "IOT Policy CloudFormation",
        "Resources": {
            "testPolicy": {
                "Type": "AWS::IoT::Policy",
                "Properties": {
                    "PolicyName": updated_policy_name,
                    "PolicyDocument": json.dumps(
                        {
                            "Version": "2012-10-17",
                            "Statement": [
                                {
                                    "Effect": "Allow",
                                    "Action": ["iot:Connect", "iot:Subscribe"],
                                    "Resource": ["*"],
                                }
                            ],
                        }
                    ),
                },
            },
        },
    }
    # when
    cfn_conn = boto3.client("cloudformation", region_name=TEST_REGION)
    cfn_conn.create_stack(
        StackName=stack_name, TemplateBody=json.dumps(initial_template)
    )
    iot_conn = boto3.client("iot", region_name=TEST_REGION)
    policies = iot_conn.list_policies()["policies"]
    assert len(policies) == 1
    assert policies[0]["policyName"] == initial_policy_name

    # then update stack
    cfn_conn.update_stack(
        StackName=stack_name, TemplateBody=json.dumps(updated_template)
    )

    policies = iot_conn.list_policies()["policies"]
    assert len(policies) == 1
    assert policies[0]["policyName"] == updated_policy_name

    policy = iot_conn.get_policy(policyName=updated_policy_name)

    assert policy["policyName"] == updated_policy_name
    policyDocument = json.loads(policy["policyDocument"])
    assert policyDocument["Statement"][0]["Resource"] == ["*"]


@mock_aws
def test_delete_stack_should_delete_policy():
    # given
    stack_name = "test_stack"
    policy_name = "Test_Policy"
    template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Description": "IOT Policy CloudFormation",
        "Resources": {
            "testPolicy": {
                "Type": "AWS::IoT::Policy",
                "Properties": {
                    "PolicyName": policy_name,
                    "PolicyDocument": json.dumps(
                        {
                            "Version": "2012-10-17",
                            "Statement": [
                                {
                                    "Effect": "Allow",
                                    "Action": ["iot:Connect"],
                                    "Resource": [
                                        "arn:aws:iot:us-east-1:123456789012:client/client1"
                                    ],
                                }
                            ],
                        }
                    ),
                },
            },
        },
    }
    # when
    cfn_conn = boto3.client("cloudformation", region_name=TEST_REGION)
    cfn_conn.create_stack(StackName=stack_name, TemplateBody=json.dumps(template))
    iot_conn = boto3.client("iot", region_name=TEST_REGION)
    assert len(iot_conn.list_policies()["policies"]) == 1

    # then delete stack
    cfn_conn.delete_stack(StackName=stack_name)
    assert len(iot_conn.list_policies()["policies"]) == 0


@mock_aws
def test_create_role_alias_with_simple_cloudformation():
    # given
    stack_name = "test_stack"
    template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Description": "IOT RoleAlias CloudFormation",
        "Resources": {
            "testRoleAlias": {
                "Type": "AWS::IoT::RoleAlias",
                "Properties": {
                    "RoleAlias": "TestRoleAlias",
                    "RoleArn": "arn:aws:iam::123456789012:role/my-role",
                },
            },
        },
        "Outputs": {
            "RoleAliasArn": {
                "Value": {"Fn::GetAtt": ["testRoleAlias", "RoleAliasArn"]}
            },
        },
    }

    # when
    cfn_conn = boto3.client("cloudformation", region_name=TEST_REGION)
    cfn_conn.create_stack(StackName=stack_name, TemplateBody=json.dumps(template))

    # then check list of things
    iot_conn = boto3.client("iot", region_name=TEST_REGION)
    assert iot_conn.list_role_aliases()["roleAliases"] == ["TestRoleAlias"]

    # then check stack
    stack = cfn_conn.describe_stacks(StackName=stack_name)["Stacks"][0]
    outputs = {
        Output["OutputKey"]: Output["OutputValue"] for Output in stack["Outputs"]
    }
    assert (
        outputs["RoleAliasArn"]
        == "arn:aws:iot:us-west-1:123456789012:rolealias/TestRoleAlias"
    )


@mock_aws
def test_update_role_alias_with_cloudformation():
    # given
    stack_name = "test_stack"
    initial_template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Description": "IOT RoleAlias CloudFormation",
        "Resources": {
            "testRoleAlias": {
                "Type": "AWS::IoT::RoleAlias",
                "Properties": {"RoleArn": "arn:aws:iam::123456789012:role/my-role"},
            },
        },
    }
    updated_template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Description": "IOT RoleAlias CloudFormation",
        "Resources": {
            "testRoleAlias": {
                "Type": "AWS::IoT::RoleAlias",
                "Properties": {
                    "RoleAlias": "TestRoleAlias",
                    "RoleArn": "arn:aws:iam::123456789012:role/other-role",
                    "CredentialDurationSeconds": 1234,
                },
            },
        },
    }

    # when
    cfn_conn = boto3.client("cloudformation", region_name=TEST_REGION)
    cfn_conn.create_stack(
        StackName=stack_name, TemplateBody=json.dumps(initial_template)
    )

    # then check list of role aliases
    iot_conn = boto3.client("iot", region_name=TEST_REGION)
    role_aliases = iot_conn.list_role_aliases()["roleAliases"]
    assert len(role_aliases) == 1
    assert role_aliases[0].startswith("test_stack-testRoleAlias-")

    # then check stack
    cfn_conn.update_stack(
        StackName=stack_name, TemplateBody=json.dumps(updated_template)
    )
    assert iot_conn.list_role_aliases()["roleAliases"] == ["TestRoleAlias"]

    # and describe that role alias
    role_alias = iot_conn.describe_role_alias(roleAlias="TestRoleAlias")
    assert role_alias["roleAliasDescription"]["roleAlias"] == "TestRoleAlias"
    assert (
        role_alias["roleAliasDescription"]["roleAliasArn"]
        == "arn:aws:iot:us-west-1:123456789012:rolealias/TestRoleAlias"
    )
    assert (
        role_alias["roleAliasDescription"]["roleArn"]
        == "arn:aws:iam::123456789012:role/other-role"
    )


@mock_aws
def test_delete_role_alias_with_cloudformation():
    # given
    stack_name = "test_stack"
    template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Description": "IOT RoleAlias CloudFormation",
        "Resources": {
            "testRoleAlias": {
                "Type": "AWS::IoT::RoleAlias",
                "Properties": {
                    "RoleAlias": "TestRoleAlias",
                    "RoleArn": "arn:aws:iam::123456789012:role/my-role",
                },
            },
        },
    }

    # when
    cfn_conn = boto3.client("cloudformation", region_name=TEST_REGION)
    cfn_conn.create_stack(StackName=stack_name, TemplateBody=json.dumps(template))

    # then check list of role aliases
    iot_conn = boto3.client("iot", region_name=TEST_REGION)
    assert len(iot_conn.list_role_aliases()["roleAliases"]) == 1

    # then check stack
    cfn_conn.delete_stack(StackName=stack_name)
    assert iot_conn.list_role_aliases()["roleAliases"] == []


@mock_aws
def test_create_job_template_with_simple_cloudformation():
    # given
    stack_name = "test_stack"
    job_document = {"field": "value"}

    template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Description": "IOT JobTemplate CloudFormation",
        "Resources": {
            "testJobTemplate": {
                "Type": "AWS::IoT::JobTemplate",
                "Properties": {
                    "JobTemplateId": "JobTemplate",
                    "Description": "Job template Description",
                    "Document": json.dumps(job_document),
                    "DocumentSource": "a document source link",
                    "PresignedUrlConfig": {
                        "ExpiresInSec": 123,
                        "RoleArn": "arn:aws:iam::1:role/service-role/iot_job_role",
                    },
                    "TimeoutConfig": {"InProgressTimeoutInMinutes": 30},
                },
            },
        },
        "Outputs": {
            "JobTemplateArn": {"Value": {"Fn::GetAtt": ["testJobTemplate", "Arn"]}},
        },
    }

    # when
    cfn_conn = boto3.client("cloudformation", region_name=TEST_REGION)
    cfn_conn.create_stack(StackName=stack_name, TemplateBody=json.dumps(template))

    # then check list of things
    iot_conn = boto3.client("iot", region_name=TEST_REGION)
    assert len(iot_conn.list_job_templates()["jobTemplates"]) == 1
    assert (
        iot_conn.list_job_templates()["jobTemplates"][0]["jobTemplateId"]
        == "JobTemplate"
    )

    # then check stack
    stack = cfn_conn.describe_stacks(StackName=stack_name)["Stacks"][0]
    outputs = {
        Output["OutputKey"]: Output["OutputValue"] for Output in stack["Outputs"]
    }
    assert (
        outputs["JobTemplateArn"]
        == "arn:aws:iot:us-west-1:123456789012:jobtemplate/JobTemplate"
    )

    # and describe it
    job_template = iot_conn.describe_job_template(jobTemplateId="JobTemplate")
    assert job_template["jobTemplateId"] == "JobTemplate"
    assert (
        job_template["jobTemplateArn"]
        == "arn:aws:iot:us-west-1:123456789012:jobtemplate/JobTemplate"
    )
    assert job_template["description"] == "Job template Description"
    assert job_template["document"] == '{"field": "value"}'
    assert job_template["documentSource"] == "a document source link"
    assert job_template["createdAt"] == datetime(2015, 1, 1, 0, 0, tzinfo=tzlocal())
    assert job_template["presignedUrlConfig"] == {
        "roleArn": "arn:aws:iam::1:role/service-role/iot_job_role",
        "expiresInSec": 123,
    }
    assert job_template["timeoutConfig"] == {
        "inProgressTimeoutInMinutes": 30,
    }


@mock_aws
def test_update_job_template_with_simple_cloudformation():
    # given
    stack_name = "test_stack"

    initial_template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Description": "IOT JobTemplate CloudFormation",
        "Resources": {
            "testJobTemplate": {
                "Type": "AWS::IoT::JobTemplate",
                "Properties": {
                    "JobTemplateId": "JobTemplate",
                    "Description": "Job template Description",
                    "Document": json.dumps({"field1": "value1"}),
                },
            },
        },
    }
    updated_template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Description": "IOT JobTemplate CloudFormation",
        "Resources": {
            "testJobTemplate": {
                "Type": "AWS::IoT::JobTemplate",
                "Properties": {
                    "JobTemplateId": "JobTemplate2",
                    "Description": "Job template Description",
                    "Document": json.dumps({"field2": "value2"}),
                },
            },
        },
    }

    # when
    cfn_conn = boto3.client("cloudformation", region_name=TEST_REGION)
    cfn_conn.create_stack(
        StackName=stack_name, TemplateBody=json.dumps(initial_template)
    )

    # then check list of things
    iot_conn = boto3.client("iot", region_name=TEST_REGION)
    assert len(iot_conn.list_job_templates()["jobTemplates"]) == 1
    assert (
        iot_conn.list_job_templates()["jobTemplates"][0]["jobTemplateId"]
        == "JobTemplate"
    )

    # then update stack
    cfn_conn.update_stack(
        StackName=stack_name, TemplateBody=json.dumps(updated_template)
    )
    assert len(iot_conn.list_job_templates()["jobTemplates"]) == 1
    assert (
        iot_conn.list_job_templates()["jobTemplates"][0]["jobTemplateId"]
        == "JobTemplate2"
    )


@mock_aws
def test_delete_job_template_with_simple_cloudformation():
    # given
    stack_name = "test_stack"

    template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Description": "IOT JobTemplate CloudFormation",
        "Resources": {
            "testJobTemplate": {
                "Type": "AWS::IoT::JobTemplate",
                "Properties": {
                    "JobTemplateId": "JobTemplate",
                    "Description": "Job template Description",
                    "Document": json.dumps({"field": "value"}),
                },
            },
        },
    }

    # when
    cfn_conn = boto3.client("cloudformation", region_name=TEST_REGION)
    cfn_conn.create_stack(StackName=stack_name, TemplateBody=json.dumps(template))

    # then check list of things
    iot_conn = boto3.client("iot", region_name=TEST_REGION)
    assert len(iot_conn.list_job_templates()["jobTemplates"]) == 1

    # then check stack
    cfn_conn.delete_stack(StackName=stack_name)

    # and
    assert len(iot_conn.list_job_templates()["jobTemplates"]) == 0


@mock_aws
def test_create_billing_group_with_cloudformation():
    # given
    stack_name = "test_stack"
    billing_group_name = "TestBillingGroup"
    template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Description": "IOT BillingGroup CloudFormation",
        "Resources": {
            "testBillingGroup": {
                "Type": "AWS::IoT::BillingGroup",
                "Properties": {
                    "BillingGroupName": billing_group_name,
                    "BillingGroupProperties": {
                        "billingGroupDescription": "My test billing group"
                    },
                },
            },
        },
        "Outputs": {
            "BillingGroupArn": {"Value": {"Fn::GetAtt": ["testBillingGroup", "Arn"]}},
            "BillingGroupId": {"Value": {"Fn::GetAtt": ["testBillingGroup", "Id"]}},
        },
    }

    # when
    cfn_conn = boto3.client("cloudformation", region_name=TEST_REGION)
    cfn_conn.create_stack(StackName=stack_name, TemplateBody=json.dumps(template))

    # then check billing group
    iot_conn = boto3.client("iot", region_name=TEST_REGION)
    resp = iot_conn.describe_billing_group(billingGroupName=billing_group_name)
    assert resp["billingGroupName"] == billing_group_name
    assert (
        resp["billingGroupProperties"]["billingGroupDescription"]
        == "My test billing group"
    )

    # Check stack outputs
    stack = cfn_conn.describe_stacks(StackName=stack_name)["Stacks"][0]
    outputs = {
        Output["OutputKey"]: Output["OutputValue"] for Output in stack["Outputs"]
    }
    assert outputs["BillingGroupArn"] == resp["billingGroupArn"]
    assert outputs["BillingGroupId"] == resp["billingGroupId"]


@mock_aws
def test_update_billing_group_description_with_cloudformation():
    # given
    stack_name = "test_stack"
    billing_group_name = "TestBillingGroup"
    initial_description = "My initial test billing group"
    updated_description = "My updated test billing group"

    initial_template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Description": "IOT BillingGroup CloudFormation",
        "Resources": {
            "testBillingGroup": {
                "Type": "AWS::IoT::BillingGroup",
                "Properties": {
                    "BillingGroupName": billing_group_name,
                    "BillingGroupProperties": {
                        "billingGroupDescription": initial_description
                    },
                },
            },
        },
    }

    updated_template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Description": "IOT BillingGroup CloudFormation",
        "Resources": {
            "testBillingGroup": {
                "Type": "AWS::IoT::BillingGroup",
                "Properties": {
                    "BillingGroupName": billing_group_name,
                    "BillingGroupProperties": {
                        "billingGroupDescription": updated_description
                    },
                },
            },
        },
    }

    # when
    cfn_conn = boto3.client("cloudformation", region_name=TEST_REGION)
    cfn_conn.create_stack(
        StackName=stack_name, TemplateBody=json.dumps(initial_template)
    )

    # then check initial billing group description
    iot_conn = boto3.client("iot", region_name=TEST_REGION)
    resp = iot_conn.describe_billing_group(billingGroupName=billing_group_name)
    assert (
        resp["billingGroupProperties"]["billingGroupDescription"] == initial_description
    )

    # when updating the stack
    cfn_conn.update_stack(
        StackName=stack_name, TemplateBody=json.dumps(updated_template)
    )

    # then check updated billing group description
    resp = iot_conn.describe_billing_group(billingGroupName=billing_group_name)
    assert (
        resp["billingGroupProperties"]["billingGroupDescription"] == updated_description
    )


@mock_aws
def test_delete_billing_group_with_cloudformation():
    # given
    stack_name = "test_stack"
    billing_group_name = "TestBillingGroup"
    template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Description": "IOT BillingGroup CloudFormation",
        "Resources": {
            "testBillingGroup": {
                "Type": "AWS::IoT::BillingGroup",
                "Properties": {
                    "BillingGroupName": billing_group_name,
                },
            },
        },
    }

    # when
    cfn_conn = boto3.client("cloudformation", region_name=TEST_REGION)
    cfn_conn.create_stack(StackName=stack_name, TemplateBody=json.dumps(template))

    # then check billing group exists
    iot_conn = boto3.client("iot", region_name=TEST_REGION)
    assert len(iot_conn.list_billing_groups()["billingGroups"]) == 1

    # when deleting the stack
    cfn_conn.delete_stack(StackName=stack_name)

    # then check billing group is removed
    assert len(iot_conn.list_billing_groups()["billingGroups"]) == 0


@mock_aws
def test_update_billing_group_name_with_cloudformation():
    # given
    stack_name = "test_stack"
    initial_billing_group_name = "InitialBillingGroup"
    updated_billing_group_name = "UpdatedBillingGroup"

    initial_template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Description": "IOT BillingGroup CloudFormation",
        "Resources": {
            "testBillingGroup": {
                "Type": "AWS::IoT::BillingGroup",
                "Properties": {
                    "BillingGroupName": initial_billing_group_name,
                },
            },
        },
    }

    updated_template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Description": "IOT BillingGroup CloudFormation",
        "Resources": {
            "testBillingGroup": {
                "Type": "AWS::IoT::BillingGroup",
                "Properties": {
                    "BillingGroupName": updated_billing_group_name,
                },
            },
        },
    }

    # when
    cfn_conn = boto3.client("cloudformation", region_name=TEST_REGION)
    cfn_conn.create_stack(
        StackName=stack_name, TemplateBody=json.dumps(initial_template)
    )

    # then check initial billing group
    iot_conn = boto3.client("iot", region_name=TEST_REGION)
    initial_resp = iot_conn.describe_billing_group(
        billingGroupName=initial_billing_group_name
    )
    assert initial_resp["billingGroupName"] == initial_billing_group_name

    # when updating the stack
    cfn_conn.update_stack(
        StackName=stack_name, TemplateBody=json.dumps(updated_template)
    )

    # then check updated billing group
    updated_resp = iot_conn.describe_billing_group(
        billingGroupName=updated_billing_group_name
    )
    assert updated_resp["billingGroupName"] == updated_billing_group_name

    # and it's a different billing group (ID should change)
    assert initial_resp["billingGroupId"] != updated_resp["billingGroupId"]

    # and the old one should be gone
    assert len(iot_conn.list_billing_groups()["billingGroups"]) == 1
