import copy
from string import Template

import boto3
import json
from moto import mock_cloudformation, mock_ecr
import sure  # noqa

from moto.core import ACCOUNT_ID

repo_template = Template(
    json.dumps(
        {
            "AWSTemplateFormatVersion": "2010-09-09",
            "Description": "ECR Repo Test",
            "Resources": {
                "Repo": {
                    "Type": "AWS::ECR::Repository",
                    "Properties": {"RepositoryName": "${repo_name}",},
                }
            },
            "Outputs": {
                "Arn": {
                    "Description": "Repo Arn",
                    "Value": {"Fn::GetAtt": ["Repo", "Arn"]},
                }
            },
        }
    )
)


@mock_ecr
@mock_cloudformation
def test_create_repository():
    # given
    cfn_client = boto3.client("cloudformation", region_name="eu-central-1")
    name = "test-repo"
    stack_name = "test-stack"
    template = repo_template.substitute({"repo_name": name})

    # when
    cfn_client.create_stack(StackName=stack_name, TemplateBody=template)

    # then
    repo_arn = f"arn:aws:ecr:eu-central-1:{ACCOUNT_ID}:repository/{name}"
    stack = cfn_client.describe_stacks(StackName=stack_name)["Stacks"][0]
    stack["Outputs"][0]["OutputValue"].should.equal(repo_arn)

    ecr_client = boto3.client("ecr", region_name="eu-central-1")
    response = ecr_client.describe_repositories(repositoryNames=[name])

    response["repositories"][0]["repositoryArn"].should.equal(repo_arn)


@mock_ecr
@mock_cloudformation
def test_update_repository():
    # given
    cfn_client = boto3.client("cloudformation", region_name="eu-central-1")
    name = "test-repo"
    stack_name = "test-stack"
    template = repo_template.substitute({"repo_name": name})
    cfn_client.create_stack(StackName=stack_name, TemplateBody=template)

    template_update = copy.deepcopy(json.loads(template))
    template_update["Resources"]["Repo"]["Properties"][
        "ImageTagMutability"
    ] = "IMMUTABLE"

    # when
    cfn_client.update_stack(
        StackName=stack_name, TemplateBody=json.dumps(template_update)
    )

    # then
    ecr_client = boto3.client("ecr", region_name="eu-central-1")
    response = ecr_client.describe_repositories(repositoryNames=[name])

    repo = response["repositories"][0]
    repo["repositoryArn"].should.equal(
        f"arn:aws:ecr:eu-central-1:{ACCOUNT_ID}:repository/{name}"
    )
    repo["imageTagMutability"].should.equal("IMMUTABLE")


@mock_ecr
@mock_cloudformation
def test_delete_repository():
    # given
    cfn_client = boto3.client("cloudformation", region_name="eu-central-1")
    name = "test-repo"
    stack_name = "test-stack"
    template = repo_template.substitute({"repo_name": name})
    cfn_client.create_stack(StackName=stack_name, TemplateBody=template)

    # when
    cfn_client.delete_stack(StackName=stack_name)

    # then
    ecr_client = boto3.client("ecr", region_name="eu-central-1")
    response = ecr_client.describe_repositories()["repositories"]
    response.should.have.length_of(0)
