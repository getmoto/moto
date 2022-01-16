import boto3
import json
import sure  # noqa # pylint: disable=unused-import

from moto import mock_elbv2, mock_ec2, mock_cloudformation
from moto.core import ACCOUNT_ID


@mock_elbv2
@mock_cloudformation
def test_redirect_action_listener_rule_cloudformation():
    cnf_conn = boto3.client("cloudformation", region_name="us-east-1")
    elbv2_client = boto3.client("elbv2", region_name="us-east-1")

    template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Description": "ECS Cluster Test CloudFormation",
        "Resources": {
            "testVPC": {
                "Type": "AWS::EC2::VPC",
                "Properties": {"CidrBlock": "10.0.0.0/16"},
            },
            "subnet1": {
                "Type": "AWS::EC2::Subnet",
                "Properties": {
                    "CidrBlock": "10.0.0.0/24",
                    "VpcId": {"Ref": "testVPC"},
                    "AvalabilityZone": "us-east-1b",
                },
            },
            "subnet2": {
                "Type": "AWS::EC2::Subnet",
                "Properties": {
                    "CidrBlock": "10.0.1.0/24",
                    "VpcId": {"Ref": "testVPC"},
                    "AvalabilityZone": "us-east-1b",
                },
            },
            "testLb": {
                "Type": "AWS::ElasticLoadBalancingV2::LoadBalancer",
                "Properties": {
                    "Name": "my-lb",
                    "Subnets": [{"Ref": "subnet1"}, {"Ref": "subnet2"}],
                    "Type": "application",
                    "SecurityGroups": [],
                },
            },
            "testListener": {
                "Type": "AWS::ElasticLoadBalancingV2::Listener",
                "Properties": {
                    "LoadBalancerArn": {"Ref": "testLb"},
                    "Port": 80,
                    "Protocol": "HTTP",
                    "DefaultActions": [
                        {
                            "Type": "redirect",
                            "RedirectConfig": {
                                "Port": "443",
                                "Protocol": "HTTPS",
                                "StatusCode": "HTTP_301",
                            },
                        }
                    ],
                },
            },
        },
    }
    template_json = json.dumps(template)
    cnf_conn.create_stack(StackName="test-stack", TemplateBody=template_json)

    describe_load_balancers_response = elbv2_client.describe_load_balancers(
        Names=["my-lb"]
    )
    describe_load_balancers_response["LoadBalancers"].should.have.length_of(1)
    load_balancer_arn = describe_load_balancers_response["LoadBalancers"][0][
        "LoadBalancerArn"
    ]

    describe_listeners_response = elbv2_client.describe_listeners(
        LoadBalancerArn=load_balancer_arn
    )

    describe_listeners_response["Listeners"].should.have.length_of(1)
    describe_listeners_response["Listeners"][0]["DefaultActions"].should.equal(
        [
            {
                "Type": "redirect",
                "RedirectConfig": {
                    "Port": "443",
                    "Protocol": "HTTPS",
                    "StatusCode": "HTTP_301",
                },
            }
        ]
    )


@mock_elbv2
@mock_cloudformation
def test_cognito_action_listener_rule_cloudformation():
    cnf_conn = boto3.client("cloudformation", region_name="us-east-1")
    elbv2_client = boto3.client("elbv2", region_name="us-east-1")

    template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Description": "ECS Cluster Test CloudFormation",
        "Resources": {
            "testVPC": {
                "Type": "AWS::EC2::VPC",
                "Properties": {"CidrBlock": "10.0.0.0/16"},
            },
            "subnet1": {
                "Type": "AWS::EC2::Subnet",
                "Properties": {
                    "CidrBlock": "10.0.0.0/24",
                    "VpcId": {"Ref": "testVPC"},
                    "AvalabilityZone": "us-east-1b",
                },
            },
            "subnet2": {
                "Type": "AWS::EC2::Subnet",
                "Properties": {
                    "CidrBlock": "10.0.1.0/24",
                    "VpcId": {"Ref": "testVPC"},
                    "AvalabilityZone": "us-east-1b",
                },
            },
            "testLb": {
                "Type": "AWS::ElasticLoadBalancingV2::LoadBalancer",
                "Properties": {
                    "Name": "my-lb",
                    "Subnets": [{"Ref": "subnet1"}, {"Ref": "subnet2"}],
                    "Type": "application",
                    "SecurityGroups": [],
                },
            },
            "testListener": {
                "Type": "AWS::ElasticLoadBalancingV2::Listener",
                "Properties": {
                    "LoadBalancerArn": {"Ref": "testLb"},
                    "Port": 80,
                    "Protocol": "HTTP",
                    "DefaultActions": [
                        {
                            "Type": "authenticate-cognito",
                            "AuthenticateCognitoConfig": {
                                "UserPoolArn": "arn:aws:cognito-idp:us-east-1:{}:userpool/us-east-1_ABCD1234".format(
                                    ACCOUNT_ID
                                ),
                                "UserPoolClientId": "abcd1234abcd",
                                "UserPoolDomain": "testpool",
                            },
                        }
                    ],
                },
            },
        },
    }
    template_json = json.dumps(template)
    cnf_conn.create_stack(StackName="test-stack", TemplateBody=template_json)

    describe_load_balancers_response = elbv2_client.describe_load_balancers(
        Names=["my-lb"]
    )
    load_balancer_arn = describe_load_balancers_response["LoadBalancers"][0][
        "LoadBalancerArn"
    ]
    describe_listeners_response = elbv2_client.describe_listeners(
        LoadBalancerArn=load_balancer_arn
    )

    describe_listeners_response["Listeners"].should.have.length_of(1)
    describe_listeners_response["Listeners"][0]["DefaultActions"].should.equal(
        [
            {
                "Type": "authenticate-cognito",
                "AuthenticateCognitoConfig": {
                    "UserPoolArn": "arn:aws:cognito-idp:us-east-1:{}:userpool/us-east-1_ABCD1234".format(
                        ACCOUNT_ID
                    ),
                    "UserPoolClientId": "abcd1234abcd",
                    "UserPoolDomain": "testpool",
                },
            }
        ]
    )


@mock_ec2
@mock_elbv2
@mock_cloudformation
def test_create_target_groups_through_cloudformation():
    cfn_conn = boto3.client("cloudformation", region_name="us-east-1")
    elbv2_client = boto3.client("elbv2", region_name="us-east-1")

    # test that setting a name manually as well as letting cloudformation create a name both work
    # this is a special case because test groups have a name length limit of 22 characters, and must be unique
    # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-elasticloadbalancingv2-targetgroup.html#cfn-elasticloadbalancingv2-targetgroup-name
    template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Description": "ECS Cluster Test CloudFormation",
        "Resources": {
            "testVPC": {
                "Type": "AWS::EC2::VPC",
                "Properties": {"CidrBlock": "10.0.0.0/16"},
            },
            "testGroup1": {
                "Type": "AWS::ElasticLoadBalancingV2::TargetGroup",
                "Properties": {
                    "Port": 80,
                    "Protocol": "HTTP",
                    "VpcId": {"Ref": "testVPC"},
                },
            },
            "testGroup2": {
                "Type": "AWS::ElasticLoadBalancingV2::TargetGroup",
                "Properties": {
                    "Port": 90,
                    "Protocol": "HTTP",
                    "VpcId": {"Ref": "testVPC"},
                },
            },
            "testGroup3": {
                "Type": "AWS::ElasticLoadBalancingV2::TargetGroup",
                "Properties": {
                    "Name": "MyTargetGroup",
                    "Port": 70,
                    "Protocol": "HTTPS",
                    "VpcId": {"Ref": "testVPC"},
                },
            },
        },
    }
    template_json = json.dumps(template)
    cfn_conn.create_stack(StackName="test-stack", TemplateBody=template_json)

    describe_target_groups_response = elbv2_client.describe_target_groups()
    target_group_dicts = describe_target_groups_response["TargetGroups"]
    assert len(target_group_dicts) == 3

    # there should be 2 target groups with the same prefix of 10 characters (since the random suffix is 12)
    # and one named MyTargetGroup
    assert (
        len(
            [
                tg
                for tg in target_group_dicts
                if tg["TargetGroupName"] == "MyTargetGroup"
            ]
        )
        == 1
    )
    assert (
        len(
            [
                tg
                for tg in target_group_dicts
                if tg["TargetGroupName"].startswith("test-stack")
            ]
        )
        == 2
    )


@mock_elbv2
@mock_cloudformation
def test_fixed_response_action_listener_rule_cloudformation():
    cnf_conn = boto3.client("cloudformation", region_name="us-east-1")
    elbv2_client = boto3.client("elbv2", region_name="us-east-1")

    template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Description": "ECS Cluster Test CloudFormation",
        "Resources": {
            "testVPC": {
                "Type": "AWS::EC2::VPC",
                "Properties": {"CidrBlock": "10.0.0.0/16"},
            },
            "subnet1": {
                "Type": "AWS::EC2::Subnet",
                "Properties": {
                    "CidrBlock": "10.0.0.0/24",
                    "VpcId": {"Ref": "testVPC"},
                    "AvalabilityZone": "us-east-1b",
                },
            },
            "subnet2": {
                "Type": "AWS::EC2::Subnet",
                "Properties": {
                    "CidrBlock": "10.0.1.0/24",
                    "VpcId": {"Ref": "testVPC"},
                    "AvalabilityZone": "us-east-1b",
                },
            },
            "testLb": {
                "Type": "AWS::ElasticLoadBalancingV2::LoadBalancer",
                "Properties": {
                    "Name": "my-lb",
                    "Subnets": [{"Ref": "subnet1"}, {"Ref": "subnet2"}],
                    "Type": "application",
                    "SecurityGroups": [],
                },
            },
            "testListener": {
                "Type": "AWS::ElasticLoadBalancingV2::Listener",
                "Properties": {
                    "LoadBalancerArn": {"Ref": "testLb"},
                    "Port": 80,
                    "Protocol": "HTTP",
                    "DefaultActions": [
                        {
                            "Type": "fixed-response",
                            "FixedResponseConfig": {
                                "ContentType": "text/plain",
                                "MessageBody": "This page does not exist",
                                "StatusCode": "404",
                            },
                        }
                    ],
                },
            },
        },
    }
    template_json = json.dumps(template)
    cnf_conn.create_stack(StackName="test-stack", TemplateBody=template_json)

    describe_load_balancers_response = elbv2_client.describe_load_balancers(
        Names=["my-lb"]
    )
    load_balancer_arn = describe_load_balancers_response["LoadBalancers"][0][
        "LoadBalancerArn"
    ]
    describe_listeners_response = elbv2_client.describe_listeners(
        LoadBalancerArn=load_balancer_arn
    )

    describe_listeners_response["Listeners"].should.have.length_of(1)
    describe_listeners_response["Listeners"][0]["DefaultActions"].should.equal(
        [
            {
                "Type": "fixed-response",
                "FixedResponseConfig": {
                    "ContentType": "text/plain",
                    "MessageBody": "This page does not exist",
                    "StatusCode": "404",
                },
            }
        ]
    )
