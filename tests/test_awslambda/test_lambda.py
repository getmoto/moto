import base64
import json
import os
from unittest import SkipTest, mock
import boto3
import hashlib
import pytest

from botocore.exceptions import ClientError, ParamValidationError
from freezegun import freeze_time
from tests.test_ecr.test_ecr_helpers import _create_image_manifest
from moto import mock_lambda, mock_s3, mock_ecr, settings
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
from uuid import uuid4
from .utilities import (
    get_role_name,
    get_test_zip_file1,
    get_test_zip_file2,
    get_test_zip_file3,
    create_invalid_lambda,
    _process_lambda,
)

_lambda_region = "us-west-2"
boto3.setup_default_session(region_name=_lambda_region)


@mock.patch.dict("os.environ", {"MOTO_ENABLE_ISO_REGIONS": "true"})
@pytest.mark.parametrize("region", ["us-west-2", "cn-northwest-1", "us-isob-east-1"])
@mock_lambda
def test_lambda_regions(region):
    client = boto3.client("lambda", region_name=region)
    resp = client.list_functions()
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200


@mock_lambda
def test_list_functions():
    conn = boto3.client("lambda", _lambda_region)
    function_name = str(uuid4())[0:6]
    initial_list = conn.list_functions()["Functions"]
    initial_names = [f["FunctionName"] for f in initial_list]
    assert function_name not in initial_names

    conn.create_function(
        FunctionName=function_name,
        Runtime="python3.7",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"ZipFile": get_test_zip_file1()},
    )
    names = [f["FunctionName"] for f in conn.list_functions()["Functions"]]
    assert function_name in names

    conn.publish_version(FunctionName=function_name, Description="v2")
    func_list = conn.list_functions()["Functions"]
    our_functions = [f for f in func_list if f["FunctionName"] == function_name]
    assert len(our_functions) == 1

    # FunctionVersion=ALL means we should get a list of all versions
    full_list = conn.list_functions(FunctionVersion="ALL")["Functions"]
    our_functions = [f for f in full_list if f["FunctionName"] == function_name]
    assert len(our_functions) == 2

    v1 = [f for f in our_functions if f["Version"] == "1"][0]
    assert v1["Description"] == "v2"
    assert (
        v1["FunctionArn"]
        == f"arn:aws:lambda:{_lambda_region}:{ACCOUNT_ID}:function:{function_name}:1"
    )

    latest = [f for f in our_functions if f["Version"] == "$LATEST"][0]
    assert latest["Description"] == ""
    assert (
        latest["FunctionArn"]
        == f"arn:aws:lambda:{_lambda_region}:{ACCOUNT_ID}:function:{function_name}:$LATEST"
    )


@mock_lambda
def test_create_based_on_s3_with_missing_bucket():
    conn = boto3.client("lambda", _lambda_region)
    function_name = str(uuid4())[0:6]

    with pytest.raises(ClientError) as exc:
        conn.create_function(
            FunctionName=function_name,
            Runtime="python2.7",
            Role=get_role_name(),
            Handler="lambda_function.lambda_handler",
            Code={"S3Bucket": "this-bucket-does-not-exist", "S3Key": "test.zip"},
            Description="test lambda function",
            Timeout=3,
            MemorySize=128,
            Publish=True,
            VpcConfig={
                "SecurityGroupIds": ["sg-123abc"],
                "SubnetIds": ["subnet-123abc"],
            },
        )
    err = exc.value.response["Error"]
    assert (
        err["Message"]
        == "Error occurred while GetObject. S3 Error Code: NoSuchBucket. S3 Error Message: The specified bucket does not exist"
    )


@mock_lambda
@mock_s3
@freeze_time("2015-01-01 00:00:00")
def test_create_function_from_aws_bucket():
    bucket_name = str(uuid4())
    s3_conn = boto3.client("s3", _lambda_region)
    s3_conn.create_bucket(
        Bucket=bucket_name,
        CreateBucketConfiguration={"LocationConstraint": _lambda_region},
    )
    zip_content = get_test_zip_file2()

    s3_conn.put_object(Bucket=bucket_name, Key="test.zip", Body=zip_content)
    conn = boto3.client("lambda", _lambda_region)
    function_name = str(uuid4())[0:6]

    result = conn.create_function(
        FunctionName=function_name,
        Runtime="python2.7",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"S3Bucket": bucket_name, "S3Key": "test.zip"},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        PackageType="ZIP",
        Publish=True,
        VpcConfig={"SecurityGroupIds": ["sg-123abc"], "SubnetIds": ["subnet-123abc"]},
    )

    assert result["FunctionName"] == function_name
    assert (
        result["FunctionArn"]
        == f"arn:aws:lambda:{_lambda_region}:{ACCOUNT_ID}:function:{function_name}"
    )
    assert result["Runtime"] == "python2.7"
    assert result["Handler"] == "lambda_function.lambda_handler"
    assert result["CodeSha256"] == base64.b64encode(
        hashlib.sha256(zip_content).digest()
    ).decode("utf-8")
    assert result["State"] == "Active"


@mock_lambda
@freeze_time("2015-01-01 00:00:00")
def test_create_function_from_zipfile():
    conn = boto3.client("lambda", _lambda_region)
    zip_content = get_test_zip_file1()
    function_name = str(uuid4())[0:6]
    result = conn.create_function(
        FunctionName=function_name,
        Runtime="python2.7",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"ZipFile": zip_content},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
    )
    # this is hard to match against, so remove it
    result["ResponseMetadata"].pop("HTTPHeaders", None)
    # Botocore inserts retry attempts not seen in Python27
    result["ResponseMetadata"].pop("RetryAttempts", None)
    result.pop("LastModified")

    assert result == {
        "Architectures": ["x86_64"],
        "EphemeralStorage": {"Size": 512},
        "FunctionName": function_name,
        "FunctionArn": f"arn:aws:lambda:{_lambda_region}:{ACCOUNT_ID}:function:{function_name}",
        "Runtime": "python2.7",
        "Role": result["Role"],
        "Handler": "lambda_function.lambda_handler",
        "CodeSize": len(zip_content),
        "Description": "test lambda function",
        "Timeout": 3,
        "MemorySize": 128,
        "CodeSha256": base64.b64encode(hashlib.sha256(zip_content).digest()).decode(
            "utf-8"
        ),
        "Version": "1",
        "VpcConfig": {"SecurityGroupIds": [], "SubnetIds": []},
        "ResponseMetadata": {"HTTPStatusCode": 201},
        "State": "Active",
        "Layers": [],
        "TracingConfig": {"Mode": "PassThrough"},
        "SnapStart": {"ApplyOn": "None", "OptimizationStatus": "Off"},
    }


@mock_lambda
def test_create_function_from_image():
    conn = boto3.client("lambda", _lambda_region)
    function_name = str(uuid4())[0:6]
    image_uri = f"{ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/testlambdaecr:prod"
    image_config = {
        "EntryPoint": [
            "python",
        ],
        "Command": [
            "/opt/app.py",
        ],
        "WorkingDirectory": "/opt",
    }
    conn.create_function(
        FunctionName=function_name,
        Role=get_role_name(),
        Code={"ImageUri": image_uri},
        Description="test lambda function",
        ImageConfig=image_config,
        PackageType="Image",
        Timeout=3,
        MemorySize=128,
        Publish=True,
    )

    result = conn.get_function(FunctionName=function_name)

    assert "ImageConfigResponse" in result["Configuration"]
    assert result["Configuration"]["ImageConfigResponse"]["ImageConfig"] == image_config


@mock_lambda
def test_create_function_error_bad_architecture():
    conn = boto3.client("lambda", _lambda_region)
    function_name = str(uuid4())[0:6]
    image_uri = f"{ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/testlambdaecr:prod"

    with pytest.raises(ClientError) as exc:
        conn.create_function(
            Architectures=["foo"],
            FunctionName=function_name,
            Role=get_role_name(),
            Code={"ImageUri": image_uri},
            Description="test lambda function",
            Timeout=3,
            MemorySize=128,
            Publish=True,
        )

    err = exc.value.response

    assert err["Error"]["Code"] == "ValidationException"
    assert (
        err["Error"]["Message"]
        == "1 validation error detected: Value '['foo']' at 'architectures' failed to satisfy"
        " constraint: Member must satisfy constraint: [Member must satisfy enum value set: "
        "[x86_64, arm64], Member must not be null]"
    )


@mock_lambda
def test_create_function_error_ephemeral_too_big():
    conn = boto3.client("lambda", _lambda_region)
    function_name = str(uuid4())[0:6]
    image_uri = f"{ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/testlambdaecr:prod"

    with pytest.raises(ClientError) as exc:
        conn.create_function(
            FunctionName=function_name,
            Role=get_role_name(),
            Code={"ImageUri": image_uri},
            Description="test lambda function",
            Timeout=3,
            MemorySize=128,
            Publish=True,
            EphemeralStorage={"Size": 3000000},
        )

    err = exc.value.response

    assert err["Error"]["Code"] == "ValidationException"
    assert (
        err["Error"]["Message"]
        == "1 validation error detected: Value '3000000' at 'ephemeralStorage.size' "
        "failed to satisfy constraint: "
        "Member must have value less than or equal to 10240"
    )


@mock_lambda
def test_create_function_error_ephemeral_too_small():
    conn = boto3.client("lambda", _lambda_region)
    function_name = str(uuid4())[0:6]
    image_uri = f"{ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/testlambdaecr:prod"

    with pytest.raises(ParamValidationError) as exc:
        conn.create_function(
            FunctionName=function_name,
            Role=get_role_name(),
            Code={"ImageUri": image_uri},
            Description="test lambda function",
            Timeout=3,
            MemorySize=128,
            Publish=True,
            EphemeralStorage={"Size": 200},
        )

    # this one is handled by botocore, not moto
    assert exc.typename == "ParamValidationError"


@mock_lambda
@pytest.mark.parametrize(
    "tracing_mode",
    [(None, "PassThrough"), ("PassThrough", "PassThrough"), ("Active", "Active")],
)
def test_create_function__with_tracingmode(tracing_mode):
    conn = boto3.client("lambda", _lambda_region)
    source, output = tracing_mode
    zip_content = get_test_zip_file1()
    function_name = str(uuid4())[0:6]
    kwargs = dict(
        FunctionName=function_name,
        Runtime="python2.7",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"ZipFile": zip_content},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
    )
    if source:
        kwargs["TracingConfig"] = {"Mode": source}
    result = conn.create_function(**kwargs)
    assert result["TracingConfig"] == {"Mode": output}


@pytest.fixture(name="with_ecr_mock")
def ecr_repo_fixture():
    with mock_ecr():
        os.environ["MOTO_LAMBDA_STUB_ECR"] = "FALSE"
        repo_name = "testlambdaecr"
        ecr_client = boto3.client("ecr", "us-east-1")
        ecr_client.create_repository(repositoryName=repo_name)
        response = ecr_client.put_image(
            repositoryName=repo_name,
            imageManifest=json.dumps(_create_image_manifest()),
            imageTag="latest",
        )
        yield response["image"]["imageId"]
        ecr_client.delete_repository(repositoryName=repo_name, force=True)
        os.environ["MOTO_LAMBDA_STUB_ECR"] = "TRUE"


@mock_lambda
def test_create_function_from_stubbed_ecr():
    lambda_client = boto3.client("lambda", "us-east-1")
    fn_name = str(uuid4())[0:6]
    image_uri = "111122223333.dkr.ecr.us-east-1.amazonaws.com/testlambda:latest"

    dic = {
        "FunctionName": fn_name,
        "Role": get_role_name(),
        "Code": {"ImageUri": image_uri},
        "PackageType": "Image",
        "Timeout": 100,
    }

    resp = lambda_client.create_function(**dic)

    assert resp["FunctionName"] == fn_name
    assert resp["CodeSize"] == 0
    assert "CodeSha256" in resp
    assert resp["PackageType"] == "Image"

    result = lambda_client.get_function(FunctionName=fn_name)
    assert "Configuration" in result
    config = result["Configuration"]
    assert "Code" in result
    code = result["Code"]
    assert code["RepositoryType"] == "ECR"
    assert code["ImageUri"] == image_uri
    image_uri_without_tag = image_uri.split(":")[0]
    resolved_image_uri = f"{image_uri_without_tag}@sha256:{config['CodeSha256']}"
    assert code["ResolvedImageUri"] == resolved_image_uri


@mock_lambda
def test_create_function_from_mocked_ecr_image_tag(
    with_ecr_mock,
):  # pylint: disable=unused-argument
    if settings.TEST_SERVER_MODE:
        raise SkipTest(
            "Envars not easily set in server mode, feature off by default, skipping..."
        )

    lambda_client = boto3.client("lambda", "us-east-1")
    fn_name = str(uuid4())[0:6]
    image = with_ecr_mock
    image_uri = f"{ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/testlambdaecr:{image['imageTag']}"

    dic = {
        "FunctionName": fn_name,
        "Role": get_role_name(),
        "Code": {"ImageUri": image_uri},
        "PackageType": "Image",
        "Timeout": 100,
    }
    resp = lambda_client.create_function(**dic)

    assert resp["FunctionName"] == fn_name
    assert resp["CodeSize"] > 0
    assert "CodeSha256" in resp
    assert resp["PackageType"] == "Image"

    result = lambda_client.get_function(FunctionName=fn_name)
    assert "Configuration" in result
    config = result["Configuration"]
    assert config["CodeSha256"] == image["imageDigest"].replace("sha256:", "")
    assert config["CodeSize"] == resp["CodeSize"]
    assert "Code" in result
    code = result["Code"]
    assert code["RepositoryType"] == "ECR"
    assert code["ImageUri"] == image_uri
    image_uri_without_tag = image_uri.split(":")[0]
    resolved_image_uri = f"{image_uri_without_tag}@sha256:{config['CodeSha256']}"
    assert code["ResolvedImageUri"] == resolved_image_uri


@mock_lambda
def test_create_function_from_mocked_ecr_image_digest(
    with_ecr_mock,
):  # pylint: disable=unused-argument
    if settings.TEST_SERVER_MODE:
        raise SkipTest(
            "Envars not easily set in server mode, feature off by default, skipping..."
        )
    lambda_client = boto3.client("lambda", "us-east-1")
    fn_name = str(uuid4())[0:6]
    image = with_ecr_mock
    image_uri = f"{ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/testlambdaecr@{image['imageDigest']}"

    dic = {
        "FunctionName": fn_name,
        "Role": get_role_name(),
        "Code": {"ImageUri": image_uri},
        "PackageType": "Image",
        "Timeout": 100,
    }
    resp = lambda_client.create_function(**dic)
    assert resp["FunctionName"] == fn_name
    assert resp["CodeSize"] > 0
    assert resp["CodeSha256"] == image["imageDigest"].replace("sha256:", "")
    assert resp["PackageType"] == "Image"


@mock_lambda
def test_create_function_from_mocked_ecr_missing_image(
    with_ecr_mock,
):  # pylint: disable=unused-argument
    if settings.TEST_SERVER_MODE:
        raise SkipTest(
            "Envars not easily set in server mode, feature off by default, skipping..."
        )

    lambda_client = boto3.client("lambda", "us-east-1")

    fn_name = str(uuid4())[0:6]
    image_uri = f"{ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/testlambdaecr:dne"

    dic = {
        "FunctionName": fn_name,
        "Role": get_role_name(),
        "Code": {"ImageUri": image_uri},
        "PackageType": "Image",
        "Timeout": 100,
    }

    with pytest.raises(ClientError) as exc:
        lambda_client.create_function(**dic)

    err = exc.value.response["Error"]
    assert err["Code"] == "ImageNotFoundException"
    assert (
        err["Message"]
        == "The image with imageId {'imageTag': 'dne'} does not exist within the repository with name 'testlambdaecr' in the registry with id '123456789012'"
    )


@mock_lambda
@mock_s3
@freeze_time("2015-01-01 00:00:00")
def test_get_function():
    bucket_name = str(uuid4())
    s3_conn = boto3.client("s3", _lambda_region)
    s3_conn.create_bucket(
        Bucket=bucket_name,
        CreateBucketConfiguration={"LocationConstraint": _lambda_region},
    )

    zip_content = get_test_zip_file1()
    s3_conn.put_object(Bucket=bucket_name, Key="test.zip", Body=zip_content)
    conn = boto3.client("lambda", _lambda_region)
    function_name = str(uuid4())[0:6]

    conn.create_function(
        FunctionName=function_name,
        Runtime="python2.7",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"S3Bucket": bucket_name, "S3Key": "test.zip"},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
        Environment={"Variables": {"test_variable": "test_value"}},
    )

    result = conn.get_function(FunctionName=function_name)
    # this is hard to match against, so remove it
    result["ResponseMetadata"].pop("HTTPHeaders", None)
    # Botocore inserts retry attempts not seen in Python27
    result["ResponseMetadata"].pop("RetryAttempts", None)
    result["Configuration"].pop("LastModified")

    assert (
        result["Code"]["Location"]
        == f"s3://awslambda-{_lambda_region}-tasks.s3-{_lambda_region}.amazonaws.com/test.zip"
    )
    assert result["Code"]["RepositoryType"] == "S3"

    assert result["Configuration"]["CodeSha256"] == base64.b64encode(
        hashlib.sha256(zip_content).digest()
    ).decode("utf-8")
    assert result["Configuration"]["CodeSize"] == len(zip_content)
    assert result["Configuration"]["Description"] == "test lambda function"
    assert "FunctionArn" in result["Configuration"]
    assert result["Configuration"]["FunctionName"] == function_name
    assert result["Configuration"]["Handler"] == "lambda_function.lambda_handler"
    assert result["Configuration"]["MemorySize"] == 128
    assert result["Configuration"]["Role"] == get_role_name()
    assert result["Configuration"]["Runtime"] == "python2.7"
    assert result["Configuration"]["Timeout"] == 3
    assert result["Configuration"]["Version"] == "$LATEST"
    assert "VpcConfig" in result["Configuration"]
    assert "Environment" in result["Configuration"]
    assert "Variables" in result["Configuration"]["Environment"]
    assert result["Configuration"]["Environment"]["Variables"] == {
        "test_variable": "test_value"
    }

    # Test get function with qualifier
    result = conn.get_function(FunctionName=function_name, Qualifier="$LATEST")
    assert result["Configuration"]["Version"] == "$LATEST"
    assert (
        result["Configuration"]["FunctionArn"]
        == f"arn:aws:lambda:us-west-2:{ACCOUNT_ID}:function:{function_name}:$LATEST"
    )

    # Test get function when can't find function name
    with pytest.raises(conn.exceptions.ResourceNotFoundException):
        conn.get_function(FunctionName="junk", Qualifier="$LATEST")


@pytest.mark.parametrize("key", ["FunctionName", "FunctionArn"])
@mock_lambda
@mock_s3
@freeze_time("2015-01-01 00:00:00")
def test_get_function_configuration(key):
    bucket_name = str(uuid4())
    s3_conn = boto3.client("s3", _lambda_region)
    s3_conn.create_bucket(
        Bucket=bucket_name,
        CreateBucketConfiguration={"LocationConstraint": _lambda_region},
    )

    zip_content = get_test_zip_file1()
    s3_conn.put_object(Bucket=bucket_name, Key="test.zip", Body=zip_content)
    conn = boto3.client("lambda", _lambda_region)
    function_name = str(uuid4())[0:6]

    fxn = conn.create_function(
        FunctionName=function_name,
        Runtime="python2.7",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"S3Bucket": bucket_name, "S3Key": "test.zip"},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
        Environment={"Variables": {"test_variable": "test_value"}},
    )
    name_or_arn = fxn[key]

    result = conn.get_function_configuration(FunctionName=name_or_arn)

    assert result["CodeSha256"] == base64.b64encode(
        hashlib.sha256(zip_content).digest()
    ).decode("utf-8")
    assert result["CodeSize"] == len(zip_content)
    assert result["Description"] == "test lambda function"
    assert "FunctionArn" in result
    assert result["FunctionName"] == function_name
    assert result["Handler"] == "lambda_function.lambda_handler"
    assert result["MemorySize"] == 128
    assert result["Role"] == get_role_name()
    assert result["Runtime"] == "python2.7"
    assert result["Timeout"] == 3
    assert result["Version"] == "$LATEST"
    assert "VpcConfig" in result
    assert "Environment" in result
    assert "Variables" in result["Environment"]
    assert result["Environment"]["Variables"] == {"test_variable": "test_value"}

    # Test get function with qualifier
    result = conn.get_function_configuration(
        FunctionName=name_or_arn, Qualifier="$LATEST"
    )
    assert result["Version"] == "$LATEST"
    assert (
        result["FunctionArn"]
        == f"arn:aws:lambda:{_lambda_region}:{ACCOUNT_ID}:function:{function_name}:$LATEST"
    )

    # Test get function when can't find function name
    with pytest.raises(conn.exceptions.ResourceNotFoundException):
        conn.get_function_configuration(FunctionName="junk", Qualifier="$LATEST")


@pytest.mark.parametrize("key", ["FunctionName", "FunctionArn"])
@mock_lambda
@mock_s3
def test_get_function_code_signing_config(key):
    bucket_name = str(uuid4())
    s3_conn = boto3.client("s3", _lambda_region)
    s3_conn.create_bucket(
        Bucket=bucket_name,
        CreateBucketConfiguration={"LocationConstraint": _lambda_region},
    )

    zip_content = get_test_zip_file1()
    s3_conn.put_object(Bucket=bucket_name, Key="test.zip", Body=zip_content)
    conn = boto3.client("lambda", _lambda_region)
    function_name = str(uuid4())[0:6]

    fxn = conn.create_function(
        FunctionName=function_name,
        Runtime="python3.7",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"S3Bucket": bucket_name, "S3Key": "test.zip"},
        CodeSigningConfigArn="csc:arn",
    )
    name_or_arn = fxn[key]

    result = conn.get_function_code_signing_config(FunctionName=name_or_arn)

    assert result["FunctionName"] == function_name
    assert result["CodeSigningConfigArn"] == "csc:arn"


@mock_lambda
@mock_s3
def test_get_function_by_arn():
    bucket_name = str(uuid4())
    s3_conn = boto3.client("s3", "us-east-1")
    s3_conn.create_bucket(
        Bucket=bucket_name,
        CreateBucketConfiguration={"LocationConstraint": _lambda_region},
    )

    zip_content = get_test_zip_file2()
    s3_conn.put_object(Bucket=bucket_name, Key="test.zip", Body=zip_content)
    conn = boto3.client("lambda", "us-east-1")
    function_name = str(uuid4())[0:6]

    fnc = conn.create_function(
        FunctionName=function_name,
        Runtime="python2.7",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"S3Bucket": bucket_name, "S3Key": "test.zip"},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
    )

    result = conn.get_function(FunctionName=fnc["FunctionArn"])
    assert result["Configuration"]["FunctionName"] == function_name


@mock_lambda
@mock_s3
def test_delete_function():
    bucket_name = str(uuid4())
    s3_conn = boto3.client("s3", _lambda_region)
    s3_conn.create_bucket(
        Bucket=bucket_name,
        CreateBucketConfiguration={"LocationConstraint": _lambda_region},
    )

    zip_content = get_test_zip_file2()
    s3_conn.put_object(Bucket=bucket_name, Key="test.zip", Body=zip_content)
    conn = boto3.client("lambda", _lambda_region)
    function_name = str(uuid4())[0:6]

    conn.create_function(
        FunctionName=function_name,
        Runtime="python2.7",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"S3Bucket": bucket_name, "S3Key": "test.zip"},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
    )

    success_result = conn.delete_function(FunctionName=function_name)
    # this is hard to match against, so remove it
    success_result["ResponseMetadata"].pop("HTTPHeaders", None)
    # Botocore inserts retry attempts not seen in Python27
    success_result["ResponseMetadata"].pop("RetryAttempts", None)

    assert success_result == {"ResponseMetadata": {"HTTPStatusCode": 204}}

    func_list = conn.list_functions()["Functions"]
    our_functions = [f for f in func_list if f["FunctionName"] == function_name]
    assert len(our_functions) == 0


@mock_lambda
@mock_s3
def test_delete_function_by_arn():
    bucket_name = str(uuid4())
    s3_conn = boto3.client("s3", "us-east-1")
    s3_conn.create_bucket(
        Bucket=bucket_name,
        CreateBucketConfiguration={"LocationConstraint": _lambda_region},
    )

    zip_content = get_test_zip_file2()
    s3_conn.put_object(Bucket=bucket_name, Key="test.zip", Body=zip_content)
    conn = boto3.client("lambda", "us-east-1")
    function_name = str(uuid4())[0:6]

    fnc = conn.create_function(
        FunctionName=function_name,
        Runtime="python2.7",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"S3Bucket": bucket_name, "S3Key": "test.zip"},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
    )

    conn.delete_function(FunctionName=fnc["FunctionArn"])

    func_list = conn.list_functions()["Functions"]
    our_functions = [f for f in func_list if f["FunctionName"] == function_name]
    assert len(our_functions) == 0


@mock_lambda
def test_delete_unknown_function():
    conn = boto3.client("lambda", _lambda_region)
    with pytest.raises(ClientError) as exc:
        conn.delete_function(FunctionName="testFunctionThatDoesntExist")
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"


@mock_lambda
@pytest.mark.parametrize(
    "name",
    [
        "bad_function_name",
        f"arn:aws:lambda:eu-west-1:{ACCOUNT_ID}:function:bad_function_name",
    ],
)
def test_publish_version_unknown_function(name):
    client = boto3.client("lambda", "eu-west-1")
    with pytest.raises(ClientError) as exc:
        client.publish_version(FunctionName=name, Description="v2")
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert (
        err["Message"]
        == f"Function not found: arn:aws:lambda:eu-west-1:{ACCOUNT_ID}:function:bad_function_name"
    )


@mock_lambda
@mock_s3
def test_publish():
    bucket_name = str(uuid4())
    s3_conn = boto3.client("s3", _lambda_region)
    s3_conn.create_bucket(
        Bucket=bucket_name,
        CreateBucketConfiguration={"LocationConstraint": _lambda_region},
    )

    zip_content = get_test_zip_file2()
    s3_conn.put_object(Bucket=bucket_name, Key="test.zip", Body=zip_content)
    conn = boto3.client("lambda", _lambda_region)
    function_name = str(uuid4())[0:6]

    conn.create_function(
        FunctionName=function_name,
        Runtime="python2.7",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"S3Bucket": bucket_name, "S3Key": "test.zip"},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=False,
    )

    function_list = conn.list_functions(FunctionVersion="ALL")["Functions"]
    our_functions = [f for f in function_list if f["FunctionName"] == function_name]
    assert len(our_functions) == 1
    latest_arn = our_functions[0]["FunctionArn"]

    res = conn.publish_version(FunctionName=function_name)
    assert res["ResponseMetadata"]["HTTPStatusCode"] == 201

    function_list = conn.list_functions(FunctionVersion="ALL")["Functions"]
    our_functions = [f for f in function_list if f["FunctionName"] == function_name]
    assert len(our_functions) == 2

    # #SetComprehension ;-)
    published_arn = list({f["FunctionArn"] for f in our_functions} - {latest_arn})[0]
    assert f"{function_name}:1" in published_arn

    conn.delete_function(FunctionName=function_name, Qualifier="1")

    function_list = conn.list_functions()["Functions"]
    our_functions = [f for f in function_list if f["FunctionName"] == function_name]
    assert len(our_functions) == 1
    assert function_name in our_functions[0]["FunctionArn"]


@mock_lambda
@mock_s3
@freeze_time("2015-01-01 00:00:00")
def test_list_create_list_get_delete_list():
    """
    test `list -> create -> list -> get -> delete -> list` integration

    """
    bucket_name = str(uuid4())
    s3_conn = boto3.client("s3", _lambda_region)
    s3_conn.create_bucket(
        Bucket=bucket_name,
        CreateBucketConfiguration={"LocationConstraint": _lambda_region},
    )

    zip_content = get_test_zip_file2()
    s3_conn.put_object(Bucket=bucket_name, Key="test.zip", Body=zip_content)
    conn = boto3.client("lambda", _lambda_region)
    function_name = str(uuid4())[0:6]

    initial_list = conn.list_functions()["Functions"]
    initial_names = [f["FunctionName"] for f in initial_list]
    assert function_name not in initial_names

    function_name = function_name
    conn.create_function(
        FunctionName=function_name,
        Runtime="python2.7",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"S3Bucket": bucket_name, "S3Key": "test.zip"},
        Description="test lambda function",
        EphemeralStorage={"Size": 2500},
        Timeout=3,
        MemorySize=128,
        Publish=True,
    )
    expected_function_result = {
        "Code": {
            "Location": f"s3://awslambda-{_lambda_region}-tasks.s3-{_lambda_region}.amazonaws.com/test.zip",
            "RepositoryType": "S3",
        },
        "Configuration": {
            "CodeSha256": base64.b64encode(hashlib.sha256(zip_content).digest()).decode(
                "utf-8"
            ),
            "CodeSize": len(zip_content),
            "Description": "test lambda function",
            "FunctionName": function_name,
            "Handler": "lambda_function.lambda_handler",
            "MemorySize": 128,
            "Role": get_role_name(),
            "Runtime": "python2.7",
            "Timeout": 3,
            "Version": "$LATEST",
            "VpcConfig": {"SecurityGroupIds": [], "SubnetIds": []},
            "State": "Active",
            "Layers": [],
            "LastUpdateStatus": "Successful",
            "TracingConfig": {"Mode": "PassThrough"},
            "Architectures": ["x86_64"],
            "EphemeralStorage": {"Size": 2500},
            "SnapStart": {"ApplyOn": "None", "OptimizationStatus": "Off"},
        },
        "ResponseMetadata": {"HTTPStatusCode": 200},
    }
    functions = conn.list_functions()["Functions"]
    func_names = [f["FunctionName"] for f in functions]
    assert function_name in func_names

    func_arn = [
        f["FunctionArn"] for f in functions if f["FunctionName"] == function_name
    ][0]
    assert (
        func_arn
        == f"arn:aws:lambda:{_lambda_region}:{ACCOUNT_ID}:function:{function_name}"
    )
    functions = conn.list_functions(FunctionVersion="ALL")["Functions"]
    our_functions = [f for f in functions if f["FunctionName"] == function_name]
    assert len(our_functions) == 2

    latest = [f for f in our_functions if f["Version"] == "$LATEST"][0]
    assert (
        latest["FunctionArn"]
        == f"arn:aws:lambda:{_lambda_region}:{ACCOUNT_ID}:function:{function_name}:$LATEST"
    )
    latest.pop("FunctionArn")
    latest.pop("LastModified")
    assert latest == expected_function_result["Configuration"]

    published = [f for f in our_functions if f["Version"] != "$LATEST"][0]
    assert published["Version"] == "1"
    assert (
        published["FunctionArn"]
        == f"arn:aws:lambda:{_lambda_region}:{ACCOUNT_ID}:function:{function_name}:1"
    )

    func = conn.get_function(FunctionName=function_name)

    assert (
        func["Configuration"]["FunctionArn"]
        == f"arn:aws:lambda:{_lambda_region}:{ACCOUNT_ID}:function:{function_name}"
    )

    # this is hard to match against, so remove it
    func["ResponseMetadata"].pop("HTTPHeaders", None)
    # Botocore inserts retry attempts not seen in Python27
    func["ResponseMetadata"].pop("RetryAttempts", None)
    func["Configuration"].pop("LastModified")
    func["Configuration"].pop("FunctionArn")

    assert func == expected_function_result
    conn.delete_function(FunctionName=function_name)

    functions = conn.list_functions()["Functions"]
    func_names = [f["FunctionName"] for f in functions]
    assert function_name not in func_names


@mock_lambda
@freeze_time("2015-01-01 00:00:00")
def test_get_function_created_with_zipfile():
    conn = boto3.client("lambda", _lambda_region)
    function_name = str(uuid4())[0:6]
    zip_content = get_test_zip_file1()
    conn.create_function(
        FunctionName=function_name,
        Runtime="python2.7",
        Role=get_role_name(),
        Handler="lambda_function.handler",
        Code={"ZipFile": zip_content},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
    )

    response = conn.get_function(FunctionName=function_name)

    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert len(response["Code"]) == 2
    assert response["Code"]["RepositoryType"] == "S3"
    assert response["Code"]["Location"].startswith(
        f"s3://awslambda-{_lambda_region}-tasks.s3-{_lambda_region}.amazonaws.com"
    )
    assert "Configuration" in response
    config = response["Configuration"]
    assert config["CodeSha256"] == base64.b64encode(
        hashlib.sha256(zip_content).digest()
    ).decode("utf-8")
    assert config["CodeSize"] == len(zip_content)
    assert config["Description"] == "test lambda function"
    assert (
        config["FunctionArn"]
        == f"arn:aws:lambda:{_lambda_region}:{ACCOUNT_ID}:function:{function_name}"
    )
    assert config["FunctionName"] == function_name
    assert config["Handler"] == "lambda_function.handler"
    assert config["MemorySize"] == 128
    assert config["Role"] == get_role_name()
    assert config["Runtime"] == "python2.7"
    assert config["Timeout"] == 3
    assert config["Version"] == "$LATEST"
    assert config["State"] == "Active"
    assert config["Layers"] == []
    assert config["LastUpdateStatus"] == "Successful"


@mock_lambda
@mock_s3
def test_list_versions_by_function():
    bucket_name = str(uuid4())
    s3_conn = boto3.client("s3", _lambda_region)
    s3_conn.create_bucket(
        Bucket=bucket_name,
        CreateBucketConfiguration={"LocationConstraint": _lambda_region},
    )

    zip_content = get_test_zip_file2()
    s3_conn.put_object(Bucket=bucket_name, Key="test.zip", Body=zip_content)
    conn = boto3.client("lambda", _lambda_region)
    function_name = str(uuid4())[0:6]

    conn.create_function(
        FunctionName=function_name,
        Runtime="python2.7",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"S3Bucket": bucket_name, "S3Key": "test.zip"},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
    )
    conn.update_function_code(FunctionName=function_name, ZipFile=get_test_zip_file1())

    res = conn.publish_version(FunctionName=function_name)
    assert res["ResponseMetadata"]["HTTPStatusCode"] == 201
    versions = conn.list_versions_by_function(FunctionName=function_name)
    assert len(versions["Versions"]) == 3
    assert (
        versions["Versions"][0]["FunctionArn"]
        == f"arn:aws:lambda:us-west-2:{ACCOUNT_ID}:function:{function_name}:$LATEST"
    )
    assert (
        versions["Versions"][1]["FunctionArn"]
        == f"arn:aws:lambda:us-west-2:{ACCOUNT_ID}:function:{function_name}:1"
    )
    assert (
        versions["Versions"][2]["FunctionArn"]
        == f"arn:aws:lambda:us-west-2:{ACCOUNT_ID}:function:{function_name}:2"
    )

    conn.create_function(
        FunctionName="testFunction_2",
        Runtime="python2.7",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"S3Bucket": bucket_name, "S3Key": "test.zip"},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=False,
    )
    versions = conn.list_versions_by_function(FunctionName="testFunction_2")
    assert len(versions["Versions"]) == 1
    assert (
        versions["Versions"][0]["FunctionArn"]
        == f"arn:aws:lambda:us-west-2:{ACCOUNT_ID}:function:testFunction_2:$LATEST"
    )


@mock_lambda
@mock_s3
def test_list_aliases():
    bucket_name = str(uuid4())
    s3_conn = boto3.client("s3", _lambda_region)
    s3_conn.create_bucket(
        Bucket=bucket_name,
        CreateBucketConfiguration={"LocationConstraint": _lambda_region},
    )

    zip_content = get_test_zip_file2()
    s3_conn.put_object(Bucket=bucket_name, Key="test.zip", Body=zip_content)
    conn = boto3.client("lambda", _lambda_region)
    function_name = str(uuid4())[0:6]
    function_name2 = str(uuid4())[0:6]

    conn.create_function(
        FunctionName=function_name,
        Runtime="python2.7",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"S3Bucket": bucket_name, "S3Key": "test.zip"},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
    )

    conn.create_function(
        FunctionName=function_name2,
        Runtime="python2.7",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"S3Bucket": bucket_name, "S3Key": "test.zip"},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
    )

    first_version = conn.publish_version(FunctionName=function_name)["Version"]

    conn.create_alias(
        FunctionName=function_name,
        Name="alias1",
        FunctionVersion=first_version,
    )

    conn.update_function_code(FunctionName=function_name, ZipFile=get_test_zip_file1())
    second_version = conn.publish_version(FunctionName=function_name)["Version"]

    conn.create_alias(
        FunctionName=function_name,
        Name="alias2",
        FunctionVersion=second_version,
    )

    conn.create_alias(
        FunctionName=function_name,
        Name="alias0",
        FunctionVersion=second_version,
    )

    aliases = conn.list_aliases(FunctionName=function_name)
    assert len(aliases["Aliases"]) == 3

    # should be ordered by their alias name (as per SDK response)
    assert (
        aliases["Aliases"][0]["AliasArn"]
        == f"arn:aws:lambda:us-west-2:{ACCOUNT_ID}:function:{function_name}:alias0"
    )
    assert aliases["Aliases"][0]["FunctionVersion"] == second_version

    assert (
        aliases["Aliases"][1]["AliasArn"]
        == f"arn:aws:lambda:us-west-2:{ACCOUNT_ID}:function:{function_name}:alias1"
    )
    assert aliases["Aliases"][1]["FunctionVersion"] == first_version

    assert (
        aliases["Aliases"][2]["AliasArn"]
        == f"arn:aws:lambda:us-west-2:{ACCOUNT_ID}:function:{function_name}:alias2"
    )
    assert aliases["Aliases"][2]["FunctionVersion"] == second_version

    res = conn.publish_version(FunctionName=function_name2)
    conn.create_alias(
        FunctionName=function_name2,
        Name="alias1",
        FunctionVersion=res["Version"],
    )

    aliases = conn.list_aliases(FunctionName=function_name2)

    assert len(aliases["Aliases"]) == 1
    assert (
        aliases["Aliases"][0]["AliasArn"]
        == f"arn:aws:lambda:us-west-2:{ACCOUNT_ID}:function:{function_name2}:alias1"
    )


@mock_lambda
@mock_s3
def test_create_function_with_already_exists():
    bucket_name = str(uuid4())
    s3_conn = boto3.client("s3", _lambda_region)
    s3_conn.create_bucket(
        Bucket=bucket_name,
        CreateBucketConfiguration={"LocationConstraint": _lambda_region},
    )

    zip_content = get_test_zip_file2()
    s3_conn.put_object(Bucket=bucket_name, Key="test.zip", Body=zip_content)
    conn = boto3.client("lambda", _lambda_region)
    function_name = str(uuid4())[0:6]

    conn.create_function(
        FunctionName=function_name,
        Runtime="python2.7",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"S3Bucket": bucket_name, "S3Key": "test.zip"},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
    )

    response = conn.create_function(
        FunctionName=function_name,
        Runtime="python2.7",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"S3Bucket": bucket_name, "S3Key": "test.zip"},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
    )

    assert response["FunctionName"] == function_name


@mock_lambda
@mock_s3
def test_list_versions_by_function_for_nonexistent_function():
    conn = boto3.client("lambda", _lambda_region)
    function_name = str(uuid4())[0:6]
    versions = conn.list_versions_by_function(FunctionName=function_name)

    assert len(versions["Versions"]) == 0


@pytest.mark.parametrize("key", ["FunctionName", "FunctionArn"])
@mock_lambda
@mock_s3
def test_update_configuration(key):
    bucket_name = str(uuid4())
    function_name = str(uuid4())[0:6]
    s3_conn = boto3.client("s3", _lambda_region)
    s3_conn.create_bucket(
        Bucket=bucket_name,
        CreateBucketConfiguration={"LocationConstraint": _lambda_region},
    )

    zip_content = get_test_zip_file2()
    s3_conn.put_object(Bucket=bucket_name, Key="test.zip", Body=zip_content)
    conn = boto3.client("lambda", _lambda_region)

    fxn = conn.create_function(
        FunctionName=function_name,
        Runtime="python2.7",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"S3Bucket": bucket_name, "S3Key": "test.zip"},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
        Environment={"Variables": {"test_old_environment": "test_old_value"}},
    )
    name_or_arn = fxn[key]

    assert fxn["Description"] == "test lambda function"
    assert fxn["Handler"] == "lambda_function.lambda_handler"
    assert fxn["MemorySize"] == 128
    assert fxn["Runtime"] == "python2.7"
    assert fxn["Timeout"] == 3

    updated_config = conn.update_function_configuration(
        FunctionName=name_or_arn,
        Description="updated test lambda function",
        Handler="lambda_function.new_lambda_handler",
        Runtime="python3.6",
        Timeout=7,
        VpcConfig={"SecurityGroupIds": ["sg-123abc"], "SubnetIds": ["subnet-123abc"]},
        Environment={"Variables": {"test_environment": "test_value"}},
    )

    assert updated_config["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert updated_config["Description"] == "updated test lambda function"
    assert updated_config["Handler"] == "lambda_function.new_lambda_handler"
    assert updated_config["MemorySize"] == 128
    assert updated_config["Runtime"] == "python3.6"
    assert updated_config["Timeout"] == 7
    assert updated_config["Environment"]["Variables"] == {
        "test_environment": "test_value"
    }
    assert updated_config["VpcConfig"] == {
        "SecurityGroupIds": ["sg-123abc"],
        "SubnetIds": ["subnet-123abc"],
        "VpcId": "vpc-123abc",
    }


@pytest.mark.parametrize("key", ["FunctionName", "FunctionArn"])
@mock_lambda
def test_update_function_zip(key):
    conn = boto3.client("lambda", _lambda_region)

    zip_content_one = get_test_zip_file1()
    function_name = str(uuid4())[0:6]

    fxn = conn.create_function(
        FunctionName=function_name,
        Runtime="python2.7",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"ZipFile": zip_content_one},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
    )
    name_or_arn = fxn[key]
    first_sha = fxn["CodeSha256"]

    zip_content_two = get_test_zip_file2()

    update1 = conn.update_function_code(
        FunctionName=name_or_arn, ZipFile=zip_content_two, Publish=True
    )
    assert update1["CodeSha256"] != first_sha

    response = conn.get_function(FunctionName=function_name, Qualifier="2")

    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert len(response["Code"]) == 2
    assert response["Code"]["RepositoryType"] == "S3"
    assert response["Code"]["Location"].startswith(
        f"s3://awslambda-{_lambda_region}-tasks.s3-{_lambda_region}.amazonaws.com"
    )

    config = response["Configuration"]
    assert config["CodeSize"] == len(zip_content_two)
    assert config["Description"] == "test lambda function"
    assert (
        config["FunctionArn"]
        == f"arn:aws:lambda:{_lambda_region}:{ACCOUNT_ID}:function:{function_name}:2"
    )
    assert config["FunctionName"] == function_name
    assert config["Version"] == "2"
    assert config["LastUpdateStatus"] == "Successful"
    assert config["CodeSha256"] == update1["CodeSha256"]

    most_recent_config = conn.get_function(FunctionName=function_name)
    assert most_recent_config["Configuration"]["CodeSha256"] == update1["CodeSha256"]

    # Publishing this again, with the same code, gives us the same version
    same_update = conn.update_function_code(
        FunctionName=name_or_arn, ZipFile=zip_content_two, Publish=True
    )
    assert (
        same_update["FunctionArn"]
        == most_recent_config["Configuration"]["FunctionArn"] + ":2"
    )
    assert same_update["Version"] == "2"

    # Only when updating the code should we have a new version
    new_update = conn.update_function_code(
        FunctionName=name_or_arn, ZipFile=get_test_zip_file3(), Publish=True
    )
    assert (
        new_update["FunctionArn"]
        == most_recent_config["Configuration"]["FunctionArn"] + ":3"
    )
    assert new_update["Version"] == "3"


@mock_lambda
@mock_s3
def test_update_function_s3():
    bucket_name = str(uuid4())
    s3_conn = boto3.client("s3", _lambda_region)
    s3_conn.create_bucket(
        Bucket=bucket_name,
        CreateBucketConfiguration={"LocationConstraint": _lambda_region},
    )

    zip_content = get_test_zip_file1()
    s3_conn.put_object(Bucket=bucket_name, Key="test.zip", Body=zip_content)

    conn = boto3.client("lambda", _lambda_region)
    function_name = str(uuid4())[0:6]

    conn.create_function(
        FunctionName=function_name,
        Runtime="python2.7",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"S3Bucket": bucket_name, "S3Key": "test.zip"},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
    )

    zip_content_two = get_test_zip_file2()
    s3_conn.put_object(Bucket=bucket_name, Key="test2.zip", Body=zip_content_two)

    conn.update_function_code(
        FunctionName=function_name,
        S3Bucket=bucket_name,
        S3Key="test2.zip",
        Publish=True,
    )

    response = conn.get_function(FunctionName=function_name, Qualifier="2")

    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert len(response["Code"]) == 2
    assert response["Code"]["RepositoryType"] == "S3"
    assert response["Code"]["Location"].startswith(
        f"s3://awslambda-{_lambda_region}-tasks.s3-{_lambda_region}.amazonaws.com"
    )

    config = response["Configuration"]
    assert config["CodeSha256"] == base64.b64encode(
        hashlib.sha256(zip_content_two).digest()
    ).decode("utf-8")
    assert config["CodeSize"] == len(zip_content_two)
    assert config["Description"] == "test lambda function"
    assert (
        config["FunctionArn"]
        == f"arn:aws:lambda:{_lambda_region}:{ACCOUNT_ID}:function:{function_name}:2"
    )
    assert config["FunctionName"] == function_name
    assert config["Version"] == "2"
    assert config["LastUpdateStatus"] == "Successful"


@mock_lambda
def test_create_function_with_invalid_arn():
    err = create_invalid_lambda("test-iam-role")
    assert (
        err.value.response["Error"]["Message"]
        == r"1 validation error detected: Value 'test-iam-role' at 'role' failed to satisfy constraint: Member must satisfy regular expression pattern: arn:(aws[a-zA-Z-]*)?:iam::(\d{12}):role/?[a-zA-Z_0-9+=,.@\-_/]+"
    )


@mock_lambda
def test_create_function_with_arn_from_different_account():
    err = create_invalid_lambda("arn:aws:iam::000000000000:role/example_role")
    assert (
        err.value.response["Error"]["Message"]
        == "Cross-account pass role is not allowed."
    )


@mock_lambda
def test_create_function_with_unknown_arn():
    err = create_invalid_lambda(
        "arn:aws:iam::" + str(ACCOUNT_ID) + ":role/service-role/unknown_role"
    )
    assert (
        err.value.response["Error"]["Message"]
        == "The role defined for the function cannot be assumed by Lambda."
    )


@mock_lambda
def test_remove_unknown_permission_throws_error():
    conn = boto3.client("lambda", _lambda_region)
    zip_content = get_test_zip_file1()
    function_name = str(uuid4())[0:6]
    f = conn.create_function(
        FunctionName=function_name,
        Runtime="python3.7",
        Role=(get_role_name()),
        Handler="lambda_function.handler",
        Code={"ZipFile": zip_content},
    )
    arn = f["FunctionArn"]

    with pytest.raises(ClientError) as exc:
        conn.remove_permission(FunctionName=arn, StatementId="1")
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert err["Message"] == "No policy is associated with the given resource."


@mock_lambda
def test_multiple_qualifiers():
    client = boto3.client("lambda", "us-east-1")

    zip_content = get_test_zip_file1()
    fn_name = str(uuid4())[0:6]
    client.create_function(
        FunctionName=fn_name,
        Runtime="python3.7",
        Role=(get_role_name()),
        Handler="lambda_function.handler",
        Code={"ZipFile": zip_content},
    )

    for _ in range(10):
        new_zip = _process_lambda(f"func content {_}")
        client.update_function_code(FunctionName=fn_name, ZipFile=new_zip)
        client.publish_version(FunctionName=fn_name)

    resp = client.list_versions_by_function(FunctionName=fn_name)["Versions"]
    qualis = [fn["FunctionArn"].split(":")[-1] for fn in resp]
    assert qualis == ["$LATEST", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]

    client.delete_function(FunctionName=fn_name, Qualifier="4")
    client.delete_function(FunctionName=fn_name, Qualifier="5")

    resp = client.list_versions_by_function(FunctionName=fn_name)["Versions"]
    qualis = [fn["FunctionArn"].split(":")[-1] for fn in resp]
    assert qualis == ["$LATEST", "1", "2", "3", "6", "7", "8", "9", "10"]

    fn = client.get_function(FunctionName=fn_name, Qualifier="6")["Configuration"]
    assert (
        fn["FunctionArn"]
        == f"arn:aws:lambda:us-east-1:{ACCOUNT_ID}:function:{fn_name}:6"
    )


def test_get_role_name_utility_race_condition():
    # Play with these variables as needed to reproduce the error.
    max_workers, num_threads = 3, 15

    errors = []
    roles = []

    def thread_function(_):
        while True:
            # noinspection PyBroadException
            try:
                role = get_role_name()
            except ClientError as e:
                errors.append(str(e))
                break
            except Exception:
                # boto3 and our own IAMBackend are not thread-safe,
                # and occasionally throw weird errors, so we just
                # pass and retry.
                # https://github.com/boto/boto3/issues/1592
                pass
            else:
                roles.append(role)
                break

    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        executor.map(thread_function, range(num_threads))
    # Check all threads are accounted for, all roles are the same entity,
    # and there are no client errors.
    assert len(errors) + len(roles) == num_threads
    assert roles.count(roles[0]) == len(roles)
    assert len(errors) == 0
