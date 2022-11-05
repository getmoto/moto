import boto3
import json
import sure  # noqa # pylint: disable=unused-import
from moto import mock_iam, mock_ec2, mock_ecs, mock_cloudformation
from moto import mock_batch_simple as mock_batch_without_docker
from uuid import uuid4


# Copy of test_batch/test_batch_cloudformation
# Except that we verify this behaviour still works without docker


DEFAULT_REGION = "eu-central-1"


def _get_clients():
    return (
        boto3.client("ec2", region_name=DEFAULT_REGION),
        boto3.client("iam", region_name=DEFAULT_REGION),
        boto3.client("ecs", region_name=DEFAULT_REGION),
        boto3.client("logs", region_name=DEFAULT_REGION),
        boto3.client("batch", region_name=DEFAULT_REGION),
    )


def _setup(ec2_client, iam_client):
    """
    Do prerequisite setup
    :return: VPC ID, Subnet ID, Security group ID, IAM Role ARN
    :rtype: tuple
    """
    resp = ec2_client.create_vpc(CidrBlock="172.30.0.0/24")
    vpc_id = resp["Vpc"]["VpcId"]
    resp = ec2_client.create_subnet(
        AvailabilityZone="eu-central-1a", CidrBlock="172.30.0.0/25", VpcId=vpc_id
    )
    subnet_id = resp["Subnet"]["SubnetId"]
    resp = ec2_client.create_security_group(
        Description="test_sg_desc", GroupName=str(uuid4())[0:6], VpcId=vpc_id
    )
    sg_id = resp["GroupId"]

    role_name = str(uuid4())[0:6]
    resp = iam_client.create_role(
        RoleName=role_name, AssumeRolePolicyDocument="some_policy"
    )
    iam_arn = resp["Role"]["Arn"]
    iam_client.create_instance_profile(InstanceProfileName=role_name)
    iam_client.add_role_to_instance_profile(
        InstanceProfileName=role_name, RoleName=role_name
    )

    return vpc_id, subnet_id, sg_id, iam_arn


@mock_cloudformation()
@mock_ec2
@mock_ecs
@mock_iam
@mock_batch_without_docker
def test_create_env_cf():
    ec2_client, iam_client, _, _, _ = _get_clients()
    _, subnet_id, sg_id, iam_arn = _setup(ec2_client, iam_client)

    create_environment_template = {
        "Resources": {
            "ComputeEnvironment": {
                "Type": "AWS::Batch::ComputeEnvironment",
                "Properties": {
                    "Type": "MANAGED",
                    "ComputeResources": {
                        "Type": "EC2",
                        "MinvCpus": 0,
                        "DesiredvCpus": 0,
                        "MaxvCpus": 64,
                        "InstanceTypes": ["optimal"],
                        "Subnets": [subnet_id],
                        "SecurityGroupIds": [sg_id],
                        "InstanceRole": iam_arn.replace("role", "instance-profile"),
                    },
                    "ServiceRole": iam_arn,
                },
            }
        }
    }
    cf_json = json.dumps(create_environment_template)

    cf_conn = boto3.client("cloudformation", DEFAULT_REGION)
    stack_name = str(uuid4())[0:6]
    stack_id = cf_conn.create_stack(StackName=stack_name, TemplateBody=cf_json)[
        "StackId"
    ]

    stack_resources = cf_conn.list_stack_resources(StackName=stack_id)

    stack_resources["StackResourceSummaries"][0]["ResourceStatus"].should.equal(
        "CREATE_COMPLETE"
    )
    # Spot checks on the ARN
    stack_resources["StackResourceSummaries"][0]["PhysicalResourceId"].startswith(
        "arn:aws:batch:"
    )
    stack_resources["StackResourceSummaries"][0]["PhysicalResourceId"].should.contain(
        stack_name
    )


@mock_cloudformation()
@mock_ec2
@mock_ecs
@mock_iam
@mock_batch_without_docker
def test_create_job_queue_cf():
    ec2_client, iam_client, _, _, _ = _get_clients()
    _, subnet_id, sg_id, iam_arn = _setup(ec2_client, iam_client)

    create_environment_template = {
        "Resources": {
            "ComputeEnvironment": {
                "Type": "AWS::Batch::ComputeEnvironment",
                "Properties": {
                    "Type": "MANAGED",
                    "ComputeResources": {
                        "Type": "EC2",
                        "MinvCpus": 0,
                        "DesiredvCpus": 0,
                        "MaxvCpus": 64,
                        "InstanceTypes": ["optimal"],
                        "Subnets": [subnet_id],
                        "SecurityGroupIds": [sg_id],
                        "InstanceRole": iam_arn.replace("role", "instance-profile"),
                    },
                    "ServiceRole": iam_arn,
                },
            },
            "JobQueue": {
                "Type": "AWS::Batch::JobQueue",
                "Properties": {
                    "Priority": 1,
                    "ComputeEnvironmentOrder": [
                        {
                            "Order": 1,
                            "ComputeEnvironment": {"Ref": "ComputeEnvironment"},
                        }
                    ],
                },
            },
        }
    }
    cf_json = json.dumps(create_environment_template)

    cf_conn = boto3.client("cloudformation", DEFAULT_REGION)
    stack_name = str(uuid4())[0:6]
    stack_id = cf_conn.create_stack(StackName=stack_name, TemplateBody=cf_json)[
        "StackId"
    ]

    stack_resources = cf_conn.list_stack_resources(StackName=stack_id)
    len(stack_resources["StackResourceSummaries"]).should.equal(2)

    job_queue_resource = list(
        filter(
            lambda item: item["ResourceType"] == "AWS::Batch::JobQueue",
            stack_resources["StackResourceSummaries"],
        )
    )[0]

    job_queue_resource["ResourceStatus"].should.equal("CREATE_COMPLETE")
    # Spot checks on the ARN
    job_queue_resource["PhysicalResourceId"].startswith("arn:aws:batch:")
    job_queue_resource["PhysicalResourceId"].should.contain(stack_name)
    job_queue_resource["PhysicalResourceId"].should.contain("job-queue/")


@mock_cloudformation
@mock_ec2
@mock_ecs
@mock_iam
@mock_batch_without_docker
def test_create_job_def_cf():
    ec2_client, iam_client, _, _, _ = _get_clients()
    _, subnet_id, sg_id, iam_arn = _setup(ec2_client, iam_client)

    create_environment_template = {
        "Resources": {
            "ComputeEnvironment": {
                "Type": "AWS::Batch::ComputeEnvironment",
                "Properties": {
                    "Type": "MANAGED",
                    "ComputeResources": {
                        "Type": "EC2",
                        "MinvCpus": 0,
                        "DesiredvCpus": 0,
                        "MaxvCpus": 64,
                        "InstanceTypes": ["optimal"],
                        "Subnets": [subnet_id],
                        "SecurityGroupIds": [sg_id],
                        "InstanceRole": iam_arn.replace("role", "instance-profile"),
                    },
                    "ServiceRole": iam_arn,
                },
            },
            "JobQueue": {
                "Type": "AWS::Batch::JobQueue",
                "Properties": {
                    "Priority": 1,
                    "ComputeEnvironmentOrder": [
                        {
                            "Order": 1,
                            "ComputeEnvironment": {"Ref": "ComputeEnvironment"},
                        }
                    ],
                },
            },
            "JobDefinition": {
                "Type": "AWS::Batch::JobDefinition",
                "Properties": {
                    "Type": "container",
                    "ContainerProperties": {
                        "Image": {
                            "Fn::Join": [
                                "",
                                [
                                    "137112412989.dkr.ecr.",
                                    {"Ref": "AWS::Region"},
                                    ".amazonaws.com/amazonlinux:latest",
                                ],
                            ]
                        },
                        "ResourceRequirements": [
                            {"Type": "MEMORY", "Value": 2000},
                            {"Type": "VCPU", "Value": 2},
                        ],
                        "Command": ["echo", "Hello world"],
                        "LinuxParameters": {"Devices": [{"HostPath": "test-path"}]},
                    },
                    "RetryStrategy": {"Attempts": 1},
                },
            },
        }
    }
    cf_json = json.dumps(create_environment_template)

    cf_conn = boto3.client("cloudformation", DEFAULT_REGION)
    stack_name = str(uuid4())[0:6]
    stack_id = cf_conn.create_stack(StackName=stack_name, TemplateBody=cf_json)[
        "StackId"
    ]

    stack_resources = cf_conn.list_stack_resources(StackName=stack_id)
    len(stack_resources["StackResourceSummaries"]).should.equal(3)

    job_def_resource = list(
        filter(
            lambda item: item["ResourceType"] == "AWS::Batch::JobDefinition",
            stack_resources["StackResourceSummaries"],
        )
    )[0]

    job_def_resource["ResourceStatus"].should.equal("CREATE_COMPLETE")
    # Spot checks on the ARN
    job_def_resource["PhysicalResourceId"].startswith("arn:aws:batch:")
    job_def_resource["PhysicalResourceId"].should.contain(f"{stack_name}-JobDef")
    job_def_resource["PhysicalResourceId"].should.contain("job-definition/")

    # Test the linux parameter device host path
    # This ensures that batch is parsing the parameter dictionaries
    # correctly by recursively converting the first character of all
    # dict keys to lowercase.
    batch_conn = boto3.client("batch", DEFAULT_REGION)
    response = batch_conn.describe_job_definitions(
        jobDefinitions=[job_def_resource["PhysicalResourceId"]]
    )
    job_def_linux_device_host_path = response.get("jobDefinitions")[0][
        "containerProperties"
    ]["linuxParameters"]["devices"][0]["hostPath"]

    job_def_linux_device_host_path.should.equal("test-path")
