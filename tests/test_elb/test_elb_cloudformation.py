import boto3
import json

from moto import mock_cloudformation, mock_ec2, mock_elb
from tests import EXAMPLE_AMI_ID


@mock_ec2
@mock_elb
@mock_cloudformation
def test_stack_elb_integration_with_attached_ec2_instances():
    elb_template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "MyELB": {
                "Type": "AWS::ElasticLoadBalancing::LoadBalancer",
                "Properties": {
                    "Instances": [{"Ref": "Ec2Instance1"}],
                    "LoadBalancerName": "test-elb",
                    "AvailabilityZones": ["us-west-1a"],
                    "Listeners": [
                        {
                            "InstancePort": "80",
                            "LoadBalancerPort": "80",
                            "Protocol": "HTTP",
                        }
                    ],
                },
            },
            "Ec2Instance1": {
                "Type": "AWS::EC2::Instance",
                "Properties": {"ImageId": EXAMPLE_AMI_ID, "UserData": "some user data"},
            },
        },
    }
    elb_template_json = json.dumps(elb_template)

    cf = boto3.client("cloudformation", region_name="us-west-1")
    cf.create_stack(StackName="elb_stack", TemplateBody=elb_template_json)

    elb = boto3.client("elb", region_name="us-west-1")
    load_balancer = elb.describe_load_balancers()["LoadBalancerDescriptions"][0]

    ec2 = boto3.client("ec2", region_name="us-west-1")
    reservations = ec2.describe_instances()["Reservations"][0]
    ec2_instance = reservations["Instances"][0]

    assert load_balancer["Instances"][0]["InstanceId"] == ec2_instance["InstanceId"]
    assert load_balancer["AvailabilityZones"] == ["us-west-1a"]


@mock_elb
@mock_cloudformation
def test_stack_elb_integration_with_health_check():
    elb_template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "MyELB": {
                "Type": "AWS::ElasticLoadBalancing::LoadBalancer",
                "Properties": {
                    "LoadBalancerName": "test-elb",
                    "AvailabilityZones": ["us-west-1b"],
                    "HealthCheck": {
                        "HealthyThreshold": "3",
                        "Interval": "5",
                        "Target": "HTTP:80/healthcheck",
                        "Timeout": "4",
                        "UnhealthyThreshold": "2",
                    },
                    "Listeners": [
                        {
                            "InstancePort": "80",
                            "LoadBalancerPort": "80",
                            "Protocol": "HTTP",
                        }
                    ],
                },
            }
        },
    }
    elb_template_json = json.dumps(elb_template)

    cf = boto3.client("cloudformation", region_name="us-west-1")
    cf.create_stack(StackName="elb_stack", TemplateBody=elb_template_json)

    elb = boto3.client("elb", region_name="us-west-1")
    load_balancer = elb.describe_load_balancers()["LoadBalancerDescriptions"][0]
    health_check = load_balancer["HealthCheck"]

    assert health_check["HealthyThreshold"] == 3
    assert health_check["Interval"] == 5
    assert health_check["Target"] == "HTTP:80/healthcheck"
    assert health_check["Timeout"] == 4
    assert health_check["UnhealthyThreshold"] == 2


@mock_elb
@mock_cloudformation
def test_stack_elb_integration_with_update():
    elb_template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "MyELB": {
                "Type": "AWS::ElasticLoadBalancing::LoadBalancer",
                "Properties": {
                    "LoadBalancerName": "test-elb",
                    "AvailabilityZones": ["us-west-1a"],
                    "Listeners": [
                        {
                            "InstancePort": "80",
                            "LoadBalancerPort": "80",
                            "Protocol": "HTTP",
                        }
                    ],
                    "Policies": {"Ref": "AWS::NoValue"},
                },
            }
        },
    }
    elb_template_json = json.dumps(elb_template)

    # when
    cf = boto3.client("cloudformation", region_name="us-west-1")
    cf.create_stack(StackName="elb_stack", TemplateBody=elb_template_json)

    # then
    elb = boto3.client("elb", region_name="us-west-1")
    load_balancer = elb.describe_load_balancers()["LoadBalancerDescriptions"][0]
    assert load_balancer["AvailabilityZones"] == ["us-west-1a"]

    # when
    elb_template["Resources"]["MyELB"]["Properties"]["AvailabilityZones"] = [
        "us-west-1b"
    ]
    elb_template_json = json.dumps(elb_template)
    cf.update_stack(StackName="elb_stack", TemplateBody=elb_template_json)

    # then
    load_balancer = elb.describe_load_balancers()["LoadBalancerDescriptions"][0]
    assert load_balancer["AvailabilityZones"] == ["us-west-1b"]
