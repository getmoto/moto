import copy
import json
from string import Template

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID

repo_template = Template(
    json.dumps(
        {
            "AWSTemplateFormatVersion": "2010-09-09",
            "Description": "ECR Repo Test",
            "Resources": {
                "Repo": {
                    "Type": "AWS::ECR::Repository",
                    "Properties": {
                        "RepositoryName": "${repo_name}",
                        "ImageTagMutability": "MUTABLE_WITH_EXCLUSION",
                        "ImageTagMutabilityExclusionFilters": [
                            {
                                "ImageTagMutabilityExclusionFilterType": "WILDCARD",
                                "ImageTagMutabilityExclusionFilterValue": "dev*",
                            },
                        ],
                    },
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


@mock_aws
def test_create_repository():
    # given
    cfn_client = boto3.client("cloudformation", region_name="eu-central-1")
    name = "test-repo"
    stack_name = "test-stack"
    template = repo_template.substitute({"repo_name": name})

    # Eventually we will just create the repository using the CloudFormation template above,
    # But we shall highlight the validations as part of the process, which lead to failure in
    # the creation of the repository
    invalid_template_wo_exclusion = copy.deepcopy(json.loads(template))
    _ = invalid_template_wo_exclusion["Resources"]["Repo"]["Properties"].pop(
        "ImageTagMutabilityExclusionFilters", None
    )
    with pytest.raises(ClientError) as exc:
        cfn_client.create_stack(
            StackName=f"{stack_name}-invalid-1",
            TemplateBody=json.dumps(invalid_template_wo_exclusion),
        )
    assert exc.value.response["Error"]["Code"] == "InvalidParameterException"
    assert (
        exc.value.response["Error"]["Message"]
        == "Invalid parameter at 'imageTagMutabilityExclusionFilters' failed to satisfy constraint: 'ImageTagMutabilityExclusionFilters can't be null when imageTagMutability is set as MUTABLE_WITH_EXCLUSION'"
    )

    # Similarly, when exclusion filters are provided but imageTagMutability is not of the _EXCLUSION variant
    invalid_template_wo_exclusion = copy.deepcopy(json.loads(template))
    invalid_template_wo_exclusion["Resources"]["Repo"]["Properties"][
        "ImageTagMutability"
    ] = "MUTABLE"
    with pytest.raises(ClientError) as exc:
        cfn_client.create_stack(
            StackName=f"{stack_name}-invalid-2",
            TemplateBody=json.dumps(invalid_template_wo_exclusion),
        )
    assert exc.value.response["Error"]["Code"] == "InvalidParameterException"
    assert (
        exc.value.response["Error"]["Message"]
        == "Invalid parameter at 'imageTagMutabilityExclusionFilters' failed to satisfy constraint: 'ImageTagMutabilityExclusionFilters can't be null when imageTagMutability is set as MUTABLE'"
    )

    # when
    cfn_client.create_stack(StackName=stack_name, TemplateBody=template)

    # then
    repo_arn = f"arn:aws:ecr:eu-central-1:{ACCOUNT_ID}:repository/{name}"
    stack = cfn_client.describe_stacks(StackName=stack_name)["Stacks"][0]
    assert stack["Outputs"][0]["OutputValue"] == repo_arn

    ecr_client = boto3.client("ecr", region_name="eu-central-1")
    response = ecr_client.describe_repositories(repositoryNames=[name])

    assert response["repositories"][0]["repositoryArn"] == repo_arn
    assert response["repositories"][0]["imageTagMutability"] == "MUTABLE_WITH_EXCLUSION"


@mock_aws
def test_update_repository():
    # given
    cfn_client = boto3.client("cloudformation", region_name="eu-central-1")
    name = "test-repo"
    stack_name = "test-stack"
    template = repo_template.substitute({"repo_name": name})
    cfn_client.create_stack(StackName=stack_name, TemplateBody=template)

    template_update = copy.deepcopy(json.loads(template))
    template_update["Resources"]["Repo"]["Properties"]["ImageTagMutability"] = (
        "IMMUTABLE"
    )
    _ = template_update["Resources"]["Repo"]["Properties"].pop(
        "ImageTagMutabilityExclusionFilters", None
    )

    # when
    cfn_client.update_stack(
        StackName=stack_name, TemplateBody=json.dumps(template_update)
    )

    # then
    ecr_client = boto3.client("ecr", region_name="eu-central-1")
    response = ecr_client.describe_repositories(repositoryNames=[name])

    repo = response["repositories"][0]
    assert (
        repo["repositoryArn"]
        == f"arn:aws:ecr:eu-central-1:{ACCOUNT_ID}:repository/{name}"
    )
    assert repo["imageTagMutability"] == "IMMUTABLE"


@mock_aws
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
    assert len(response) == 0
