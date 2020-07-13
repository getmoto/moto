# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import datetime
import boto3
from botocore.exceptions import ClientError, ParamValidationError
import sure  # noqa

from moto import mock_sagemaker
from moto.sts.models import ACCOUNT_ID
from nose.tools import assert_true, assert_equal, assert_raises

TEST_REGION_NAME = "us-east-1"
FAKE_SUBNET_ID = "subnet-012345678"
FAKE_SECURITY_GROUP_IDS = ["sg-0123456789abcdef0", "sg-0123456789abcdef1"]
FAKE_ROLE_ARN = "arn:aws:iam::{}:role/FakeRole".format(ACCOUNT_ID)
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
    assert_equal(
        resp["Url"], "{}.notebook.{}.sagemaker.aws".format(NAME_PARAM, TEST_REGION_NAME)
    )
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
    assert_equal(
        resp["Url"], "{}.notebook.{}.sagemaker.aws".format(NAME_PARAM, TEST_REGION_NAME)
    )
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
        "Parameter validation failed:\nInvalid range for parameter VolumeSizeInGB, value: {}, valid range: 5-inf".format(
            vol_size
        ),
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
    expected_message = "Value '{}' at 'instanceType' failed to satisfy constraint: Member must satisfy enum value set: [".format(
        instance_type
    )

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
    expected_message = "Status (InService) not in ([Stopped, Failed]). Unable to transition to (Deleting) for Notebook Instance ({})".format(
        notebook_instance_arn
    )
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


@mock_sagemaker
def test_describe_nonexistent_model():
    sagemaker = boto3.client("sagemaker", region_name=TEST_REGION_NAME)

    with assert_raises(ClientError) as e:
        resp = sagemaker.describe_model(ModelName="Nonexistent")
    assert_true(
        e.exception.response["Error"]["Message"].startswith("Could not find model")
    )
