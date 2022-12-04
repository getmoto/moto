import base64
import json
import os
from unittest import SkipTest
import botocore.client
import boto3
import hashlib
import sure  # noqa # pylint: disable=unused-import
import pytest

from botocore.exceptions import ClientError
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


@pytest.mark.parametrize("region", ["us-west-2", "cn-northwest-1"])
@mock_lambda
def test_lambda_regions(region):
    client = boto3.client("lambda", region_name=region)
    resp = client.list_functions()
    resp["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)


@mock_lambda
def test_list_functions():
    conn = boto3.client("lambda", _lambda_region)
    function_name = str(uuid4())[0:6]
    initial_list = conn.list_functions()["Functions"]
    initial_names = [f["FunctionName"] for f in initial_list]
    initial_names.shouldnt.contain(function_name)

    conn.create_function(
        FunctionName=function_name,
        Runtime="python3.7",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"ZipFile": get_test_zip_file1()},
    )
    names = [f["FunctionName"] for f in conn.list_functions()["Functions"]]
    names.should.contain(function_name)

    conn.publish_version(FunctionName=function_name, Description="v2")
    func_list = conn.list_functions()["Functions"]
    our_functions = [f for f in func_list if f["FunctionName"] == function_name]
    our_functions.should.have.length_of(1)

    # FunctionVersion=ALL means we should get a list of all versions
    full_list = conn.list_functions(FunctionVersion="ALL")["Functions"]
    our_functions = [f for f in full_list if f["FunctionName"] == function_name]
    our_functions.should.have.length_of(2)

    v1 = [f for f in our_functions if f["Version"] == "1"][0]
    v1["Description"].should.equal("v2")
    v1["FunctionArn"].should.equal(
        f"arn:aws:lambda:{_lambda_region}:{ACCOUNT_ID}:function:{function_name}:1"
    )

    latest = [f for f in our_functions if f["Version"] == "$LATEST"][0]
    latest["Description"].should.equal("")
    latest["FunctionArn"].should.equal(
        f"arn:aws:lambda:{_lambda_region}:{ACCOUNT_ID}:function:{function_name}:$LATEST"
    )


@mock_lambda
def test_create_based_on_s3_with_missing_bucket():
    conn = boto3.client("lambda", _lambda_region)
    function_name = str(uuid4())[0:6]

    conn.create_function.when.called_with(
        FunctionName=function_name,
        Runtime="python2.7",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"S3Bucket": "this-bucket-does-not-exist", "S3Key": "test.zip"},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
        VpcConfig={"SecurityGroupIds": ["sg-123abc"], "SubnetIds": ["subnet-123abc"]},
    ).should.throw(botocore.client.ClientError)


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

    result.should.have.key("FunctionName").equals(function_name)
    result.should.have.key("FunctionArn").equals(
        f"arn:aws:lambda:{_lambda_region}:{ACCOUNT_ID}:function:{function_name}"
    )
    result.should.have.key("Runtime").equals("python2.7")
    result.should.have.key("Handler").equals("lambda_function.lambda_handler")
    result.should.have.key("CodeSha256").equals(
        base64.b64encode(hashlib.sha256(zip_content).digest()).decode("utf-8")
    )
    result.should.have.key("State").equals("Active")


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

    result.should.equal(
        {
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
        }
    )


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
    result.should.have.key("TracingConfig").should.equal({"Mode": output})


@pytest.fixture(name="with_ecr_mock")
def ecr_repo_fixture():
    with mock_ecr():
        os.environ["MOTO_LAMBDA_STUB_ECR"] = "FALSE"
        repo_name = "testlambdaecr"
        ecr_client = ecr_client = boto3.client("ecr", "us-east-1")
        ecr_client.create_repository(repositoryName=repo_name)
        ecr_client.put_image(
            repositoryName=repo_name,
            imageManifest=json.dumps(_create_image_manifest()),
            imageTag="latest",
        )
        yield
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

    resp.should.have.key("FunctionName").equals(fn_name)
    resp.should.have.key("CodeSize").equals(0)
    resp.should.have.key("CodeSha256")
    resp.should.have.key("PackageType").equals("Image")

    result = lambda_client.get_function(FunctionName=fn_name)
    result.should.have.key("Configuration")
    config = result["Configuration"]
    result.should.have.key("Code")
    code = result["Code"]
    code.should.have.key("RepositoryType").equals("ECR")
    code.should.have.key("ImageUri").equals(image_uri)
    image_uri_without_tag = image_uri.split(":")[0]
    resolved_image_uri = f"{image_uri_without_tag}@sha256:{config['CodeSha256']}"
    code.should.have.key("ResolvedImageUri").equals(resolved_image_uri)


@mock_lambda
def test_create_function_from_mocked_ecr_image(
    with_ecr_mock,
):  # pylint: disable=unused-argument
    if settings.TEST_SERVER_MODE:
        raise SkipTest(
            "Envars not easily set in server mode, feature off by default, skipping..."
        )

    lambda_client = boto3.client("lambda", "us-east-1")
    fn_name = str(uuid4())[0:6]
    image_uri = f"{ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/testlambdaecr:latest"

    dic = {
        "FunctionName": fn_name,
        "Role": get_role_name(),
        "Code": {"ImageUri": image_uri},
        "PackageType": "Image",
        "Timeout": 100,
    }
    resp = lambda_client.create_function(**dic)

    resp.should.have.key("FunctionName").equals(fn_name)
    resp.should.have.key("CodeSize").greater_than(0)
    resp.should.have.key("CodeSha256")
    resp.should.have.key("PackageType").equals("Image")

    result = lambda_client.get_function(FunctionName=fn_name)
    result.should.have.key("Configuration")
    config = result["Configuration"]
    config.should.have.key("CodeSha256").equals(resp["CodeSha256"])
    config.should.have.key("CodeSize").equals(resp["CodeSize"])
    result.should.have.key("Code")
    code = result["Code"]
    code.should.have.key("RepositoryType").equals("ECR")
    code.should.have.key("ImageUri").equals(image_uri)
    image_uri_without_tag = image_uri.split(":")[0]
    resolved_image_uri = f"{image_uri_without_tag}@sha256:{config['CodeSha256']}"
    code.should.have.key("ResolvedImageUri").equals(resolved_image_uri)


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
    err["Code"].should.equal("ImageNotFoundException")
    err["Message"].should.equal(
        "The image with imageId {'imageTag': 'dne'} does not exist within the repository with name 'testlambdaecr' in the registry with id '123456789012'"
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

    result["Code"]["Location"].should.equal(
        f"s3://awslambda-{_lambda_region}-tasks.s3-{_lambda_region}.amazonaws.com/test.zip"
    )
    result["Code"]["RepositoryType"].should.equal("S3")

    result["Configuration"]["CodeSha256"].should.equal(
        base64.b64encode(hashlib.sha256(zip_content).digest()).decode("utf-8")
    )
    result["Configuration"]["CodeSize"].should.equal(len(zip_content))
    result["Configuration"]["Description"].should.equal("test lambda function")
    result["Configuration"].should.contain("FunctionArn")
    result["Configuration"]["FunctionName"].should.equal(function_name)
    result["Configuration"]["Handler"].should.equal("lambda_function.lambda_handler")
    result["Configuration"]["MemorySize"].should.equal(128)
    result["Configuration"]["Role"].should.equal(get_role_name())
    result["Configuration"]["Runtime"].should.equal("python2.7")
    result["Configuration"]["Timeout"].should.equal(3)
    result["Configuration"]["Version"].should.equal("$LATEST")
    result["Configuration"].should.contain("VpcConfig")
    result["Configuration"].should.contain("Environment")
    result["Configuration"]["Environment"].should.contain("Variables")
    result["Configuration"]["Environment"]["Variables"].should.equal(
        {"test_variable": "test_value"}
    )

    # Test get function with qualifier
    result = conn.get_function(FunctionName=function_name, Qualifier="$LATEST")
    result["Configuration"]["Version"].should.equal("$LATEST")
    result["Configuration"]["FunctionArn"].should.equal(
        f"arn:aws:lambda:us-west-2:{ACCOUNT_ID}:function:{function_name}:$LATEST"
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

    result["CodeSha256"].should.equal(
        base64.b64encode(hashlib.sha256(zip_content).digest()).decode("utf-8")
    )
    result["CodeSize"].should.equal(len(zip_content))
    result["Description"].should.equal("test lambda function")
    result.should.contain("FunctionArn")
    result["FunctionName"].should.equal(function_name)
    result["Handler"].should.equal("lambda_function.lambda_handler")
    result["MemorySize"].should.equal(128)
    result["Role"].should.equal(get_role_name())
    result["Runtime"].should.equal("python2.7")
    result["Timeout"].should.equal(3)
    result["Version"].should.equal("$LATEST")
    result.should.contain("VpcConfig")
    result.should.contain("Environment")
    result["Environment"].should.contain("Variables")
    result["Environment"]["Variables"].should.equal({"test_variable": "test_value"})

    # Test get function with qualifier
    result = conn.get_function_configuration(
        FunctionName=name_or_arn, Qualifier="$LATEST"
    )
    result["Version"].should.equal("$LATEST")
    result["FunctionArn"].should.equal(
        f"arn:aws:lambda:{_lambda_region}:{ACCOUNT_ID}:function:{function_name}:$LATEST"
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

    result["FunctionName"].should.equal(function_name)
    result["CodeSigningConfigArn"].should.equal("csc:arn")


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
    result["Configuration"]["FunctionName"].should.equal(function_name)


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

    success_result.should.equal({"ResponseMetadata": {"HTTPStatusCode": 204}})

    func_list = conn.list_functions()["Functions"]
    our_functions = [f for f in func_list if f["FunctionName"] == function_name]
    our_functions.should.have.length_of(0)


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
    our_functions.should.have.length_of(0)


@mock_lambda
def test_delete_unknown_function():
    conn = boto3.client("lambda", _lambda_region)
    conn.delete_function.when.called_with(
        FunctionName="testFunctionThatDoesntExist"
    ).should.throw(botocore.client.ClientError)


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
    err["Code"].should.equal("ResourceNotFoundException")
    err["Message"].should.equal(
        f"Function not found: arn:aws:lambda:eu-west-1:{ACCOUNT_ID}:function:bad_function_name"
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
    our_functions.should.have.length_of(1)
    latest_arn = our_functions[0]["FunctionArn"]

    res = conn.publish_version(FunctionName=function_name)
    assert res["ResponseMetadata"]["HTTPStatusCode"] == 201

    function_list = conn.list_functions(FunctionVersion="ALL")["Functions"]
    our_functions = [f for f in function_list if f["FunctionName"] == function_name]
    our_functions.should.have.length_of(2)

    # #SetComprehension ;-)
    published_arn = list({f["FunctionArn"] for f in our_functions} - {latest_arn})[0]
    published_arn.should.contain(f"{function_name}:1")

    conn.delete_function(FunctionName=function_name, Qualifier="1")

    function_list = conn.list_functions()["Functions"]
    our_functions = [f for f in function_list if f["FunctionName"] == function_name]
    our_functions.should.have.length_of(1)
    our_functions[0]["FunctionArn"].should.contain(function_name)


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
    initial_names.shouldnt.contain(function_name)

    function_name = function_name
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
        },
        "ResponseMetadata": {"HTTPStatusCode": 200},
    }
    functions = conn.list_functions()["Functions"]
    func_names = [f["FunctionName"] for f in functions]
    func_names.should.contain(function_name)

    func_arn = [
        f["FunctionArn"] for f in functions if f["FunctionName"] == function_name
    ][0]
    func_arn.should.equal(
        f"arn:aws:lambda:{_lambda_region}:{ACCOUNT_ID}:function:{function_name}"
    )
    functions = conn.list_functions(FunctionVersion="ALL")["Functions"]
    our_functions = [f for f in functions if f["FunctionName"] == function_name]
    our_functions.should.have.length_of(2)

    latest = [f for f in our_functions if f["Version"] == "$LATEST"][0]
    latest["FunctionArn"].should.equal(
        f"arn:aws:lambda:{_lambda_region}:{ACCOUNT_ID}:function:{function_name}:$LATEST"
    )
    latest.pop("FunctionArn")
    latest.pop("LastModified")
    latest.should.equal(expected_function_result["Configuration"])

    published = [f for f in our_functions if f["Version"] != "$LATEST"][0]
    published["Version"].should.equal("1")
    published["FunctionArn"].should.equal(
        f"arn:aws:lambda:{_lambda_region}:{ACCOUNT_ID}:function:{function_name}:1"
    )

    func = conn.get_function(FunctionName=function_name)

    func["Configuration"]["FunctionArn"].should.equal(
        f"arn:aws:lambda:{_lambda_region}:{ACCOUNT_ID}:function:{function_name}"
    )

    # this is hard to match against, so remove it
    func["ResponseMetadata"].pop("HTTPHeaders", None)
    # Botocore inserts retry attempts not seen in Python27
    func["ResponseMetadata"].pop("RetryAttempts", None)
    func["Configuration"].pop("LastModified")
    func["Configuration"].pop("FunctionArn")

    func.should.equal(expected_function_result)
    conn.delete_function(FunctionName=function_name)

    functions = conn.list_functions()["Functions"]
    func_names = [f["FunctionName"] for f in functions]
    func_names.shouldnt.contain(function_name)


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

    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    assert len(response["Code"]) == 2
    assert response["Code"]["RepositoryType"] == "S3"
    assert response["Code"]["Location"].startswith(
        f"s3://awslambda-{_lambda_region}-tasks.s3-{_lambda_region}.amazonaws.com"
    )
    response.should.have.key("Configuration")
    config = response["Configuration"]
    config.should.have.key("CodeSha256").equals(
        base64.b64encode(hashlib.sha256(zip_content).digest()).decode("utf-8")
    )
    config.should.have.key("CodeSize").equals(len(zip_content))
    config.should.have.key("Description").equals("test lambda function")
    config.should.have.key("FunctionArn").equals(
        f"arn:aws:lambda:{_lambda_region}:{ACCOUNT_ID}:function:{function_name}"
    )
    config.should.have.key("FunctionName").equals(function_name)
    config.should.have.key("Handler").equals("lambda_function.handler")
    config.should.have.key("MemorySize").equals(128)
    config.should.have.key("Role").equals(get_role_name())
    config.should.have.key("Runtime").equals("python2.7")
    config.should.have.key("Timeout").equals(3)
    config.should.have.key("Version").equals("$LATEST")
    config.should.have.key("State").equals("Active")
    config.should.have.key("Layers").equals([])
    config.should.have.key("LastUpdateStatus").equals("Successful")


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
    update1["CodeSha256"].shouldnt.equal(first_sha)

    response = conn.get_function(FunctionName=function_name, Qualifier="2")

    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    assert len(response["Code"]) == 2
    assert response["Code"]["RepositoryType"] == "S3"
    assert response["Code"]["Location"].startswith(
        f"s3://awslambda-{_lambda_region}-tasks.s3-{_lambda_region}.amazonaws.com"
    )

    config = response["Configuration"]
    config.should.have.key("CodeSize").equals(len(zip_content_two))
    config.should.have.key("Description").equals("test lambda function")
    config.should.have.key("FunctionArn").equals(
        f"arn:aws:lambda:{_lambda_region}:{ACCOUNT_ID}:function:{function_name}:2"
    )
    config.should.have.key("FunctionName").equals(function_name)
    config.should.have.key("Version").equals("2")
    config.should.have.key("LastUpdateStatus").equals("Successful")
    config.should.have.key("CodeSha256").equals(update1["CodeSha256"])

    most_recent_config = conn.get_function(FunctionName=function_name)
    most_recent_config["Configuration"]["CodeSha256"].should.equal(
        update1["CodeSha256"]
    )

    # Publishing this again, with the same code, gives us the same version
    same_update = conn.update_function_code(
        FunctionName=name_or_arn, ZipFile=zip_content_two, Publish=True
    )
    same_update["FunctionArn"].should.equal(
        most_recent_config["Configuration"]["FunctionArn"] + ":2"
    )
    same_update["Version"].should.equal("2")

    # Only when updating the code should we have a new version
    new_update = conn.update_function_code(
        FunctionName=name_or_arn, ZipFile=get_test_zip_file3(), Publish=True
    )
    new_update["FunctionArn"].should.equal(
        most_recent_config["Configuration"]["FunctionArn"] + ":3"
    )
    new_update["Version"].should.equal("3")


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

    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    assert len(response["Code"]) == 2
    assert response["Code"]["RepositoryType"] == "S3"
    assert response["Code"]["Location"].startswith(
        f"s3://awslambda-{_lambda_region}-tasks.s3-{_lambda_region}.amazonaws.com"
    )

    config = response["Configuration"]
    config.should.have.key("CodeSha256").equals(
        base64.b64encode(hashlib.sha256(zip_content_two).digest()).decode("utf-8")
    )
    config.should.have.key("CodeSize").equals(len(zip_content_two))
    config.should.have.key("Description").equals("test lambda function")
    config.should.have.key("FunctionArn").equals(
        f"arn:aws:lambda:{_lambda_region}:{ACCOUNT_ID}:function:{function_name}:2"
    )
    config.should.have.key("FunctionName").equals(function_name)
    config.should.have.key("Version").equals("2")
    config.should.have.key("LastUpdateStatus").equals("Successful")


@mock_lambda
def test_create_function_with_invalid_arn():
    err = create_invalid_lambda("test-iam-role")
    err.value.response["Error"]["Message"].should.equal(
        r"1 validation error detected: Value 'test-iam-role' at 'role' failed to satisfy constraint: Member must satisfy regular expression pattern: arn:(aws[a-zA-Z-]*)?:iam::(\d{12}):role/?[a-zA-Z_0-9+=,.@\-_/]+"
    )


@mock_lambda
def test_create_function_with_arn_from_different_account():
    err = create_invalid_lambda("arn:aws:iam::000000000000:role/example_role")
    err.value.response["Error"]["Message"].should.equal(
        "Cross-account pass role is not allowed."
    )


@mock_lambda
def test_create_function_with_unknown_arn():
    err = create_invalid_lambda(
        "arn:aws:iam::" + str(ACCOUNT_ID) + ":role/service-role/unknown_role"
    )
    err.value.response["Error"]["Message"].should.equal(
        "The role defined for the function cannot be assumed by Lambda."
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
    err["Code"].should.equal("ResourceNotFoundException")
    err["Message"].should.equal("No policy is associated with the given resource.")


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
    qualis.should.equal(["$LATEST", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"])

    client.delete_function(FunctionName=fn_name, Qualifier="4")
    client.delete_function(FunctionName=fn_name, Qualifier="5")

    resp = client.list_versions_by_function(FunctionName=fn_name)["Versions"]
    qualis = [fn["FunctionArn"].split(":")[-1] for fn in resp]
    qualis.should.equal(["$LATEST", "1", "2", "3", "6", "7", "8", "9", "10"])

    fn = client.get_function(FunctionName=fn_name, Qualifier="6")["Configuration"]
    fn["FunctionArn"].should.equal(
        f"arn:aws:lambda:us-east-1:{ACCOUNT_ID}:function:{fn_name}:6"
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
