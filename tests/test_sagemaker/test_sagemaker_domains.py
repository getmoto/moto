"""Unit tests for sagemaker-supported APIs."""

import datetime

import boto3

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_aws
def test_create_domain():
    client = boto3.client("sagemaker", region_name="us-east-2")
    resp = client.create_domain(
        DomainName="testdomain",
        AuthMode="IAM",
        DefaultUserSettings={
            "ExecutionRole": f"arn:aws:iam::{ACCOUNT_ID}:role/iamrole-domain-execution",
            "SecurityGroups": ["sg-12345678901234567"],
            "SharingSettings": {
                "NotebookOutputOption": "Allowed",
                "S3OutputPath": "s3://output",
            },
        },
        SubnetIds=["subnet-12345678901234567"],
        VpcId="VpcId",
        AppNetworkAccessType="PublicInternetOnly",
        Tags=[{"Key": "string", "Value": "string"}],
    )

    assert (
        resp["DomainArn"]
        == f"arn:aws:sagemaker:us-east-2:{ACCOUNT_ID}:domain/d-testdomain"
    )
    assert resp["Url"] == "testdomain.us-east-2.sagemaker.test.com"


@mock_aws
def test_describe_domain():
    client = boto3.client("sagemaker", region_name="ap-southeast-1")
    client.create_domain(
        DomainName="testdomain",
        AuthMode="IAM",
        DefaultUserSettings={
            "ExecutionRole": f"arn:aws:iam::{ACCOUNT_ID}:role/iamrole-domain-execution",
            "SecurityGroups": ["sg-12345678901234567"],
            "SharingSettings": {
                "NotebookOutputOption": "Allowed",
                "S3OutputPath": "s3://output",
            },
        },
        SubnetIds=["subnet-12345678901234567"],
        VpcId="VpcId",
        AppNetworkAccessType="PublicInternetOnly",
        HomeEfsFileSystemKmsKeyId="testHomeEfsFileSystemKmsKeyId",
        KmsKeyId="testKmsKeyId",
        DefaultSpaceSettings={
            "ExecutionRole": f"arn:aws:iam::{ACCOUNT_ID}:role/iamrole-space-execution",
            "SecurityGroups": [
                "sg-12345678901234564",
            ],
            "JupyterServerAppSettings": {
                "DefaultResourceSpec": {
                    "SageMakerImageArn": "SageMakerImageArn",
                    "SageMakerImageVersionArn": "SageMakerImageVersionArn",
                    "SageMakerImageVersionAlias": "SageMakerImageVersionAlias",
                    "InstanceType": "system",
                    "LifecycleConfigArn": "LifecycleConfigArn",
                },
                "LifecycleConfigArns": [
                    "LifecycleConfigArns",
                ],
                "CodeRepositories": [
                    {"RepositoryUrl": "RepositoryUrl"},
                ],
            },
        },
        Tags=[{"Key": "string", "Value": "string"}],
    )
    resp = client.describe_domain(DomainId="d-testdomain")
    assert (
        resp["DomainArn"]
        == f"arn:aws:sagemaker:ap-southeast-1:{ACCOUNT_ID}:domain/d-testdomain"
    )
    assert resp["DomainId"] == "d-testdomain"
    assert resp["DomainName"] == "testdomain"
    assert resp["HomeEfsFileSystemId"] == "testdomain-efs-id"
    assert resp["SingleSignOnManagedApplicationInstanceId"] == "testdomain-sso-id"
    assert (
        resp["SingleSignOnApplicationArn"]
        == "arn:aws:sagemaker::123456789012:sso/application/testdomain/apl-testdomain"
    )
    assert resp["Status"] == "InService"
    assert isinstance(resp["CreationTime"], datetime.datetime)
    assert isinstance(resp["LastModifiedTime"], datetime.datetime)
    assert resp["FailureReason"] == ""
    assert resp["SecurityGroupIdForDomainBoundary"] == "sg-testdomain"
    assert resp["AuthMode"] == "IAM"
    assert resp["DefaultUserSettings"] == {
        "ExecutionRole": f"arn:aws:iam::{ACCOUNT_ID}:role/iamrole-domain-execution",
        "SecurityGroups": ["sg-12345678901234567"],
        "SharingSettings": {
            "NotebookOutputOption": "Allowed",
            "S3OutputPath": "s3://output",
        },
    }


@mock_aws
def test_describe_domain_defaults():
    client = boto3.client("sagemaker", region_name="ap-southeast-1")
    resp = client.create_domain(
        DomainName="testdomain",
        AuthMode="IAM",
        DefaultUserSettings={},
        SubnetIds=["subnet-12345678901234567"],
        VpcId="VpcId",
    )
    resp = client.describe_domain(DomainId="d-testdomain")
    assert (
        resp["DomainArn"]
        == f"arn:aws:sagemaker:ap-southeast-1:{ACCOUNT_ID}:domain/d-testdomain"
    )
    assert resp["DomainId"] == "d-testdomain"
    assert resp["DomainName"] == "testdomain"
    assert resp["HomeEfsFileSystemId"] == "testdomain-efs-id"
    assert resp["SingleSignOnManagedApplicationInstanceId"] == "testdomain-sso-id"
    assert (
        resp["SingleSignOnApplicationArn"]
        == "arn:aws:sagemaker::123456789012:sso/application/testdomain/apl-testdomain"
    )
    assert resp["Status"] == "InService"
    assert isinstance(resp["CreationTime"], datetime.datetime)
    assert isinstance(resp["LastModifiedTime"], datetime.datetime)
    assert resp["FailureReason"] == ""
    assert resp["SecurityGroupIdForDomainBoundary"] == "sg-testdomain"
    assert resp["AuthMode"] == "IAM"
    assert resp["DefaultUserSettings"] == {}


@mock_aws
def test_list_domains():
    client = boto3.client("sagemaker", region_name="us-east-2")
    client.create_domain(
        DomainName="testdomain",
        AuthMode="IAM",
        DefaultUserSettings={},
        SubnetIds=["subnet-12345678901234567"],
        VpcId="VpcId",
    )
    client.create_domain(
        DomainName="testdomain2",
        AuthMode="IAM",
        DefaultUserSettings={},
        SubnetIds=["subnet-12345678901234567"],
        VpcId="VpcId",
    )
    resp = client.list_domains()
    assert len(resp["Domains"]) == 2
    assert (
        resp["Domains"][0]["DomainArn"]
        == "arn:aws:sagemaker:us-east-2:123456789012:domain/d-testdomain"
    )
    assert resp["Domains"][0]["DomainId"] == "d-testdomain"
    assert resp["Domains"][0]["DomainName"] == "testdomain"
    assert resp["Domains"][0]["Status"] == "InService"
    assert isinstance(resp["Domains"][0]["CreationTime"], datetime.datetime)
    assert isinstance(resp["Domains"][0]["LastModifiedTime"], datetime.datetime)
    assert resp["Domains"][0]["Url"] == "testdomain.us-east-2.sagemaker.test.com"
    assert (
        resp["Domains"][1]["DomainArn"]
        == "arn:aws:sagemaker:us-east-2:123456789012:domain/d-testdomain2"
    )
    assert resp["Domains"][1]["DomainId"] == "d-testdomain2"
    assert resp["Domains"][1]["DomainName"] == "testdomain2"
    assert resp["Domains"][1]["Status"] == "InService"
    assert isinstance(resp["Domains"][1]["CreationTime"], datetime.datetime)
    assert isinstance(resp["Domains"][1]["LastModifiedTime"], datetime.datetime)
    assert resp["Domains"][1]["Url"] == "testdomain2.us-east-2.sagemaker.test.com"


@mock_aws
def test_delete_domain():
    client = boto3.client("sagemaker", region_name="us-east-2")
    client.create_domain(
        DomainName="testdomain",
        AuthMode="IAM",
        DefaultUserSettings={},
        SubnetIds=["subnet-12345678901234567"],
        VpcId="VpcId",
    )
    client.create_domain(
        DomainName="testdomain2",
        AuthMode="IAM",
        DefaultUserSettings={},
        SubnetIds=["subnet-12345678901234567"],
        VpcId="VpcId",
    )
    client.delete_domain(DomainId="d-testdomain2")
    resp = client.list_domains()
    assert len(resp["Domains"]) == 1
    assert (
        resp["Domains"][0]["DomainArn"]
        == "arn:aws:sagemaker:us-east-2:123456789012:domain/d-testdomain"
    )
    assert resp["Domains"][0]["DomainId"] == "d-testdomain"
    assert resp["Domains"][0]["DomainName"] == "testdomain"


@mock_aws
def test_tag_domain():
    client = boto3.client("sagemaker", region_name="us-east-2")
    resp = client.create_domain(
        DomainName="testdomain",
        AuthMode="IAM",
        DefaultUserSettings={
            "ExecutionRole": f"arn:aws:iam::{ACCOUNT_ID}:role/iamrole-domain-execution",
            "SecurityGroups": ["sg-12345678901234567"],
            "SharingSettings": {
                "NotebookOutputOption": "Allowed",
                "S3OutputPath": "s3://output",
            },
        },
        SubnetIds=["subnet-12345678901234567"],
        VpcId="VpcId",
        AppNetworkAccessType="PublicInternetOnly",
        Tags=[{"Key": "testkey", "Value": "testvalue"}],
    )
    tags1 = client.list_tags(ResourceArn=resp["DomainArn"])
    assert tags1["Tags"] == [{"Key": "testkey", "Value": "testvalue"}]
    client.add_tags(
        ResourceArn=resp["DomainArn"], Tags=[{"Key": "testkey2", "Value": "testvalue2"}]
    )
    tags2 = client.list_tags(ResourceArn=resp["DomainArn"])
    assert tags2["Tags"] == [
        {"Key": "testkey", "Value": "testvalue"},
        {"Key": "testkey2", "Value": "testvalue2"},
    ]
    client.delete_tags(ResourceArn=resp["DomainArn"], TagKeys=["testkey"])
    tags3 = client.list_tags(ResourceArn=resp["DomainArn"])
    assert tags3["Tags"] == [{"Key": "testkey2", "Value": "testvalue2"}]
