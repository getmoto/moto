import boto3
import sure  # noqa

from moto import (
    mock_autoscaling,
    mock_cloudformation,
    mock_ec2,
)

from .utils import setup_networking
from tests import EXAMPLE_AMI_ID


@mock_autoscaling
@mock_cloudformation
def test_launch_configuration():
    cf_client = boto3.client("cloudformation", region_name="us-east-1")
    client = boto3.client("autoscaling", region_name="us-east-1")

    stack_name = "test-launch-configuration"

    cf_template = """
Resources:
    LaunchConfiguration:
        Type: AWS::AutoScaling::LaunchConfiguration
        Properties:
            ImageId: {0}
            InstanceType: t2.micro
            LaunchConfigurationName: test_launch_configuration
Outputs:
    LaunchConfigurationName:
        Value: !Ref LaunchConfiguration
""".strip().format(
        EXAMPLE_AMI_ID
    )

    cf_client.create_stack(
        StackName=stack_name, TemplateBody=cf_template,
    )
    stack = cf_client.describe_stacks(StackName=stack_name)["Stacks"][0]
    stack["Outputs"][0]["OutputValue"].should.be.equal("test_launch_configuration")

    lc = client.describe_launch_configurations()["LaunchConfigurations"][0]
    lc["LaunchConfigurationName"].should.be.equal("test_launch_configuration")
    lc["ImageId"].should.be.equal(EXAMPLE_AMI_ID)
    lc["InstanceType"].should.be.equal("t2.micro")

    cf_template = """
Resources:
    LaunchConfiguration:
        Type: AWS::AutoScaling::LaunchConfiguration
        Properties:
            ImageId: {0}
            InstanceType: m5.large
            LaunchConfigurationName: test_launch_configuration
Outputs:
    LaunchConfigurationName:
        Value: !Ref LaunchConfiguration
""".strip().format(
        EXAMPLE_AMI_ID
    )

    cf_client.update_stack(
        StackName=stack_name, TemplateBody=cf_template,
    )
    stack = cf_client.describe_stacks(StackName=stack_name)["Stacks"][0]
    stack["Outputs"][0]["OutputValue"].should.be.equal("test_launch_configuration")

    lc = client.describe_launch_configurations()["LaunchConfigurations"][0]
    lc["LaunchConfigurationName"].should.be.equal("test_launch_configuration")
    lc["ImageId"].should.be.equal(EXAMPLE_AMI_ID)
    lc["InstanceType"].should.be.equal("m5.large")


@mock_autoscaling
@mock_cloudformation
def test_autoscaling_group_from_launch_config():
    subnet_id = setup_networking()["subnet1"]

    cf_client = boto3.client("cloudformation", region_name="us-east-1")
    client = boto3.client("autoscaling", region_name="us-east-1")

    client.create_launch_configuration(
        LaunchConfigurationName="test_launch_configuration",
        InstanceType="t2.micro",
        ImageId=EXAMPLE_AMI_ID,
    )
    stack_name = "test-auto-scaling-group"

    cf_template = """
Parameters:
    SubnetId:
        Type: AWS::EC2::Subnet::Id
Resources:
    AutoScalingGroup:
        Type: AWS::AutoScaling::AutoScalingGroup
        Properties:
            AutoScalingGroupName: test_auto_scaling_group
            AvailabilityZones:
                - us-east-1a
            LaunchConfigurationName: test_launch_configuration
            MaxSize: "5"
            MinSize: "1"
            VPCZoneIdentifier:
                - !Ref SubnetId
Outputs:
    AutoScalingGroupName:
        Value: !Ref AutoScalingGroup
""".strip()

    cf_client.create_stack(
        StackName=stack_name,
        TemplateBody=cf_template,
        Parameters=[{"ParameterKey": "SubnetId", "ParameterValue": subnet_id}],
    )
    stack = cf_client.describe_stacks(StackName=stack_name)["Stacks"][0]
    stack["Outputs"][0]["OutputValue"].should.be.equal("test_auto_scaling_group")

    asg = client.describe_auto_scaling_groups()["AutoScalingGroups"][0]
    asg["AutoScalingGroupName"].should.be.equal("test_auto_scaling_group")
    asg["MinSize"].should.be.equal(1)
    asg["MaxSize"].should.be.equal(5)
    asg["LaunchConfigurationName"].should.be.equal("test_launch_configuration")

    client.create_launch_configuration(
        LaunchConfigurationName="test_launch_configuration_new",
        InstanceType="t2.micro",
        ImageId=EXAMPLE_AMI_ID,
    )

    cf_template = """
Parameters:
    SubnetId:
        Type: AWS::EC2::Subnet::Id
Resources:
    AutoScalingGroup:
        Type: AWS::AutoScaling::AutoScalingGroup
        Properties:
            AutoScalingGroupName: test_auto_scaling_group
            AvailabilityZones:
                - us-east-1a
            LaunchConfigurationName: test_launch_configuration_new
            MaxSize: "6"
            MinSize: "2"
            VPCZoneIdentifier:
                - !Ref SubnetId
Outputs:
    AutoScalingGroupName:
        Value: !Ref AutoScalingGroup
""".strip()

    cf_client.update_stack(
        StackName=stack_name,
        TemplateBody=cf_template,
        Parameters=[{"ParameterKey": "SubnetId", "ParameterValue": subnet_id}],
    )
    stack = cf_client.describe_stacks(StackName=stack_name)["Stacks"][0]
    stack["Outputs"][0]["OutputValue"].should.be.equal("test_auto_scaling_group")

    asg = client.describe_auto_scaling_groups()["AutoScalingGroups"][0]
    asg["AutoScalingGroupName"].should.be.equal("test_auto_scaling_group")
    asg["MinSize"].should.be.equal(2)
    asg["MaxSize"].should.be.equal(6)
    asg["LaunchConfigurationName"].should.be.equal("test_launch_configuration_new")


@mock_autoscaling
@mock_cloudformation
@mock_ec2
def test_autoscaling_group_from_launch_template():
    subnet_id = setup_networking()["subnet1"]

    cf_client = boto3.client("cloudformation", region_name="us-east-1")
    ec2_client = boto3.client("ec2", region_name="us-east-1")
    client = boto3.client("autoscaling", region_name="us-east-1")

    template_response = ec2_client.create_launch_template(
        LaunchTemplateName="test_launch_template",
        LaunchTemplateData={"ImageId": EXAMPLE_AMI_ID, "InstanceType": "t2.micro",},
    )
    launch_template_id = template_response["LaunchTemplate"]["LaunchTemplateId"]
    stack_name = "test-auto-scaling-group"

    cf_template = """
Parameters:
    SubnetId:
        Type: AWS::EC2::Subnet::Id
    LaunchTemplateId:
        Type: String
Resources:
    AutoScalingGroup:
        Type: AWS::AutoScaling::AutoScalingGroup
        Properties:
            AutoScalingGroupName: test_auto_scaling_group
            AvailabilityZones:
                - us-east-1a
            LaunchTemplate:
                LaunchTemplateId: !Ref LaunchTemplateId
                Version: "1"
            MaxSize: "5"
            MinSize: "1"
            VPCZoneIdentifier:
                - !Ref SubnetId
Outputs:
    AutoScalingGroupName:
        Value: !Ref AutoScalingGroup
""".strip()

    cf_client.create_stack(
        StackName=stack_name,
        TemplateBody=cf_template,
        Parameters=[
            {"ParameterKey": "SubnetId", "ParameterValue": subnet_id},
            {"ParameterKey": "LaunchTemplateId", "ParameterValue": launch_template_id},
        ],
    )
    stack = cf_client.describe_stacks(StackName=stack_name)["Stacks"][0]
    stack["Outputs"][0]["OutputValue"].should.be.equal("test_auto_scaling_group")

    asg = client.describe_auto_scaling_groups()["AutoScalingGroups"][0]
    asg["AutoScalingGroupName"].should.be.equal("test_auto_scaling_group")
    asg["MinSize"].should.be.equal(1)
    asg["MaxSize"].should.be.equal(5)
    lt = asg["LaunchTemplate"]
    lt["LaunchTemplateId"].should.be.equal(launch_template_id)
    lt["LaunchTemplateName"].should.be.equal("test_launch_template")
    lt["Version"].should.be.equal("1")

    template_response = ec2_client.create_launch_template(
        LaunchTemplateName="test_launch_template_new",
        LaunchTemplateData={"ImageId": EXAMPLE_AMI_ID, "InstanceType": "m5.large",},
    )
    launch_template_id = template_response["LaunchTemplate"]["LaunchTemplateId"]

    cf_template = """
Parameters:
    SubnetId:
        Type: AWS::EC2::Subnet::Id
    LaunchTemplateId:
        Type: String
Resources:
    AutoScalingGroup:
        Type: AWS::AutoScaling::AutoScalingGroup
        Properties:
            AutoScalingGroupName: test_auto_scaling_group
            AvailabilityZones:
                - us-east-1a
            LaunchTemplate:
                LaunchTemplateId: !Ref LaunchTemplateId
                Version: "1"
            MaxSize: "6"
            MinSize: "2"
            VPCZoneIdentifier:
                - !Ref SubnetId
Outputs:
    AutoScalingGroupName:
        Value: !Ref AutoScalingGroup
""".strip()

    cf_client.update_stack(
        StackName=stack_name,
        TemplateBody=cf_template,
        Parameters=[
            {"ParameterKey": "SubnetId", "ParameterValue": subnet_id},
            {"ParameterKey": "LaunchTemplateId", "ParameterValue": launch_template_id},
        ],
    )
    stack = cf_client.describe_stacks(StackName=stack_name)["Stacks"][0]
    stack["Outputs"][0]["OutputValue"].should.be.equal("test_auto_scaling_group")

    asg = client.describe_auto_scaling_groups()["AutoScalingGroups"][0]
    asg["AutoScalingGroupName"].should.be.equal("test_auto_scaling_group")
    asg["MinSize"].should.be.equal(2)
    asg["MaxSize"].should.be.equal(6)
    lt = asg["LaunchTemplate"]
    lt["LaunchTemplateId"].should.be.equal(launch_template_id)
    lt["LaunchTemplateName"].should.be.equal("test_launch_template_new")
    lt["Version"].should.be.equal("1")
