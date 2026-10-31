import re
from uuid import uuid4

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID

from .utilities import get_role_name, get_test_zip_file1

PYTHON_VERSION = "python3.11"
REGION = "us-east-1"
SIGNING_PROFILE_VERSION_ARN = (
    f"arn:aws:signer:{REGION}:{ACCOUNT_ID}:/signing-profiles/MyProfile/abcdef1234"
)
CSC_ARN_PATTERN = re.compile(
    rf"^arn:aws:lambda:{REGION}:{ACCOUNT_ID}:code-signing-config:csc-[a-z0-9]{{17}}$"
)


def create_code_signing_config(client, **kwargs):
    return client.create_code_signing_config(
        AllowedPublishers={"SigningProfileVersionArns": [SIGNING_PROFILE_VERSION_ARN]},
        **kwargs,
    )["CodeSigningConfig"]


def create_function(client):
    return client.create_function(
        FunctionName=str(uuid4())[0:6],
        Runtime=PYTHON_VERSION,
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"ZipFile": get_test_zip_file1()},
    )


@mock_aws
def test_create_code_signing_config():
    client = boto3.client("lambda", REGION)

    resp = client.create_code_signing_config(
        Description="my config",
        AllowedPublishers={"SigningProfileVersionArns": [SIGNING_PROFILE_VERSION_ARN]},
        CodeSigningPolicies={"UntrustedArtifactOnDeployment": "Enforce"},
    )

    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 201
    config = resp["CodeSigningConfig"]
    assert CSC_ARN_PATTERN.match(config["CodeSigningConfigArn"])
    assert config["CodeSigningConfigArn"].endswith(config["CodeSigningConfigId"])
    assert config["Description"] == "my config"
    assert config["AllowedPublishers"] == {
        "SigningProfileVersionArns": [SIGNING_PROFILE_VERSION_ARN]
    }
    assert config["CodeSigningPolicies"] == {"UntrustedArtifactOnDeployment": "Enforce"}
    assert "LastModified" in config


@mock_aws
def test_create_code_signing_config_defaults_to_warn():
    client = boto3.client("lambda", REGION)

    config = create_code_signing_config(client)

    assert config["CodeSigningPolicies"] == {"UntrustedArtifactOnDeployment": "Warn"}
    assert config["Description"] == ""


@mock_aws
def test_get_code_signing_config():
    client = boto3.client("lambda", REGION)
    arn = create_code_signing_config(client, Description="my config")[
        "CodeSigningConfigArn"
    ]

    config = client.get_code_signing_config(CodeSigningConfigArn=arn)[
        "CodeSigningConfig"
    ]

    assert config["CodeSigningConfigArn"] == arn
    assert config["Description"] == "my config"


@mock_aws
def test_get_unknown_code_signing_config():
    client = boto3.client("lambda", REGION)
    arn = f"arn:aws:lambda:{REGION}:{ACCOUNT_ID}:code-signing-config:csc-0123456789abcdef0"

    with pytest.raises(ClientError) as exc:
        client.get_code_signing_config(CodeSigningConfigArn=arn)

    err = exc.value.response
    assert err["ResponseMetadata"]["HTTPStatusCode"] == 404
    assert err["Error"]["Code"] == "ResourceNotFoundException"


@mock_aws
def test_update_code_signing_config():
    client = boto3.client("lambda", REGION)
    arn = create_code_signing_config(client, Description="old")["CodeSigningConfigArn"]

    config = client.update_code_signing_config(
        CodeSigningConfigArn=arn,
        CodeSigningPolicies={"UntrustedArtifactOnDeployment": "Enforce"},
    )["CodeSigningConfig"]

    # Only the fields that are provided are updated
    assert config["Description"] == "old"
    assert config["CodeSigningPolicies"] == {"UntrustedArtifactOnDeployment": "Enforce"}

    config = client.get_code_signing_config(CodeSigningConfigArn=arn)[
        "CodeSigningConfig"
    ]
    assert config["CodeSigningPolicies"] == {"UntrustedArtifactOnDeployment": "Enforce"}


@mock_aws
def test_delete_code_signing_config():
    client = boto3.client("lambda", REGION)
    arn = create_code_signing_config(client)["CodeSigningConfigArn"]

    resp = client.delete_code_signing_config(CodeSigningConfigArn=arn)
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 204

    with pytest.raises(ClientError) as exc:
        client.get_code_signing_config(CodeSigningConfigArn=arn)
    assert exc.value.response["Error"]["Code"] == "ResourceNotFoundException"


@mock_aws
def test_delete_code_signing_config_that_is_in_use():
    client = boto3.client("lambda", REGION)
    arn = create_code_signing_config(client)["CodeSigningConfigArn"]
    function_name = create_function(client)["FunctionName"]
    client.put_function_code_signing_config(
        FunctionName=function_name, CodeSigningConfigArn=arn
    )

    with pytest.raises(ClientError) as exc:
        client.delete_code_signing_config(CodeSigningConfigArn=arn)
    err = exc.value.response
    assert err["ResponseMetadata"]["HTTPStatusCode"] == 409
    assert err["Error"]["Code"] == "ResourceConflictException"

    # The config can be deleted once no function uses it anymore
    client.delete_function_code_signing_config(FunctionName=function_name)
    client.delete_code_signing_config(CodeSigningConfigArn=arn)


@mock_aws
def test_list_code_signing_configs():
    client = boto3.client("lambda", REGION)
    arns = [
        create_code_signing_config(client)["CodeSigningConfigArn"] for _ in range(3)
    ]

    page = client.list_code_signing_configs(MaxItems=2)
    assert len(page["CodeSigningConfigs"]) == 2
    assert "NextMarker" in page

    next_page = client.list_code_signing_configs(MaxItems=2, Marker=page["NextMarker"])
    assert len(next_page["CodeSigningConfigs"]) == 1
    assert "NextMarker" not in next_page

    listed = page["CodeSigningConfigs"] + next_page["CodeSigningConfigs"]
    assert sorted(c["CodeSigningConfigArn"] for c in listed) == sorted(arns)


@mock_aws
def test_function_code_signing_config():
    client = boto3.client("lambda", REGION)
    arn = create_code_signing_config(client)["CodeSigningConfigArn"]
    function_name = create_function(client)["FunctionName"]

    resp = client.put_function_code_signing_config(
        FunctionName=function_name, CodeSigningConfigArn=arn
    )
    assert resp["CodeSigningConfigArn"] == arn
    assert resp["FunctionName"] == function_name

    resp = client.get_function_code_signing_config(FunctionName=function_name)
    assert resp["CodeSigningConfigArn"] == arn

    resp = client.delete_function_code_signing_config(FunctionName=function_name)
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 204

    resp = client.get_function_code_signing_config(FunctionName=function_name)
    assert resp.get("CodeSigningConfigArn") is None


@mock_aws
def test_put_function_code_signing_config_with_unknown_config():
    client = boto3.client("lambda", REGION)
    function_name = create_function(client)["FunctionName"]
    arn = f"arn:aws:lambda:{REGION}:{ACCOUNT_ID}:code-signing-config:csc-0123456789abcdef0"

    with pytest.raises(ClientError) as exc:
        client.put_function_code_signing_config(
            FunctionName=function_name, CodeSigningConfigArn=arn
        )

    err = exc.value.response
    assert err["ResponseMetadata"]["HTTPStatusCode"] == 404
    assert err["Error"]["Code"] == "CodeSigningConfigNotFoundException"


@mock_aws
def test_list_functions_by_code_signing_config():
    client = boto3.client("lambda", REGION)
    arn = create_code_signing_config(client)["CodeSigningConfigArn"]
    other_arn = create_code_signing_config(client)["CodeSigningConfigArn"]
    functions = [create_function(client) for _ in range(3)]
    for fn in functions[:2]:
        client.put_function_code_signing_config(
            FunctionName=fn["FunctionName"], CodeSigningConfigArn=arn
        )
    client.put_function_code_signing_config(
        FunctionName=functions[2]["FunctionName"], CodeSigningConfigArn=other_arn
    )

    function_arns = client.list_functions_by_code_signing_config(
        CodeSigningConfigArn=arn
    )["FunctionArns"]

    assert sorted(function_arns) == sorted(fn["FunctionArn"] for fn in functions[:2])

    page = client.list_functions_by_code_signing_config(
        CodeSigningConfigArn=arn, MaxItems=1
    )
    assert len(page["FunctionArns"]) == 1
    assert "NextMarker" in page


@mock_aws
def test_list_functions_by_unknown_code_signing_config():
    client = boto3.client("lambda", REGION)
    arn = f"arn:aws:lambda:{REGION}:{ACCOUNT_ID}:code-signing-config:csc-0123456789abcdef0"

    with pytest.raises(ClientError) as exc:
        client.list_functions_by_code_signing_config(CodeSigningConfigArn=arn)

    assert exc.value.response["Error"]["Code"] == "ResourceNotFoundException"


@mock_aws
def test_code_signing_config_tags():
    client = boto3.client("lambda", REGION)
    arn = create_code_signing_config(client, Tags={"team": "a"})["CodeSigningConfigArn"]
    assert client.list_tags(Resource=arn)["Tags"] == {"team": "a"}

    client.tag_resource(Resource=arn, Tags={"env": "test"})
    client.untag_resource(Resource=arn, TagKeys=["team"])
    assert client.list_tags(Resource=arn)["Tags"] == {"env": "test"}

    rgta = boto3.client("resourcegroupstaggingapi", REGION)
    resources = rgta.get_resources(ResourceTypeFilters=["lambda:code-signing-config"])[
        "ResourceTagMappingList"
    ]
    assert [r["ResourceARN"] for r in resources] == [arn]
