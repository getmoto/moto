import datetime
import boto3
from botocore.exceptions import ClientError
import sure  # noqa # pylint: disable=unused-import

from moto import mock_sagemaker
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
import pytest

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
FAKE_NAME_PARAM = "MyNotebookInstance"
FAKE_INSTANCE_TYPE_PARAM = "ml.t2.medium"


@pytest.fixture(name="sagemaker_client")
def fixture_sagemaker_client():
    with mock_sagemaker():
        yield boto3.client("sagemaker", region_name=TEST_REGION_NAME)


def _get_notebook_instance_arn(notebook_name):
    return f"arn:aws:sagemaker:{TEST_REGION_NAME}:{ACCOUNT_ID}:notebook-instance/{notebook_name}"


def _get_notebook_instance_lifecycle_arn(lifecycle_name):
    return f"arn:aws:sagemaker:{TEST_REGION_NAME}:{ACCOUNT_ID}:notebook-instance-lifecycle-configuration/{lifecycle_name}"


def test_create_notebook_instance_minimal_params(sagemaker_client):
    args = {
        "NotebookInstanceName": FAKE_NAME_PARAM,
        "InstanceType": FAKE_INSTANCE_TYPE_PARAM,
        "RoleArn": FAKE_ROLE_ARN,
    }
    resp = sagemaker_client.create_notebook_instance(**args)
    expected_notebook_arn = _get_notebook_instance_arn(FAKE_NAME_PARAM)
    assert resp["NotebookInstanceArn"] == expected_notebook_arn

    resp = sagemaker_client.describe_notebook_instance(
        NotebookInstanceName=FAKE_NAME_PARAM
    )
    assert resp["NotebookInstanceArn"] == expected_notebook_arn
    assert resp["NotebookInstanceName"] == FAKE_NAME_PARAM
    assert resp["NotebookInstanceStatus"] == "InService"
    assert resp["Url"] == f"{FAKE_NAME_PARAM}.notebook.{TEST_REGION_NAME}.sagemaker.aws"
    assert resp["InstanceType"] == FAKE_INSTANCE_TYPE_PARAM
    assert resp["RoleArn"] == FAKE_ROLE_ARN
    assert isinstance(resp["LastModifiedTime"], datetime.datetime)
    assert isinstance(resp["CreationTime"], datetime.datetime)
    assert resp["DirectInternetAccess"] == "Enabled"
    assert resp["VolumeSizeInGB"] == 5


#    assert resp["RootAccess"] == True     # ToDo: Not sure if this defaults...


def test_create_notebook_instance_params(sagemaker_client):
    fake_direct_internet_access_param = "Enabled"
    volume_size_in_gb_param = 7
    accelerator_types_param = ["ml.eia1.medium", "ml.eia2.medium"]
    root_access_param = "Disabled"

    args = {
        "NotebookInstanceName": FAKE_NAME_PARAM,
        "InstanceType": FAKE_INSTANCE_TYPE_PARAM,
        "SubnetId": FAKE_SUBNET_ID,
        "SecurityGroupIds": FAKE_SECURITY_GROUP_IDS,
        "RoleArn": FAKE_ROLE_ARN,
        "KmsKeyId": FAKE_KMS_KEY_ID,
        "Tags": GENERIC_TAGS_PARAM,
        "LifecycleConfigName": FAKE_LIFECYCLE_CONFIG_NAME,
        "DirectInternetAccess": fake_direct_internet_access_param,
        "VolumeSizeInGB": volume_size_in_gb_param,
        "AcceleratorTypes": accelerator_types_param,
        "DefaultCodeRepository": FAKE_DEFAULT_CODE_REPO,
        "AdditionalCodeRepositories": FAKE_ADDL_CODE_REPOS,
        "RootAccess": root_access_param,
    }
    resp = sagemaker_client.create_notebook_instance(**args)
    expected_notebook_arn = _get_notebook_instance_arn(FAKE_NAME_PARAM)
    assert resp["NotebookInstanceArn"] == expected_notebook_arn

    resp = sagemaker_client.describe_notebook_instance(
        NotebookInstanceName=FAKE_NAME_PARAM
    )
    assert resp["NotebookInstanceArn"] == expected_notebook_arn
    assert resp["NotebookInstanceName"] == FAKE_NAME_PARAM
    assert resp["NotebookInstanceStatus"] == "InService"
    assert resp["Url"] == f"{FAKE_NAME_PARAM}.notebook.{TEST_REGION_NAME}.sagemaker.aws"
    assert resp["InstanceType"] == FAKE_INSTANCE_TYPE_PARAM
    assert resp["RoleArn"] == FAKE_ROLE_ARN
    assert isinstance(resp["LastModifiedTime"], datetime.datetime)
    assert isinstance(resp["CreationTime"], datetime.datetime)
    assert resp["DirectInternetAccess"] == "Enabled"
    assert resp["VolumeSizeInGB"] == volume_size_in_gb_param
    #    assert resp["RootAccess"] == True     # ToDo: Not sure if this defaults...
    assert resp["SubnetId"] == FAKE_SUBNET_ID
    assert resp["SecurityGroups"] == FAKE_SECURITY_GROUP_IDS
    assert resp["KmsKeyId"] == FAKE_KMS_KEY_ID
    assert resp["NotebookInstanceLifecycleConfigName"] == FAKE_LIFECYCLE_CONFIG_NAME
    assert resp["AcceleratorTypes"] == accelerator_types_param
    assert resp["DefaultCodeRepository"] == FAKE_DEFAULT_CODE_REPO
    assert resp["AdditionalCodeRepositories"] == FAKE_ADDL_CODE_REPOS

    resp = sagemaker_client.list_tags(ResourceArn=resp["NotebookInstanceArn"])
    assert resp["Tags"] == GENERIC_TAGS_PARAM


def test_create_notebook_instance_invalid_instance_type(sagemaker_client):
    instance_type = "undefined_instance_type"
    args = {
        "NotebookInstanceName": "MyNotebookInstance",
        "InstanceType": instance_type,
        "RoleArn": FAKE_ROLE_ARN,
    }
    with pytest.raises(ClientError) as ex:
        sagemaker_client.create_notebook_instance(**args)
    assert ex.value.response["Error"]["Code"] == "ValidationException"
    expected_message = "Value '{}' at 'instanceType' failed to satisfy constraint: Member must satisfy enum value set: [".format(
        instance_type
    )

    assert expected_message in ex.value.response["Error"]["Message"]


def test_notebook_instance_lifecycle(sagemaker_client):
    args = {
        "NotebookInstanceName": FAKE_NAME_PARAM,
        "InstanceType": FAKE_INSTANCE_TYPE_PARAM,
        "RoleArn": FAKE_ROLE_ARN,
    }
    resp = sagemaker_client.create_notebook_instance(**args)
    expected_notebook_arn = _get_notebook_instance_arn(FAKE_NAME_PARAM)
    assert resp["NotebookInstanceArn"] == expected_notebook_arn

    resp = sagemaker_client.describe_notebook_instance(
        NotebookInstanceName=FAKE_NAME_PARAM
    )
    notebook_instance_arn = resp["NotebookInstanceArn"]

    with pytest.raises(ClientError) as ex:
        sagemaker_client.delete_notebook_instance(NotebookInstanceName=FAKE_NAME_PARAM)
    assert ex.value.response["Error"]["Code"] == "ValidationException"
    expected_message = "Status (InService) not in ([Stopped, Failed]). Unable to transition to (Deleting) for Notebook Instance ({})".format(
        notebook_instance_arn
    )
    assert expected_message in ex.value.response["Error"]["Message"]

    sagemaker_client.stop_notebook_instance(NotebookInstanceName=FAKE_NAME_PARAM)

    resp = sagemaker_client.describe_notebook_instance(
        NotebookInstanceName=FAKE_NAME_PARAM
    )
    assert resp["NotebookInstanceStatus"] == "Stopped"

    sagemaker_client.start_notebook_instance(NotebookInstanceName=FAKE_NAME_PARAM)

    resp = sagemaker_client.describe_notebook_instance(
        NotebookInstanceName=FAKE_NAME_PARAM
    )
    assert resp["NotebookInstanceStatus"] == "InService"

    sagemaker_client.stop_notebook_instance(NotebookInstanceName=FAKE_NAME_PARAM)

    resp = sagemaker_client.describe_notebook_instance(
        NotebookInstanceName=FAKE_NAME_PARAM
    )
    assert resp["NotebookInstanceStatus"] == "Stopped"

    sagemaker_client.delete_notebook_instance(NotebookInstanceName=FAKE_NAME_PARAM)

    with pytest.raises(ClientError) as ex:
        sagemaker_client.describe_notebook_instance(
            NotebookInstanceName=FAKE_NAME_PARAM
        )
    assert ex.value.response["Error"]["Message"] == "RecordNotFound"


def test_describe_nonexistent_model(sagemaker_client):
    with pytest.raises(ClientError) as e:
        sagemaker_client.describe_model(ModelName="Nonexistent")
    assert e.value.response["Error"]["Message"].startswith("Could not find model")


def test_notebook_instance_lifecycle_config(sagemaker_client):
    name = "MyLifeCycleConfig"
    on_create = [{"Content": "Create Script Line 1"}]
    on_start = [{"Content": "Start Script Line 1"}]
    resp = sagemaker_client.create_notebook_instance_lifecycle_config(
        NotebookInstanceLifecycleConfigName=name, OnCreate=on_create, OnStart=on_start
    )
    expected_arn = _get_notebook_instance_lifecycle_arn(name)
    assert resp["NotebookInstanceLifecycleConfigArn"] == expected_arn

    with pytest.raises(ClientError) as e:
        sagemaker_client.create_notebook_instance_lifecycle_config(
            NotebookInstanceLifecycleConfigName=name,
            OnCreate=on_create,
            OnStart=on_start,
        )
    assert e.value.response["Error"]["Message"].endswith(
        "Notebook Instance Lifecycle Config already exists.)"
    )

    resp = sagemaker_client.describe_notebook_instance_lifecycle_config(
        NotebookInstanceLifecycleConfigName=name
    )
    assert resp["NotebookInstanceLifecycleConfigName"] == name
    assert resp["NotebookInstanceLifecycleConfigArn"] == expected_arn
    assert resp["OnStart"] == on_start
    assert resp["OnCreate"] == on_create
    assert isinstance(resp["LastModifiedTime"], datetime.datetime)
    assert isinstance(resp["CreationTime"], datetime.datetime)

    sagemaker_client.delete_notebook_instance_lifecycle_config(
        NotebookInstanceLifecycleConfigName=name
    )

    with pytest.raises(ClientError) as e:
        sagemaker_client.describe_notebook_instance_lifecycle_config(
            NotebookInstanceLifecycleConfigName=name
        )
    assert e.value.response["Error"]["Message"].endswith(
        "Notebook Instance Lifecycle Config does not exist.)"
    )

    with pytest.raises(ClientError) as e:
        sagemaker_client.delete_notebook_instance_lifecycle_config(
            NotebookInstanceLifecycleConfigName=name
        )
    assert e.value.response["Error"]["Message"].endswith(
        "Notebook Instance Lifecycle Config does not exist.)"
    )


def test_add_tags_to_notebook(sagemaker_client):
    args = {
        "NotebookInstanceName": FAKE_NAME_PARAM,
        "InstanceType": FAKE_INSTANCE_TYPE_PARAM,
        "RoleArn": FAKE_ROLE_ARN,
    }
    resp = sagemaker_client.create_notebook_instance(**args)
    resource_arn = resp["NotebookInstanceArn"]

    tags = [
        {"Key": "myKey", "Value": "myValue"},
    ]
    response = sagemaker_client.add_tags(ResourceArn=resource_arn, Tags=tags)
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

    response = sagemaker_client.list_tags(ResourceArn=resource_arn)
    assert response["Tags"] == tags


def test_delete_tags_from_notebook(sagemaker_client):
    args = {
        "NotebookInstanceName": FAKE_NAME_PARAM,
        "InstanceType": FAKE_INSTANCE_TYPE_PARAM,
        "RoleArn": FAKE_ROLE_ARN,
    }
    resp = sagemaker_client.create_notebook_instance(**args)
    resource_arn = resp["NotebookInstanceArn"]

    tags = [
        {"Key": "myKey", "Value": "myValue"},
    ]
    response = sagemaker_client.add_tags(ResourceArn=resource_arn, Tags=tags)
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

    tag_keys = [tag["Key"] for tag in tags]
    response = sagemaker_client.delete_tags(ResourceArn=resource_arn, TagKeys=tag_keys)
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

    response = sagemaker_client.list_tags(ResourceArn=resource_arn)
    assert response["Tags"] == []
