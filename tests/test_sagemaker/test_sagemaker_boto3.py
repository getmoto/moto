# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import datetime
import boto3
from botocore.exceptions import ClientError, ParamValidationError
import sure  # noqa

from moto import mock_sagemaker, mock_iam
from moto.sagemaker.models import VpcConfig
from moto.sts.models import ACCOUNT_ID
from nose.tools import assert_true, assert_equal, assert_raises

TEST_REGION_NAME = "us-east-1"
FAKE_SUBNET_ID = "subnet-012345678"
FAKE_SECURITY_GROUP_IDS = ["sg-0123456789abcdef0", "sg-0123456789abcdef1"]
FAKE_ROLE_ARN = f"arn:aws:iam::{ACCOUNT_ID}:role/FakeRole"
FAKE_KMS_KEY_ID = "62d4509a-9f96-446c-a9ba-6b1c353c8c58"
GENERIC_TAGS_PARAM = [
    {"Key": "newkey1", "Value": "newval1"},
    {"Key": "newkey2", "Value": "newval2"},
]
FAKE_LIFECYCLE_CONFIG_NAME = "FakeLifecycleConfigName"
FAKE_DEFAULT_CODE_REPO = "https://github.com/user/repo1"
FAKE_ADDL_CODE_REPOS = [
    "https://github.com/user/repo2",
    "https://github.com/user/repo2",
]


class MySageMakerModel(object):
    def __init__(self, name, arn, container=None, vpc_config=None):
        self.name = name
        self.arn = arn
        self.container = container if container else {}
        self.vpc_config = (
            vpc_config if vpc_config else {"sg-groups": ["sg-123"], "subnets": ["123"]}
        )

    def save(self):
        client = boto3.client("sagemaker", region_name="us-east-1")
        vpc_config = VpcConfig(
            self.vpc_config.get("sg-groups"), self.vpc_config.get("subnets")
        )
        client.create_model(
            ModelName=self.name,
            ExecutionRoleArn=self.arn,
            VpcConfig=vpc_config.response_object,
        )


@mock_sagemaker
def test_describe_model():
    client = boto3.client("sagemaker", region_name="us-east-1")
    test_model = MySageMakerModel(
        name="blah",
        arn="arn:aws:sagemaker:eu-west-1:000000000000:x-x/foobar",
        vpc_config={"sg-groups": ["sg-123"], "subnets": ["123"]},
    )
    test_model.save()
    model = client.describe_model(ModelName="blah")
    assert model.get("ModelName").should.equal("blah")


@mock_sagemaker
def test_create_model():
    client = boto3.client("sagemaker", region_name="us-east-1")
    vpc_config = VpcConfig(["sg-foobar"], ["subnet-xxx"])
    arn = "arn:aws:sagemaker:eu-west-1:000000000000:x-x/foobar"
    model = client.create_model(
        ModelName="blah", ExecutionRoleArn=arn, VpcConfig=vpc_config.response_object
    )

    assert model["ModelArn"].should.equal(arn)


@mock_sagemaker
def test_delete_model():
    client = boto3.client("sagemaker", region_name="us-east-1")
    name = "blah"
    arn = "arn:aws:sagemaker:eu-west-1:000000000000:x-x/foobar"
    test_model = MySageMakerModel(name=name, arn=arn)
    test_model.save()

    assert len(client.list_models()["Models"]).should.equal(1)
    client.delete_model(ModelName=name)
    assert len(client.list_models()["Models"]).should.equal(0)


@mock_sagemaker
def test_delete_model_not_found():
    with assert_raises(ClientError) as err:
        boto3.client("sagemaker", region_name="us-east-1").delete_model(
            ModelName="blah"
        )
    assert err.exception.response["Error"]["Code"].should.equal("404")


@mock_sagemaker
def test_list_models():
    client = boto3.client("sagemaker", region_name="us-east-1")
    name = "blah"
    arn = "arn:aws:sagemaker:eu-west-1:000000000000:x-x/foobar"
    test_model = MySageMakerModel(name=name, arn=arn)
    test_model.save()
    models = client.list_models()
    assert len(models["Models"]).should.equal(1)
    assert models["Models"][0]["ModelName"].should.equal(name)
    assert models["Models"][0]["ModelArn"].should.equal(arn)


@mock_sagemaker
def test_list_models_multiple():
    client = boto3.client("sagemaker", region_name="us-east-1")

    name_model_1 = "blah"
    arn_model_1 = "arn:aws:sagemaker:eu-west-1:000000000000:x-x/foobar"
    test_model_1 = MySageMakerModel(name=name_model_1, arn=arn_model_1)
    test_model_1.save()

    name_model_2 = "blah2"
    arn_model_2 = "arn:aws:sagemaker:eu-west-1:000000000000:x-x/foobar2"
    test_model_2 = MySageMakerModel(name=name_model_2, arn=arn_model_2)
    test_model_2.save()
    models = client.list_models()
    assert len(models["Models"]).should.equal(2)


@mock_sagemaker
def test_list_models_none():
    client = boto3.client("sagemaker", region_name="us-east-1")
    models = client.list_models()
    assert len(models["Models"]).should.equal(0)


@mock_sagemaker
def test_create_notebook_instance_minimal_params():

    sagemaker = boto3.client("sagemaker", region_name=TEST_REGION_NAME)

    NAME_PARAM = "MyNotebookInstance"
    INSTANCE_TYPE_PARAM = "ml.t2.medium"

    args = {
        "NotebookInstanceName": NAME_PARAM,
        "InstanceType": INSTANCE_TYPE_PARAM,
        "RoleArn": FAKE_ROLE_ARN,
    }
    resp = sagemaker.create_notebook_instance(**args)
    assert_true(resp["NotebookInstanceArn"].startswith("arn:aws:sagemaker"))
    assert_true(resp["NotebookInstanceArn"].endswith(args["NotebookInstanceName"]))

    resp = sagemaker.describe_notebook_instance(NotebookInstanceName=NAME_PARAM)
    assert_true(resp["NotebookInstanceArn"].startswith("arn:aws:sagemaker"))
    assert_true(resp["NotebookInstanceArn"].endswith(args["NotebookInstanceName"]))
    assert_equal(resp["NotebookInstanceName"], NAME_PARAM)
    assert_equal(resp["NotebookInstanceStatus"], "InService")
    assert_equal(resp["Url"], f"{NAME_PARAM}.notebook.{TEST_REGION_NAME}.sagemaker.aws")
    assert_equal(resp["InstanceType"], INSTANCE_TYPE_PARAM)
    assert_equal(resp["RoleArn"], FAKE_ROLE_ARN)
    assert_true(isinstance(resp["LastModifiedTime"], datetime.datetime))
    assert_true(isinstance(resp["CreationTime"], datetime.datetime))
    assert_equal(resp["DirectInternetAccess"], "Enabled")
    assert_equal(resp["VolumeSizeInGB"], 5)


#    assert_equal(resp["RootAccess"], True)     # ToDo: Not sure if this defaults...


@mock_sagemaker
def test_create_notebook_instance_params():

    sagemaker = boto3.client("sagemaker", region_name="us-east-1")

    NAME_PARAM = "MyNotebookInstance"
    INSTANCE_TYPE_PARAM = "ml.t2.medium"
    DIRECT_INTERNET_ACCESS_PARAM = "Enabled"
    VOLUME_SIZE_IN_GB_PARAM = 7
    ACCELERATOR_TYPES_PARAM = ["ml.eia1.medium", "ml.eia2.medium"]
    ROOT_ACCESS_PARAM = "Disabled"

    args = {
        "NotebookInstanceName": NAME_PARAM,
        "InstanceType": INSTANCE_TYPE_PARAM,
        "SubnetId": FAKE_SUBNET_ID,
        "SecurityGroupIds": FAKE_SECURITY_GROUP_IDS,
        "RoleArn": FAKE_ROLE_ARN,
        "KmsKeyId": FAKE_KMS_KEY_ID,
        "Tags": GENERIC_TAGS_PARAM,
        "LifecycleConfigName": FAKE_LIFECYCLE_CONFIG_NAME,
        "DirectInternetAccess": DIRECT_INTERNET_ACCESS_PARAM,
        "VolumeSizeInGB": VOLUME_SIZE_IN_GB_PARAM,
        "AcceleratorTypes": ACCELERATOR_TYPES_PARAM,
        "DefaultCodeRepository": FAKE_DEFAULT_CODE_REPO,
        "AdditionalCodeRepositories": FAKE_ADDL_CODE_REPOS,
        "RootAccess": ROOT_ACCESS_PARAM,
    }
    resp = sagemaker.create_notebook_instance(**args)
    assert_true(resp["NotebookInstanceArn"].startswith("arn:aws:sagemaker"))
    assert_true(resp["NotebookInstanceArn"].endswith(args["NotebookInstanceName"]))

    resp = sagemaker.describe_notebook_instance(NotebookInstanceName=NAME_PARAM)
    assert_true(resp["NotebookInstanceArn"].startswith("arn:aws:sagemaker"))
    assert_true(resp["NotebookInstanceArn"].endswith(args["NotebookInstanceName"]))
    assert_equal(resp["NotebookInstanceName"], NAME_PARAM)
    assert_equal(resp["NotebookInstanceStatus"], "InService")
    assert_equal(resp["Url"], f"{NAME_PARAM}.notebook.{TEST_REGION_NAME}.sagemaker.aws")
    assert_equal(resp["InstanceType"], INSTANCE_TYPE_PARAM)
    assert_equal(resp["RoleArn"], FAKE_ROLE_ARN)
    assert_true(isinstance(resp["LastModifiedTime"], datetime.datetime))
    assert_true(isinstance(resp["CreationTime"], datetime.datetime))
    assert_equal(resp["DirectInternetAccess"], "Enabled")
    assert_equal(resp["VolumeSizeInGB"], VOLUME_SIZE_IN_GB_PARAM)
    #    assert_equal(resp["RootAccess"], True)     # ToDo: Not sure if this defaults...
    assert_equal(resp["SubnetId"], FAKE_SUBNET_ID)
    assert_equal(resp["SecurityGroups"], FAKE_SECURITY_GROUP_IDS)
    assert_equal(resp["KmsKeyId"], FAKE_KMS_KEY_ID)
    assert_equal(
        resp["NotebookInstanceLifecycleConfigName"], FAKE_LIFECYCLE_CONFIG_NAME
    )
    assert_equal(resp["AcceleratorTypes"], ACCELERATOR_TYPES_PARAM)
    assert_equal(resp["DefaultCodeRepository"], FAKE_DEFAULT_CODE_REPO)
    assert_equal(resp["AdditionalCodeRepositories"], FAKE_ADDL_CODE_REPOS)

    resp = sagemaker.list_tags(ResourceArn=resp["NotebookInstanceArn"])
    assert_equal(resp["Tags"], GENERIC_TAGS_PARAM)


@mock_sagemaker
def test_create_notebook_instance_bad_volume_size():

    sagemaker = boto3.client("sagemaker", region_name="us-east-1")

    vol_size = 2
    args = {
        "NotebookInstanceName": "MyNotebookInstance",
        "InstanceType": "ml.t2.medium",
        "RoleArn": FAKE_ROLE_ARN,
        "VolumeSizeInGB": vol_size,
    }
    with assert_raises(ParamValidationError) as ex:
        resp = sagemaker.create_notebook_instance(**args)
    assert_equal(
        ex.exception.args[0],
        f"Parameter validation failed:\nInvalid range for parameter VolumeSizeInGB, value: {vol_size}, valid range: 5-inf",
    )


@mock_sagemaker
def test_create_notebook_instance_invalid_instance_type():

    sagemaker = boto3.client("sagemaker", region_name="us-east-1")

    instance_type = "undefined_instance_type"
    args = {
        "NotebookInstanceName": "MyNotebookInstance",
        "InstanceType": instance_type,
        "RoleArn": FAKE_ROLE_ARN,
    }
    with assert_raises(ClientError) as ex:
        resp = sagemaker.create_notebook_instance(**args)
    assert_equal(ex.exception.response["Error"]["Code"], "ValidationException")
    expected_message = f"Value '{instance_type}' at 'instanceType' failed to satisfy constraint: Member must satisfy enum value set: ["
    assert_true(expected_message in ex.exception.response["Error"]["Message"])


@mock_sagemaker
def test_notebook_instance_lifecycle():
    sagemaker = boto3.client("sagemaker", region_name=TEST_REGION_NAME)

    NAME_PARAM = "MyNotebookInstance"
    INSTANCE_TYPE_PARAM = "ml.t2.medium"

    args = {
        "NotebookInstanceName": NAME_PARAM,
        "InstanceType": INSTANCE_TYPE_PARAM,
        "RoleArn": FAKE_ROLE_ARN,
    }
    resp = sagemaker.create_notebook_instance(**args)
    assert_true(resp["NotebookInstanceArn"].startswith("arn:aws:sagemaker"))
    assert_true(resp["NotebookInstanceArn"].endswith(args["NotebookInstanceName"]))

    resp = sagemaker.describe_notebook_instance(NotebookInstanceName=NAME_PARAM)
    notebook_instance_arn = resp["NotebookInstanceArn"]

    with assert_raises(ClientError) as ex:
        sagemaker.delete_notebook_instance(NotebookInstanceName=NAME_PARAM)
    assert_equal(ex.exception.response["Error"]["Code"], "ValidationException")
    expected_message = f"Status (InService) not in ([Stopped, Failed]). Unable to transition to (Deleting) for Notebook Instance ({notebook_instance_arn})"
    assert_true(expected_message in ex.exception.response["Error"]["Message"])

    sagemaker.stop_notebook_instance(NotebookInstanceName=NAME_PARAM)

    resp = sagemaker.describe_notebook_instance(NotebookInstanceName=NAME_PARAM)
    assert_equal(resp["NotebookInstanceStatus"], "Stopped")

    sagemaker.start_notebook_instance(NotebookInstanceName=NAME_PARAM)

    resp = sagemaker.describe_notebook_instance(NotebookInstanceName=NAME_PARAM)
    assert_equal(resp["NotebookInstanceStatus"], "InService")

    sagemaker.stop_notebook_instance(NotebookInstanceName=NAME_PARAM)

    resp = sagemaker.describe_notebook_instance(NotebookInstanceName=NAME_PARAM)
    assert_equal(resp["NotebookInstanceStatus"], "Stopped")

    sagemaker.delete_notebook_instance(NotebookInstanceName=NAME_PARAM)

    with assert_raises(ClientError) as ex:
        sagemaker.describe_notebook_instance(NotebookInstanceName=NAME_PARAM)
    assert_equal(ex.exception.response["Error"]["Message"], "RecordNotFound")
