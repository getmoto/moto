import datetime
import re
import string
import uuid

import boto3
import botocore.exceptions
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
from moto.ssm.models import PARAMETER_HISTORY_MAX_RESULTS, PARAMETER_VERSION_LIMIT
from tests import EXAMPLE_AMI_ID


@mock_aws
def test_delete_parameter():
    client = boto3.client("ssm", region_name="us-east-1")

    client.put_parameter(
        Name="test", Description="A test parameter", Value="value", Type="String"
    )

    response = client.get_parameters(Names=["test"])
    assert len(response["Parameters"]) == 1

    client.delete_parameter(Name="test")

    response = client.get_parameters(Names=["test"])
    assert len(response["Parameters"]) == 0


@mock_aws
def test_delete_nonexistent_parameter():
    client = boto3.client("ssm", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        client.delete_parameter(Name="test_noexist")
    assert ex.value.response["Error"]["Code"] == "ParameterNotFound"
    assert ex.value.response["Error"]["Message"] == "Parameter test_noexist not found."


@mock_aws
def test_delete_parameters():
    client = boto3.client("ssm", region_name="us-east-1")

    client.put_parameter(
        Name="test", Description="A test parameter", Value="value", Type="String"
    )

    response = client.get_parameters(Names=["test"])
    assert len(response["Parameters"]) == 1

    result = client.delete_parameters(Names=["test", "invalid"])
    assert len(result["DeletedParameters"]) == 1
    assert len(result["InvalidParameters"]) == 1

    response = client.get_parameters(Names=["test"])
    assert len(response["Parameters"]) == 0


@mock_aws
def test_get_parameters_by_path():
    client = boto3.client("ssm", region_name="us-east-1")

    client.put_parameter(Name="/foo/name1", Value="value1", Type="String")

    client.put_parameter(Name="/foo/name2", Value="value2", Type="String")

    client.put_parameter(Name="/bar/name3", Value="value3", Type="String")

    client.put_parameter(
        Name="/bar/name3/name4",
        Value="value4",
        Type="String",
    )

    client.put_parameter(
        Name="/baz/name1",
        Description="A test parameter (list)",
        Value="value1,value2,value3",
        Type="StringList",
    )

    client.put_parameter(Name="/baz/name2", Value="value1", Type="String")

    client.put_parameter(
        Name="/baz/pwd",
        Description="A secure test parameter",
        Value="my_secret",
        Type="SecureString",
        KeyId="alias/aws/ssm",
    )

    client.put_parameter(Name="foo", Value="bar", Type="String")

    client.put_parameter(Name="baz", Value="qux", Type="String")

    response = client.get_parameters_by_path(Path="/", Recursive=False)
    assert len(response["Parameters"]) == 2
    assert {p["Value"] for p in response["Parameters"]} == set(["bar", "qux"])
    assert {p["ARN"] for p in response["Parameters"]} == set(
        [
            f"arn:aws:ssm:us-east-1:{ACCOUNT_ID}:parameter/foo",
            f"arn:aws:ssm:us-east-1:{ACCOUNT_ID}:parameter/baz",
        ]
    )
    for p in response["Parameters"]:
        assert isinstance(p["LastModifiedDate"], datetime.datetime)

    response = client.get_parameters_by_path(Path="/", Recursive=True)
    assert len(response["Parameters"]) == 9

    response = client.get_parameters_by_path(Path="/foo")
    assert len(response["Parameters"]) == 2
    assert {p["Value"] for p in response["Parameters"]} == set(["value1", "value2"])

    response = client.get_parameters_by_path(Path="/bar", Recursive=False)
    assert len(response["Parameters"]) == 1
    assert response["Parameters"][0]["Value"] == "value3"

    response = client.get_parameters_by_path(Path="/bar", Recursive=True)
    assert len(response["Parameters"]) == 2
    assert {p["Value"] for p in response["Parameters"]} == set(["value3", "value4"])

    response = client.get_parameters_by_path(Path="/baz")
    assert len(response["Parameters"]) == 3

    filters = [{"Key": "Type", "Option": "Equals", "Values": ["StringList"]}]
    response = client.get_parameters_by_path(Path="/baz", ParameterFilters=filters)
    assert len(response["Parameters"]) == 1
    assert {p["Name"] for p in response["Parameters"]} == set(["/baz/name1"])

    # note: 'Option' is optional (default: 'Equals')
    filters = [{"Key": "Type", "Values": ["StringList"]}]
    response = client.get_parameters_by_path(Path="/baz", ParameterFilters=filters)
    assert len(response["Parameters"]) == 1
    assert {p["Name"] for p in response["Parameters"]} == set(["/baz/name1"])

    filters = [{"Key": "Type", "Option": "Equals", "Values": ["String"]}]
    response = client.get_parameters_by_path(Path="/baz", ParameterFilters=filters)
    assert len(response["Parameters"]) == 1
    assert {p["Name"] for p in response["Parameters"]} == set(["/baz/name2"])

    filters = [
        {"Key": "Type", "Option": "Equals", "Values": ["String", "SecureString"]}
    ]
    response = client.get_parameters_by_path(Path="/baz", ParameterFilters=filters)
    assert len(response["Parameters"]) == 2
    assert {p["Name"] for p in response["Parameters"]} == set(
        ["/baz/name2", "/baz/pwd"]
    )

    filters = [{"Key": "Type", "Option": "BeginsWith", "Values": ["String"]}]
    response = client.get_parameters_by_path(Path="/baz", ParameterFilters=filters)
    assert len(response["Parameters"]) == 2
    assert {p["Name"] for p in response["Parameters"]} == set(
        ["/baz/name1", "/baz/name2"]
    )

    filters = [{"Key": "KeyId", "Option": "Equals", "Values": ["alias/aws/ssm"]}]
    response = client.get_parameters_by_path(Path="/baz", ParameterFilters=filters)
    assert len(response["Parameters"]) == 1
    assert {p["Name"] for p in response["Parameters"]} == set(["/baz/pwd"])

    response = client.get_parameters_by_path(Path="/", Recursive=True, MaxResults=4)
    assert len(response["Parameters"]) == 4
    assert response["NextToken"] == "4"
    response = client.get_parameters_by_path(
        Path="/", Recursive=True, MaxResults=4, NextToken=response["NextToken"]
    )
    assert len(response["Parameters"]) == 4
    assert response["NextToken"] == "8"
    response = client.get_parameters_by_path(
        Path="/", Recursive=True, MaxResults=4, NextToken=response["NextToken"]
    )
    assert len(response["Parameters"]) == 1
    assert "NextToken" not in response

    filters = [{"Key": "Name", "Values": ["error"]}]
    with pytest.raises(ClientError) as client_err:
        client.get_parameters_by_path(Path="/baz", ParameterFilters=filters)
    assert client_err.value.response["Error"]["Message"] == (
        "The following filter key is not valid: Name. "
        "Valid filter keys include: [Type, KeyId]."
    )

    filters = [{"Key": "Path", "Values": ["/error"]}]
    with pytest.raises(ClientError) as client_err:
        client.get_parameters_by_path(Path="/baz", ParameterFilters=filters)
    assert client_err.value.response["Error"]["Message"] == (
        "The following filter key is not valid: Path. "
        "Valid filter keys include: [Type, KeyId]."
    )

    filters = [{"Key": "Tier", "Values": ["Standard"]}]
    with pytest.raises(ClientError) as client_err:
        client.get_parameters_by_path(Path="/baz", ParameterFilters=filters)
    assert client_err.value.response["Error"]["Message"] == (
        "The following filter key is not valid: Tier. "
        "Valid filter keys include: [Type, KeyId]."
    )

    # Label filter in get_parameters_by_path
    client.label_parameter_version(Name="/foo/name2", Labels=["Label1"])

    filters = [{"Key": "Label", "Values": ["Label1"]}]
    response = client.get_parameters_by_path(Path="/foo", ParameterFilters=filters)
    assert len(response["Parameters"]) == 1
    assert {p["Name"] for p in response["Parameters"]} == set(["/foo/name2"])


@pytest.mark.parametrize("name", ["test", "my-cool-parameter"])
@mock_aws
def test_put_parameter(name):
    client = boto3.client("ssm", region_name="us-east-1")
    response = client.put_parameter(
        Name=name, Description="A test parameter", Value="value", Type="String"
    )

    assert response["Version"] == 1

    response = client.get_parameters(Names=[name], WithDecryption=False)

    assert len(response["Parameters"]) == 1
    assert response["Parameters"][0]["Name"] == name
    assert response["Parameters"][0]["Value"] == "value"
    assert response["Parameters"][0]["Type"] == "String"
    assert response["Parameters"][0]["Version"] == 1
    assert response["Parameters"][0]["DataType"] == "text"
    assert isinstance(response["Parameters"][0]["LastModifiedDate"], datetime.datetime)
    assert response["Parameters"][0]["ARN"] == (
        f"arn:aws:ssm:us-east-1:{ACCOUNT_ID}:parameter/{name}"
    )
    initial_modification_date = response["Parameters"][0]["LastModifiedDate"]

    try:
        client.put_parameter(
            Name=name, Description="desc 2", Value="value 2", Type="String"
        )
        raise RuntimeError("Should fail")
    except botocore.exceptions.ClientError as err:
        assert err.operation_name == "PutParameter"
        assert err.response["Error"]["Message"] == (
            "The parameter already exists. To overwrite this value, set the "
            "overwrite option in the request to true."
        )

    response = client.get_parameters(Names=[name], WithDecryption=False)

    # without overwrite nothing change
    assert len(response["Parameters"]) == 1
    assert response["Parameters"][0]["Name"] == name
    assert response["Parameters"][0]["Value"] == "value"
    assert response["Parameters"][0]["Type"] == "String"
    assert response["Parameters"][0]["Version"] == 1
    assert response["Parameters"][0]["DataType"] == "text"
    assert response["Parameters"][0]["LastModifiedDate"] == initial_modification_date
    assert response["Parameters"][0]["ARN"] == (
        f"arn:aws:ssm:us-east-1:{ACCOUNT_ID}:parameter/{name}"
    )
    new_data_type = "aws:ec2:image"

    # Cannot have tags and overwrite at the same time
    with pytest.raises(ClientError) as ex:
        response = client.put_parameter(
            Name=name,
            Description="desc 3",
            Value="value 3",
            Type="String",
            Overwrite=True,
            Tags=[{"Key": "foo", "Value": "bar"}],
            DataType=new_data_type,
        )
    assert ex.value.response["Error"]["Code"] == "ValidationException"

    response = client.put_parameter(
        Name=name,
        Description="desc 3",
        Value="value 3",
        Type="String",
        Overwrite=True,
        DataType=new_data_type,
    )

    assert response["Version"] == 2

    response = client.get_parameters(Names=[name], WithDecryption=False)

    # without overwrite nothing change
    assert len(response["Parameters"]) == 1
    assert response["Parameters"][0]["Name"] == name
    assert response["Parameters"][0]["Value"] == "value 3"
    assert response["Parameters"][0]["Type"] == "String"
    assert response["Parameters"][0]["Version"] == 2
    assert response["Parameters"][0]["DataType"] != "text"
    assert response["Parameters"][0]["DataType"] == new_data_type
    assert response["Parameters"][0]["LastModifiedDate"] != initial_modification_date
    assert response["Parameters"][0]["ARN"] == (
        f"arn:aws:ssm:us-east-1:{ACCOUNT_ID}:parameter/{name}"
    )


@pytest.mark.parametrize("name", ["test", "my-cool-parameter"])
@mock_aws
def test_put_parameter_overwrite_preserves_metadata(name):
    test_tag_key = "TestKey"
    test_tag_value = "TestValue"
    test_description = "A test parameter"
    test_pattern = ".*"
    test_key_id = "someKeyId"
    client = boto3.client("ssm", region_name="us-east-1")
    response = client.put_parameter(
        Name=name,
        Description=test_description,
        Value="value",
        Type="String",
        Tags=[{"Key": test_tag_key, "Value": test_tag_value}],
        AllowedPattern=test_pattern,
        KeyId=test_key_id,
        Tier="Standard",
        Policies='["Expiration"]',
    )

    assert response["Version"] == 1

    response = client.get_parameters(Names=[name], WithDecryption=False)

    assert len(response["Parameters"]) == 1
    assert response["Parameters"][0]["Name"] == name
    assert response["Parameters"][0]["Value"] == "value"
    assert response["Parameters"][0]["Type"] == "String"
    assert response["Parameters"][0]["Version"] == 1
    assert response["Parameters"][0]["DataType"] == "text"
    assert isinstance(response["Parameters"][0]["LastModifiedDate"], datetime.datetime)
    assert response["Parameters"][0]["ARN"] == (
        f"arn:aws:ssm:us-east-1:{ACCOUNT_ID}:parameter/{name}"
    )
    initial_modification_date = response["Parameters"][0]["LastModifiedDate"]

    # Verify that the tag got set
    response = client.list_tags_for_resource(ResourceType="Parameter", ResourceId=name)

    assert len(response["TagList"]) == 1
    assert response["TagList"][0]["Key"] == test_tag_key
    assert response["TagList"][0]["Value"] == test_tag_value

    # Verify description is set
    response = client.describe_parameters(
        ParameterFilters=[
            {
                "Key": "Name",
                "Option": "Equals",
                "Values": [name],
            },
        ]
    )
    assert len(response["Parameters"]) == 1
    assert response["Parameters"][0]["Description"] == test_description
    assert response["Parameters"][0]["AllowedPattern"] == test_pattern
    assert response["Parameters"][0]["KeyId"] == test_key_id

    # Overwrite just the value
    response = client.put_parameter(Name=name, Value="value 2", Overwrite=True)

    assert response["Version"] == 2

    response = client.get_parameters(Names=[name], WithDecryption=False)

    assert len(response["Parameters"]) == 1
    assert response["Parameters"][0]["Name"] == name
    assert response["Parameters"][0]["Value"] == "value 2"
    assert response["Parameters"][0]["Type"] == "String"
    assert response["Parameters"][0]["Version"] == 2
    assert response["Parameters"][0]["DataType"] == "text"
    assert response["Parameters"][0]["LastModifiedDate"] != initial_modification_date
    assert response["Parameters"][0]["ARN"] == (
        f"arn:aws:ssm:us-east-1:{ACCOUNT_ID}:parameter/{name}"
    )

    # Verify that tags are unchanged
    response = client.list_tags_for_resource(ResourceType="Parameter", ResourceId=name)

    assert len(response["TagList"]) == 1
    assert response["TagList"][0]["Key"] == test_tag_key
    assert response["TagList"][0]["Value"] == test_tag_value

    # Verify description/tier/policies is unchanged
    response = client.describe_parameters(
        ParameterFilters=[{"Key": "Name", "Option": "Equals", "Values": [name]}]
    )
    assert len(response["Parameters"]) == 1
    assert response["Parameters"][0]["Description"] == test_description
    assert response["Parameters"][0]["AllowedPattern"] == test_pattern
    assert response["Parameters"][0]["KeyId"] == test_key_id
    assert response["Parameters"][0]["Tier"] == "Standard"
    assert response["Parameters"][0]["Policies"] == [
        {
            "PolicyStatus": "Finished",
            "PolicyText": "Expiration",
            "PolicyType": "Expiration",
        }
    ]


@mock_aws
def test_put_parameter_with_invalid_policy():
    name = "some_param"
    test_description = "A test parameter"
    client = boto3.client("ssm", region_name="us-east-1")
    client.put_parameter(
        Name=name,
        Description=test_description,
        Value="value",
        Type="String",
        Policies="invalid json",
    )

    # Verify that an invalid policy does not break anything
    param = client.describe_parameters(
        ParameterFilters=[{"Key": "Name", "Option": "Equals", "Values": [name]}]
    )["Parameters"][0]
    assert "Policies" not in param


@mock_aws
def test_put_parameter_empty_string_value():
    client = boto3.client("ssm", region_name="us-east-1")
    with pytest.raises(ClientError) as e:
        client.put_parameter(Name="test_name", Value="", Type="String")
    ex = e.value
    assert ex.operation_name == "PutParameter"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "ValidationException" in ex.response["Error"]["Code"]
    assert ex.response["Error"]["Message"] == (
        "1 validation error detected: "
        "Value '' at 'value' failed to satisfy constraint: "
        "Member must have length greater than or equal to 1."
    )


@mock_aws
def test_put_parameter_invalid_names():
    client = boto3.client("ssm", region_name="us-east-1")

    invalid_prefix_err = (
        'Parameter name: can\'t be prefixed with "aws" or "ssm" (case-insensitive).'
    )

    with pytest.raises(ClientError) as client_err:
        client.put_parameter(Name="ssm_test", Value="value", Type="String")
    assert client_err.value.response["Error"]["Message"] == invalid_prefix_err

    with pytest.raises(ClientError) as client_err:
        client.put_parameter(Name="SSM_TEST", Value="value", Type="String")
    assert client_err.value.response["Error"]["Message"] == invalid_prefix_err

    with pytest.raises(ClientError) as client_err:
        client.put_parameter(Name="aws_test", Value="value", Type="String")
    assert client_err.value.response["Error"]["Message"] == invalid_prefix_err

    with pytest.raises(ClientError) as client_err:
        client.put_parameter(Name="AWS_TEST", Value="value", Type="String")
    assert client_err.value.response["Error"]["Message"] == invalid_prefix_err

    ssm_path = "/ssm_test/path/to/var"
    with pytest.raises(ClientError) as client_err:
        client.put_parameter(Name=ssm_path, Value="value", Type="String")
    assert client_err.value.response["Error"]["Message"] == (
        'Parameter name: can\'t be prefixed with "ssm" (case-insensitive). '
        "If formed as a path, it can consist of sub-paths divided by slash "
        "symbol; each sub-path can be formed as a mix of letters, numbers "
        "and the following 3 symbols .-_"
    )

    ssm_path = "/SSM/PATH/TO/VAR"
    with pytest.raises(ClientError) as client_err:
        client.put_parameter(Name=ssm_path, Value="value", Type="String")
    assert client_err.value.response["Error"]["Message"] == (
        'Parameter name: can\'t be prefixed with "ssm" (case-insensitive). '
        "If formed as a path, it can consist of sub-paths divided by slash "
        "symbol; each sub-path can be formed as a mix of letters, numbers "
        "and the following 3 symbols .-_"
    )

    aws_path = "/aws_test/path/to/var"
    with pytest.raises(ClientError) as client_err:
        client.put_parameter(Name=aws_path, Value="value", Type="String")
    assert client_err.value.response["Error"]["Message"] == (
        f"No access to reserved parameter name: {aws_path}."
    )

    aws_path = "/AWS/PATH/TO/VAR"
    with pytest.raises(ClientError) as client_err:
        client.put_parameter(Name=aws_path, Value="value", Type="String")
    assert client_err.value.response["Error"]["Message"] == (
        f"No access to reserved parameter name: {aws_path}."
    )


@mock_aws
def test_put_parameter_china():
    client = boto3.client("ssm", region_name="cn-north-1")

    response = client.put_parameter(
        Name="test", Description="A test parameter", Value="value", Type="String"
    )

    assert response["Version"] == 1


@mock_aws
@pytest.mark.parametrize("bad_data_type", ["not_text", "not_ec2", "something weird"])
def test_put_parameter_invalid_data_type(bad_data_type):
    client = boto3.client("ssm", region_name="us-east-1")
    with pytest.raises(ClientError) as e:
        client.put_parameter(
            Name="test_name", Value="some_value", Type="String", DataType=bad_data_type
        )
    ex = e.value
    assert ex.operation_name == "PutParameter"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "ValidationException" in ex.response["Error"]["Code"]
    assert ex.response["Error"]["Message"] == (
        f"The following data type is not supported: {bad_data_type}"
        " (Data type names are all lowercase.)"
    )


@mock_aws
def test_put_parameter_invalid_type():
    client = boto3.client("ssm", region_name="us-east-1")
    bad_type = "str"  # correct value is String
    with pytest.raises(ClientError) as e:
        client.put_parameter(
            Name="test_name", Value="some_value", Type=bad_type, DataType="text"
        )
    ex = e.value
    assert ex.operation_name == "PutParameter"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "ValidationException" in ex.response["Error"]["Code"]
    assert ex.response["Error"]["Message"] == (
        f"1 validation error detected: Value '{bad_type}' at 'type' "
        "failed to satisfy constraint: Member must satisfy enum value set: "
        "[SecureString, StringList, String]"
    )


@mock_aws
def test_put_parameter_no_type():
    client = boto3.client("ssm", "us-east-1")
    with pytest.raises(ClientError) as e:
        client.put_parameter(
            Name="test_name",
            Value="some_value",
        )
    ex = e.value
    assert ex.operation_name == "PutParameter"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert ex.response["Error"]["Code"] == "ValidationException"
    assert (
        ex.response["Error"]["Message"]
        == "A parameter type is required when you create a parameter."
    )

    # Ensure backend state is consistent
    assert client.describe_parameters()


@mock_aws
def test_update_parameter():
    # Setup
    client = boto3.client("ssm", "us-east-1")
    param_name = "test_param"
    param_type = "String"
    updated_value = "UpdatedValue"
    client.put_parameter(
        Description="Description",
        Name=param_name,
        Type=param_type,
        Value="Value",
    )

    # Execute
    response = client.put_parameter(
        Name=param_name,
        Overwrite=True,
        Value=updated_value,
    )
    new_param = client.get_parameter(Name=param_name)

    # Verify
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert new_param["Parameter"]["Type"] == param_type
    assert new_param["Parameter"]["Value"] == updated_value


@mock_aws
def test_update_parameter_already_exists_error():
    # Setup
    client = boto3.client("ssm", "us-east-1")
    client.put_parameter(
        Description="Description",
        Name="Name",
        Type="String",
        Value="Value",
    )

    # Execute
    with pytest.raises(ClientError) as exc:
        client.put_parameter(
            Name="Name",
            Value="UpdatedValue",
        )

    # Verify
    ex = exc.value
    assert ex.operation_name == "PutParameter"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert ex.response["Error"]["Code"] == "ParameterAlreadyExists"
    assert ex.response["Error"]["Message"] == (
        "The parameter already exists. To overwrite this value, set the "
        "overwrite option in the request to true."
    )


@mock_aws
def test_get_parameter():
    client = boto3.client("ssm", region_name="us-east-1")

    client.put_parameter(
        Name="test", Description="A test parameter", Value="value", Type="String"
    )

    response = client.get_parameter(Name="test", WithDecryption=False)

    assert response["Parameter"]["Name"] == "test"
    assert response["Parameter"]["Value"] == "value"
    assert response["Parameter"]["Type"] == "String"
    assert response["Parameter"]["DataType"] == "text"
    assert isinstance(response["Parameter"]["LastModifiedDate"], datetime.datetime)
    assert response["Parameter"]["ARN"] == (
        f"arn:aws:ssm:us-east-1:{ACCOUNT_ID}:parameter/test"
    )


@mock_aws
def test_get_parameter_with_version_and_labels():
    client = boto3.client("ssm", region_name="us-east-1")

    client.put_parameter(
        Name="test-1", Description="A test parameter", Value="value", Type="String"
    )
    client.put_parameter(
        Name="test-2", Description="A test parameter", Value="value", Type="String"
    )

    client.label_parameter_version(
        Name="test-2", ParameterVersion=1, Labels=["test-label"]
    )

    response = client.get_parameter(Name="test-1:1", WithDecryption=False)

    assert response["Parameter"]["Name"] == "test-1"
    assert response["Parameter"]["Value"] == "value"
    assert response["Parameter"]["Type"] == "String"
    assert response["Parameter"]["DataType"] == "text"
    assert isinstance(response["Parameter"]["LastModifiedDate"], datetime.datetime)
    assert response["Parameter"]["ARN"] == (
        f"arn:aws:ssm:us-east-1:{ACCOUNT_ID}:parameter/test-1"
    )

    response = client.get_parameter(Name="test-2:1", WithDecryption=False)
    assert response["Parameter"]["Name"] == "test-2"
    assert response["Parameter"]["Value"] == "value"
    assert response["Parameter"]["Type"] == "String"
    assert response["Parameter"]["DataType"] == "text"
    assert isinstance(response["Parameter"]["LastModifiedDate"], datetime.datetime)
    assert response["Parameter"]["ARN"] == (
        f"arn:aws:ssm:us-east-1:{ACCOUNT_ID}:parameter/test-2"
    )

    response = client.get_parameter(Name="test-2:test-label", WithDecryption=False)
    assert response["Parameter"]["Name"] == "test-2"
    assert response["Parameter"]["Value"] == "value"
    assert response["Parameter"]["Type"] == "String"
    assert response["Parameter"]["DataType"] == "text"
    assert isinstance(response["Parameter"]["LastModifiedDate"], datetime.datetime)
    assert response["Parameter"]["ARN"] == (
        f"arn:aws:ssm:us-east-1:{ACCOUNT_ID}:parameter/test-2"
    )

    with pytest.raises(ClientError) as ex:
        client.get_parameter(Name="test-2:2:3", WithDecryption=False)
    assert ex.value.response["Error"]["Code"] == "ParameterNotFound"
    assert ex.value.response["Error"]["Message"] == ("Parameter test-2:2:3 not found.")

    with pytest.raises(ClientError) as ex:
        client.get_parameter(Name="test-2:2", WithDecryption=False)
    assert ex.value.response["Error"]["Code"] == "ParameterVersionNotFound"
    assert ex.value.response["Error"]["Message"] == (
        "Systems Manager could not find version 2 of test-2. Verify the version and try again."
    )

    with pytest.raises(ClientError) as ex:
        client.get_parameter(Name="test-3:2", WithDecryption=False)
    assert ex.value.response["Error"]["Code"] == "ParameterNotFound"
    assert ex.value.response["Error"]["Message"] == "Parameter test-3:2 not found."


@mock_aws
def test_get_parameters_errors():
    client = boto3.client("ssm", region_name="us-east-1")

    ssm_parameters = {name: "value" for name in string.ascii_lowercase[:11]}

    for name, value in ssm_parameters.items():
        client.put_parameter(Name=name, Value=value, Type="String")

    with pytest.raises(ClientError) as e:
        client.get_parameters(Names=list(ssm_parameters.keys()))
    ex = e.value
    assert ex.operation_name == "GetParameters"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "ValidationException" in ex.response["Error"]["Code"]
    all_keys = ", ".join(ssm_parameters.keys())
    assert ex.response["Error"]["Message"] == (
        "1 validation error detected: "
        f"Value '[{all_keys}]' at 'names' failed to satisfy constraint: "
        "Member must have length less than or equal to 10."
    )


@mock_aws
def test_get_nonexistant_parameter():
    client = boto3.client("ssm", region_name="us-east-1")

    try:
        client.get_parameter(Name="test_noexist", WithDecryption=False)
        raise RuntimeError("Should have failed")
    except botocore.exceptions.ClientError as err:
        assert err.operation_name == "GetParameter"
        assert err.response["Error"]["Message"] == "Parameter test_noexist not found."


@mock_aws
def test_describe_parameters():
    client = boto3.client("ssm", region_name="us-east-1")

    client.put_parameter(
        Name="test",
        Description="A test parameter",
        Value="value",
        Type="String",
        AllowedPattern=r".*",
    )

    response = client.describe_parameters()

    parameters = response["Parameters"]
    assert len(parameters) == 1
    assert parameters[0]["Name"] == "test"
    assert parameters[0]["Type"] == "String"
    assert parameters[0]["DataType"] == "text"
    assert parameters[0]["AllowedPattern"] == r".*"


@mock_aws
def test_describe_parameters_paging():
    client = boto3.client("ssm", region_name="us-east-1")

    for i in range(50):
        client.put_parameter(Name=f"param-{i}", Value=f"value-{i}", Type="String")

    response = client.describe_parameters()
    assert len(response["Parameters"]) == 10
    assert response["NextToken"] == "10"

    response = client.describe_parameters(NextToken=response["NextToken"])
    assert len(response["Parameters"]) == 10
    assert response["NextToken"] == "20"

    response = client.describe_parameters(NextToken=response["NextToken"])
    assert len(response["Parameters"]) == 10
    assert response["NextToken"] == "30"

    response = client.describe_parameters(NextToken=response["NextToken"])
    assert len(response["Parameters"]) == 10
    assert response["NextToken"] == "40"

    response = client.describe_parameters(NextToken=response["NextToken"])
    assert len(response["Parameters"]) == 10
    assert response["NextToken"] == "50"

    response = client.describe_parameters(NextToken=response["NextToken"])
    assert len(response["Parameters"]) == 0
    assert "NextToken" not in response


@mock_aws
def test_describe_parameters_filter_names():
    client = boto3.client("ssm", region_name="us-east-1")

    for i in range(50):
        p = {"Name": f"param-{i}", "Value": f"value-{i}", "Type": "String"}
        if i % 5 == 0:
            p["Type"] = "SecureString"
            p["KeyId"] = "a key"
        client.put_parameter(**p)

    response = client.describe_parameters(
        Filters=[{"Key": "Name", "Values": ["param-22"]}]
    )

    parameters = response["Parameters"]
    assert len(parameters) == 1
    assert parameters[0]["Name"] == "param-22"
    assert parameters[0]["Type"] == "String"
    assert "NextToken" not in response


@mock_aws
def test_describe_parameters_filter_type():
    client = boto3.client("ssm", region_name="us-east-1")

    for i in range(50):
        p = {"Name": f"param-{i}", "Value": f"value-{i}", "Type": "String"}
        if i % 5 == 0:
            p["Type"] = "SecureString"
            p["KeyId"] = "a key"
        client.put_parameter(**p)

    response = client.describe_parameters(
        Filters=[{"Key": "Type", "Values": ["SecureString"]}]
    )

    parameters = response["Parameters"]
    assert len(parameters) == 10
    assert parameters[0]["Type"] == "SecureString"
    assert response["NextToken"] == "10"


@mock_aws
def test_describe_parameters_filter_keyid():
    client = boto3.client("ssm", region_name="us-east-1")

    for i in range(50):
        p = {"Name": f"param-{i}", "Value": f"value-{i}", "Type": "String"}
        if i % 5 == 0:
            p["Type"] = "SecureString"
            p["KeyId"] = f"key:{i}"
        client.put_parameter(**p)

    response = client.describe_parameters(
        Filters=[{"Key": "KeyId", "Values": ["key:10"]}]
    )

    parameters = response["Parameters"]
    assert len(parameters) == 1
    assert parameters[0]["Name"] == "param-10"
    assert parameters[0]["Type"] == "SecureString"
    assert "NextToken" not in response


@mock_aws
def test_describe_parameters_with_parameter_filters_keyid():
    client = boto3.client("ssm", region_name="us-east-1")
    client.put_parameter(Name="secure-param", Value="secure-value", Type="SecureString")
    client.put_parameter(
        Name="custom-secure-param",
        Value="custom-secure-value",
        Type="SecureString",
        KeyId="alias/custom",
    )
    client.put_parameter(Name="param", Value="value", Type="String")

    response = client.describe_parameters(
        ParameterFilters=[{"Key": "KeyId", "Values": ["alias/aws/ssm"]}]
    )

    parameters = response["Parameters"]
    assert len(parameters) == 1
    assert parameters[0]["Name"] == "secure-param"
    assert parameters[0]["Type"] == "SecureString"
    assert "NextToken" not in response

    response = client.describe_parameters(
        ParameterFilters=[{"Key": "KeyId", "Values": ["alias/custom"]}]
    )

    parameters = response["Parameters"]
    assert len(parameters) == 1
    assert parameters[0]["Name"] == "custom-secure-param"
    assert parameters[0]["Type"] == "SecureString"
    assert "NextToken" not in response

    response = client.describe_parameters(
        ParameterFilters=[{"Key": "KeyId", "Option": "BeginsWith", "Values": ["alias"]}]
    )

    parameters = response["Parameters"]
    assert len(parameters) == 2
    assert "NextToken" not in response


@mock_aws
def test_describe_parameters_with_parameter_filters_name():
    client = boto3.client("ssm", region_name="us-east-1")
    client.put_parameter(Name="param", Value="value", Type="String")
    client.put_parameter(Name="/param-2", Value="value-2", Type="String")
    client.put_parameter(Name="/tangent-3", Value="value-3", Type="String")
    client.put_parameter(Name="tangram-4", Value="value-4", Type="String")
    client.put_parameter(Name="standby-5", Value="value-5", Type="String")

    response = client.describe_parameters(
        ParameterFilters=[{"Key": "Name", "Values": ["param"]}]
    )

    parameters = response["Parameters"]
    assert len(parameters) == 1
    assert parameters[0]["Name"] == "param"
    assert parameters[0]["Type"] == "String"
    assert "NextToken" not in response

    response = client.describe_parameters(
        ParameterFilters=[{"Key": "Name", "Values": ["/param"]}]
    )

    parameters = response["Parameters"]
    assert len(parameters) == 1
    assert parameters[0]["Name"] == "param"
    assert parameters[0]["Type"] == "String"
    assert "NextToken" not in response

    response = client.describe_parameters(
        ParameterFilters=[{"Key": "Name", "Values": ["param-2"]}]
    )

    parameters = response["Parameters"]
    assert len(parameters) == 1
    assert parameters[0]["Name"] == "/param-2"
    assert parameters[0]["Type"] == "String"
    assert "NextToken" not in response

    response = client.describe_parameters(
        ParameterFilters=[{"Key": "Name", "Option": "BeginsWith", "Values": ["param"]}]
    )

    parameters = response["Parameters"]
    assert len(parameters) == 2
    assert "NextToken" not in response

    response = client.describe_parameters(
        ParameterFilters=[{"Key": "Name", "Option": "Contains", "Values": ["ram"]}]
    )

    parameters = response["Parameters"]
    assert len(parameters) == 3
    assert "NextToken" not in response

    response = client.describe_parameters(
        ParameterFilters=[{"Key": "Name", "Option": "Contains", "Values": ["/tan"]}]
    )

    parameters = response["Parameters"]
    assert len(parameters) == 2
    assert "NextToken" not in response


@mock_aws
def test_describe_parameters_with_parameter_filters_path():
    client = boto3.client("ssm", region_name="us-east-1")
    client.put_parameter(Name="/foo/name1", Value="value1", Type="String")

    client.put_parameter(Name="/foo/name2", Value="value2", Type="String")

    client.put_parameter(Name="/bar/name3", Value="value3", Type="String")

    client.put_parameter(Name="/bar/name3/name4", Value="value4", Type="String")

    client.put_parameter(Name="foo", Value="bar", Type="String")

    response = client.describe_parameters(
        ParameterFilters=[{"Key": "Path", "Values": ["/fo"]}]
    )

    parameters = response["Parameters"]
    assert len(parameters) == 0
    assert "NextToken" not in response

    response = client.describe_parameters(
        ParameterFilters=[{"Key": "Path", "Values": ["/"]}]
    )

    parameters = response["Parameters"]
    assert len(parameters) == 1
    assert parameters[0]["Name"] == "foo"
    assert parameters[0]["Type"] == "String"
    assert "NextToken" not in response

    response = client.describe_parameters(
        ParameterFilters=[{"Key": "Path", "Values": ["/", "/foo"]}]
    )

    parameters = response["Parameters"]
    assert len(parameters) == 3
    assert {parameter["Name"] for parameter in response["Parameters"]} == {
        "/foo/name1",
        "/foo/name2",
        "foo",
    }
    assert "NextToken" not in response

    response = client.describe_parameters(
        ParameterFilters=[{"Key": "Path", "Values": ["/foo/"]}]
    )

    parameters = response["Parameters"]
    assert len(parameters) == 2
    assert {parameter["Name"] for parameter in response["Parameters"]} == {
        "/foo/name1",
        "/foo/name2",
    }
    assert "NextToken" not in response

    response = client.describe_parameters(
        ParameterFilters=[
            {"Key": "Path", "Option": "OneLevel", "Values": ["/bar/name3"]}
        ]
    )

    parameters = response["Parameters"]
    assert len(parameters) == 1
    assert parameters[0]["Name"] == "/bar/name3/name4"
    assert parameters[0]["Type"] == "String"
    assert "NextToken" not in response

    response = client.describe_parameters(
        ParameterFilters=[{"Key": "Path", "Option": "Recursive", "Values": ["/fo"]}]
    )

    parameters = response["Parameters"]
    assert len(parameters) == 0
    assert "NextToken" not in response

    response = client.describe_parameters(
        ParameterFilters=[{"Key": "Path", "Option": "Recursive", "Values": ["/"]}]
    )

    parameters = response["Parameters"]
    assert len(parameters) == 5
    assert "NextToken" not in response

    response = client.describe_parameters(
        ParameterFilters=[
            {"Key": "Path", "Option": "Recursive", "Values": ["/foo", "/bar"]}
        ]
    )

    parameters = response["Parameters"]
    assert len(parameters) == 4
    assert {parameter["Name"] for parameter in response["Parameters"]} == {
        "/foo/name1",
        "/foo/name2",
        "/bar/name3",
        "/bar/name3/name4",
    }
    assert "NextToken" not in response

    response = client.describe_parameters(
        ParameterFilters=[{"Key": "Path", "Option": "Recursive", "Values": ["/foo/"]}]
    )

    parameters = response["Parameters"]
    assert len(parameters) == 2
    assert {parameter["Name"] for parameter in response["Parameters"]} == {
        "/foo/name1",
        "/foo/name2",
    }
    assert "NextToken" not in response

    response = client.describe_parameters(
        ParameterFilters=[
            {"Key": "Path", "Option": "Recursive", "Values": ["/bar/name3"]}
        ]
    )

    parameters = response["Parameters"]
    assert len(parameters) == 1
    assert parameters[0]["Name"] == "/bar/name3/name4"
    assert parameters[0]["Type"] == "String"
    assert "NextToken" not in response


@mock_aws
def test_describe_parameters_needs_param():
    client = boto3.client("ssm", region_name="us-east-1")
    with pytest.raises(ClientError) as client_err:
        client.describe_parameters(
            Filters=[{"Key": "Name", "Values": ["test"]}],
            ParameterFilters=[{"Key": "Name", "Values": ["test"]}],
        )
    assert client_err.value.response["Error"]["Message"] == (
        "You can use either Filters or ParameterFilters in a single request."
    )


@pytest.mark.parametrize(
    "filters,error_msg",
    [
        (
            [{"Key": "key"}],
            (
                "Member must satisfy regular expression pattern: "
                "tag:.+|Name|Type|KeyId|Path|Label|Tier"
            ),
        ),
        (
            [{"Key": "tag:" + "t" * 129}],
            "Member must have length less than or equal to 132",
        ),
        (
            [{"Key": "Name", "Option": "over 10 chars"}],
            "Member must have length less than or equal to 10",
        ),
        (
            [{"Key": "Name", "Values": ["test"] * 51}],
            "Member must have length less than or equal to 50",
        ),
        (
            [{"Key": "Name", "Values": ["t" * 1025]}],
            (
                "Member must have length less than or equal to 1024, "
                "Member must have length greater than or equal to 1"
            ),
        ),
        (
            [{"Key": "Name", "Option": "over 10 chars"}, {"Key": "key"}],
            "2 validation errors detected:",
        ),
        (
            [{"Key": "Label"}],
            (
                "The following filter key is not valid: Label. Valid "
                "filter keys include: [Path, Name, Type, KeyId, Tier]"
            ),
        ),
        (
            [{"Key": "Name"}],
            "The following filter values are missing : null for filter key Name",
        ),
        (
            [
                {"Key": "Name", "Values": ["test"]},
                {"Key": "Name", "Values": ["test test"]},
            ],
            (
                "The following filter is duplicated in the request: Name. "
                "A request can contain only one occurrence of a specific filter."
            ),
        ),
        (
            [{"Key": "Path", "Values": ["/aws", "/ssm"]}],
            (
                "Filters for common parameters can't be prefixed with "
                '"aws" or "ssm" (case-insensitive).'
            ),
        ),
        (
            [{"Key": "Path", "Option": "Equals", "Values": ["test"]}],
            (
                "The following filter option is not valid: Equals. "
                "Valid options include: [Recursive, OneLevel]"
            ),
        ),
        (
            [{"Key": "Tier", "Values": ["test"]}],
            (
                "The following filter value is not valid: test. Valid "
                "values include: [Standard, Advanced, Intelligent-Tiering]"
            ),
        ),
        (
            [{"Key": "Type", "Values": ["test"]}],
            (
                "The following filter value is not valid: test. Valid "
                "values include: [String, StringList, SecureString]"
            ),
        ),
        (
            [{"Key": "Name", "Option": "option", "Values": ["test"]}],
            (
                "The following filter option is not valid: option. Valid "
                "options include: [BeginsWith, Equals]."
            ),
        ),
    ],
)
@mock_aws
def test_describe_parameters_invalid_parameter_filters(filters, error_msg):
    client = boto3.client("ssm", region_name="us-east-1")

    with pytest.raises(ClientError) as e:
        client.describe_parameters(ParameterFilters=filters)
    assert error_msg in e.value.response["Error"]["Message"]


@pytest.mark.parametrize("value", ["/###", "//", "test"])
@mock_aws
def test_describe_parameters_invalid_path(value):
    client = boto3.client("ssm", region_name="us-east-1")

    with pytest.raises(ClientError) as e:
        client.describe_parameters(
            ParameterFilters=[{"Key": "Path", "Values": [value]}]
        )
    msg = e.value.response["Error"]["Message"]
    assert "The parameter doesn't meet the parameter name requirements" in msg
    assert 'The parameter name must begin with a forward slash "/".' in msg
    assert 'It can\'t be prefixed with "aws" or "ssm" (case-insensitive).' in msg
    assert (
        "It must use only letters, numbers, or the following symbols: . "
        "(period), - (hyphen), _ (underscore)."
    ) in msg
    assert (
        "Special characters are not allowed. All sub-paths, if specified, "
        'must use the forward slash symbol "/".'
    ) in msg
    assert "Valid example: /get/parameters2-/by1./path0_." in msg


@mock_aws
def test_describe_parameters_attributes():
    client = boto3.client("ssm", region_name="us-east-1")

    client.put_parameter(
        Name="aa", Value="11", Type="String", Description="my description"
    )

    client.put_parameter(Name="bb", Value="22", Type="String")

    response = client.describe_parameters()

    parameters = response["Parameters"]
    assert len(parameters) == 2

    assert parameters[0]["Description"] == "my description"
    assert parameters[0]["Version"] == 1
    assert isinstance(parameters[0]["LastModifiedDate"], datetime.date)
    assert parameters[0]["LastModifiedUser"] == "N/A"

    assert "Description" not in parameters[1]
    assert parameters[1]["Version"] == 1


@mock_aws
def test_describe_parameters_tags():
    client = boto3.client("ssm", region_name="us-east-1")

    client.put_parameter(Name="/foo/bar", Value="spam", Type="String")
    client.put_parameter(
        Name="/spam/eggs",
        Value="eggs",
        Type="String",
        Tags=[{"Key": "spam", "Value": "eggs"}],
    )

    parameters = client.describe_parameters(
        ParameterFilters=[{"Key": "tag:spam", "Values": ["eggs"]}]
    )["Parameters"]
    assert len(parameters) == 1
    assert parameters[0]["Name"] == "/spam/eggs"

    # Verify we can filter by the existence of a tag
    filters = [{"Key": "tag:spam"}]
    response = client.describe_parameters(ParameterFilters=filters)
    assert len(response["Parameters"]) == 1
    assert {p["Name"] for p in response["Parameters"]} == set(["/spam/eggs"])


@mock_aws
def test_describe_parameters__multiple_tags():
    client = boto3.client("ssm", region_name="us-east-1")

    for x in "ab":
        client.put_parameter(
            Name=f"test_my_param_01_{x}",
            Value=f"Contents of param {x}",
            Type="String",
            Tags=[{"Key": "hello", "Value": "world"}, {"Key": "x", "Value": x}],
        )

    response = client.describe_parameters(
        ParameterFilters=[
            {"Key": "tag:x", "Option": "Equals", "Values": ["b"]},
            {"Key": "tag:hello", "Option": "Equals", "Values": ["world"]},
        ]
    )
    assert len(response["Parameters"]) == 1

    # Both params contains hello:world - ensure we also check the second tag, x=b
    response = client.describe_parameters(
        ParameterFilters=[
            {"Key": "tag:hello", "Option": "Equals", "Values": ["world"]},
            {"Key": "tag:x", "Option": "Equals", "Values": ["b"]},
        ]
    )
    assert len(response["Parameters"]) == 1

    # tag begins_with should also work
    assert (
        len(
            client.describe_parameters(
                ParameterFilters=[
                    {"Key": "tag:hello", "Option": "BeginsWith", "Values": ["w"]},
                ]
            )["Parameters"]
        )
        == 2
    )
    assert (
        len(
            client.describe_parameters(
                ParameterFilters=[
                    {"Key": "tag:x", "Option": "BeginsWith", "Values": ["a"]},
                ]
            )["Parameters"]
        )
        == 1
    )


@mock_aws
def test_tags_in_list_tags_from_resource_parameter():
    client = boto3.client("ssm", region_name="us-east-1")

    client.put_parameter(
        Name="/spam/eggs",
        Value="eggs",
        Type="String",
        Tags=[{"Key": "spam", "Value": "eggs"}],
    )

    tags = client.list_tags_for_resource(
        ResourceId="/spam/eggs", ResourceType="Parameter"
    )
    assert tags.get("TagList") == [{"Key": "spam", "Value": "eggs"}]

    client.delete_parameter(Name="/spam/eggs")

    with pytest.raises(ClientError) as ex:
        client.list_tags_for_resource(ResourceType="Parameter", ResourceId="/spam/eggs")
    assert ex.value.response["Error"]["Code"] == "InvalidResourceId"


@mock_aws
def test_tags_invalid_resource_id():
    client = boto3.client("ssm", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        client.list_tags_for_resource(ResourceType="Parameter", ResourceId="bar")
    assert ex.value.response["Error"]["Code"] == "InvalidResourceId"


@mock_aws
def test_tags_invalid_resource_type():
    client = boto3.client("ssm", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        client.list_tags_for_resource(ResourceType="foo", ResourceId="bar")
    assert ex.value.response["Error"]["Code"] == "InvalidResourceType"


@mock_aws
def test_get_parameter_invalid():
    client = client = boto3.client("ssm", region_name="us-east-1")
    response = client.get_parameters(Names=["invalid"], WithDecryption=False)

    assert len(response["Parameters"]) == 0
    assert len(response["InvalidParameters"]) == 1
    assert response["InvalidParameters"][0] == "invalid"


@mock_aws
def test_put_parameter_secure_default_kms():
    client = boto3.client("ssm", region_name="us-east-1")

    client.put_parameter(
        Name="test", Description="A test parameter", Value="value", Type="SecureString"
    )

    response = client.get_parameters(Names=["test"], WithDecryption=False)

    assert len(response["Parameters"]) == 1
    assert response["Parameters"][0]["Name"] == "test"
    assert response["Parameters"][0]["Value"] == "kms:alias/aws/ssm:value"
    assert response["Parameters"][0]["Type"] == "SecureString"

    response = client.get_parameters(Names=["test"], WithDecryption=True)

    assert len(response["Parameters"]) == 1
    assert response["Parameters"][0]["Name"] == "test"
    assert response["Parameters"][0]["Value"] == "value"
    assert response["Parameters"][0]["Type"] == "SecureString"


@mock_aws
def test_put_parameter_secure_custom_kms():
    client = boto3.client("ssm", region_name="us-east-1")

    client.put_parameter(
        Name="test",
        Description="A test parameter",
        Value="value",
        Type="SecureString",
        KeyId="foo",
    )

    response = client.get_parameters(Names=["test"], WithDecryption=False)

    assert len(response["Parameters"]) == 1
    assert response["Parameters"][0]["Name"] == "test"
    assert response["Parameters"][0]["Value"] == "kms:foo:value"
    assert response["Parameters"][0]["Type"] == "SecureString"

    response = client.get_parameters(Names=["test"], WithDecryption=True)

    assert len(response["Parameters"]) == 1
    assert response["Parameters"][0]["Name"] == "test"
    assert response["Parameters"][0]["Value"] == "value"
    assert response["Parameters"][0]["Type"] == "SecureString"


@mock_aws
def test_get_parameter_history():
    client = boto3.client("ssm", region_name="us-east-1")

    test_parameter_name = "test"

    for i in range(3):
        client.put_parameter(
            Name=test_parameter_name,
            Description=f"A test parameter version {i}",
            Value=f"value-{i}",
            Type="String",
            Overwrite=True,
        )

    response = client.get_parameter_history(Name=test_parameter_name)
    parameters_response = response["Parameters"]

    for index, param in enumerate(parameters_response):
        assert param["Name"] == test_parameter_name
        assert param["Type"] == "String"
        assert param["Value"] == f"value-{index}"
        assert param["Version"] == index + 1
        assert param["Description"] == f"A test parameter version {index}"
        assert param["Labels"] == []

    assert len(parameters_response) == 3


@mock_aws
def test_get_parameter_history_with_secure_string():
    client = boto3.client("ssm", region_name="us-east-1")

    test_parameter_name = "test"

    for i in range(3):
        client.put_parameter(
            Name=test_parameter_name,
            Description=f"A test parameter version {i}",
            Value=f"value-{i}",
            Type="SecureString",
            Overwrite=True,
        )

    for with_decryption in [True, False]:
        response = client.get_parameter_history(
            Name=test_parameter_name, WithDecryption=with_decryption
        )
        parameters_response = response["Parameters"]

        for index, param in enumerate(parameters_response):
            assert param["Name"] == test_parameter_name
            assert param["Type"] == "SecureString"
            expected_plaintext_value = f"value-{index}"
            if with_decryption:
                assert param["Value"] == expected_plaintext_value
            else:
                assert param["Value"] == (
                    f"kms:alias/aws/ssm:{expected_plaintext_value}"
                )
            assert param["Version"] == index + 1
            assert param["Description"] == f"A test parameter version {index}"

        assert len(parameters_response) == 3


@mock_aws
def test_label_parameter_version():
    client = boto3.client("ssm", region_name="us-east-1")

    test_parameter_name = "test"
    client.put_parameter(
        Name=test_parameter_name,
        Description="A test parameter",
        Value="value",
        Type="String",
    )

    response = client.label_parameter_version(
        Name=test_parameter_name, Labels=["test-label"]
    )
    assert response["InvalidLabels"] == []
    assert response["ParameterVersion"] == 1


@mock_aws
def test_label_parameter_version_with_specific_version():
    client = boto3.client("ssm", region_name="us-east-1")

    test_parameter_name = "test"
    client.put_parameter(
        Name=test_parameter_name,
        Description="A test parameter",
        Value="value",
        Type="String",
    )

    response = client.label_parameter_version(
        Name=test_parameter_name, ParameterVersion=1, Labels=["test-label"]
    )
    assert response["InvalidLabels"] == []
    assert response["ParameterVersion"] == 1


@mock_aws
def test_label_parameter_version_twice():
    client = boto3.client("ssm", region_name="us-east-1")

    test_parameter_name = "test"
    test_labels = ["test-label"]
    client.put_parameter(
        Name=test_parameter_name,
        Description="A test parameter",
        Value="value",
        Type="String",
    )

    response = client.label_parameter_version(
        Name=test_parameter_name, ParameterVersion=1, Labels=test_labels
    )
    assert response["InvalidLabels"] == []
    assert response["ParameterVersion"] == 1
    response = client.label_parameter_version(
        Name=test_parameter_name, ParameterVersion=1, Labels=test_labels
    )
    assert response["InvalidLabels"] == []
    assert response["ParameterVersion"] == 1

    response = client.get_parameter_history(Name=test_parameter_name)
    assert len(response["Parameters"]) == 1
    assert response["Parameters"][0]["Labels"] == test_labels


@mock_aws
def test_label_parameter_moving_versions():
    client = boto3.client("ssm", region_name="us-east-1")

    test_parameter_name = "test"
    test_labels = ["test-label"]

    for i in range(3):
        client.put_parameter(
            Name=test_parameter_name,
            Description=f"A test parameter version {i}",
            Value=f"value-{i}",
            Type="String",
            Overwrite=True,
        )

    response = client.label_parameter_version(
        Name=test_parameter_name, ParameterVersion=1, Labels=test_labels
    )
    assert response["InvalidLabels"] == []
    assert response["ParameterVersion"] == 1
    response = client.label_parameter_version(
        Name=test_parameter_name, ParameterVersion=2, Labels=test_labels
    )
    assert response["InvalidLabels"] == []
    assert response["ParameterVersion"] == 2

    response = client.get_parameter_history(Name=test_parameter_name)
    parameters_response = response["Parameters"]

    for index, param in enumerate(parameters_response):
        assert param["Name"] == test_parameter_name
        assert param["Type"] == "String"
        assert param["Value"] == f"value-{index}"
        assert param["Version"] == index + 1
        assert param["Description"] == f"A test parameter version {index}"
        labels = test_labels if param["Version"] == 2 else []
        assert param["Labels"] == labels

    assert len(parameters_response) == 3


@mock_aws
def test_label_parameter_moving_versions_complex():
    client = boto3.client("ssm", region_name="us-east-1")

    test_parameter_name = "test"

    for i in range(3):
        client.put_parameter(
            Name=test_parameter_name,
            Description=f"A test parameter version {i}",
            Value=f"value-{i}",
            Type="String",
            Overwrite=True,
        )

    response = client.label_parameter_version(
        Name=test_parameter_name,
        ParameterVersion=1,
        Labels=["test-label1", "test-label2", "test-label3"],
    )
    assert response["InvalidLabels"] == []
    assert response["ParameterVersion"] == 1
    response = client.label_parameter_version(
        Name=test_parameter_name,
        ParameterVersion=2,
        Labels=["test-label2", "test-label3"],
    )
    assert response["InvalidLabels"] == []
    assert response["ParameterVersion"] == 2

    response = client.get_parameter_history(Name=test_parameter_name)
    parameters_response = response["Parameters"]

    for index, param in enumerate(parameters_response):
        assert param["Name"] == test_parameter_name
        assert param["Type"] == "String"
        assert param["Value"] == f"value-{index}"
        assert param["Version"] == index + 1
        assert param["Description"] == f"A test parameter version {index}"
        labels = (
            ["test-label2", "test-label3"]
            if param["Version"] == 2
            else (["test-label1"] if param["Version"] == 1 else [])
        )
        assert param["Labels"] == labels

    assert len(parameters_response) == 3


@mock_aws
def test_label_parameter_version_exception_ten_labels_at_once():
    client = boto3.client("ssm", region_name="us-east-1")

    test_parameter_name = "test"
    test_labels = [
        "test-label1",
        "test-label2",
        "test-label3",
        "test-label4",
        "test-label5",
        "test-label6",
        "test-label7",
        "test-label8",
        "test-label9",
        "test-label10",
        "test-label11",
    ]

    client.put_parameter(
        Name=test_parameter_name,
        Description="A test parameter",
        Value="value",
        Type="String",
    )
    with pytest.raises(ClientError) as client_err:
        client.label_parameter_version(
            Name="test", ParameterVersion=1, Labels=test_labels
        )
    assert client_err.value.response["Error"]["Message"] == (
        "An error occurred (ParameterVersionLabelLimitExceeded) when "
        "calling the LabelParameterVersion operation: "
        "A parameter version can have maximum 10 labels."
        "Move one or more labels to another version and try again."
    )


@mock_aws
def test_label_parameter_version_exception_ten_labels_over_multiple_calls():
    client = boto3.client("ssm", region_name="us-east-1")

    test_parameter_name = "test"

    client.put_parameter(
        Name=test_parameter_name,
        Description="A test parameter",
        Value="value",
        Type="String",
    )
    client.label_parameter_version(
        Name=test_parameter_name,
        ParameterVersion=1,
        Labels=[
            "test-label1",
            "test-label2",
            "test-label3",
            "test-label4",
            "test-label5",
        ],
    )
    with pytest.raises(ClientError) as client_err:
        client.label_parameter_version(
            Name="test",
            ParameterVersion=1,
            Labels=[
                "test-label6",
                "test-label7",
                "test-label8",
                "test-label9",
                "test-label10",
                "test-label11",
            ],
        )
    assert client_err.value.response["Error"]["Message"] == (
        "An error occurred (ParameterVersionLabelLimitExceeded) when "
        "calling the LabelParameterVersion operation: "
        "A parameter version can have maximum 10 labels."
        "Move one or more labels to another version and try again."
    )


@mock_aws
def test_label_parameter_version_invalid_name():
    client = boto3.client("ssm", region_name="us-east-1")

    test_parameter_name = "test"

    with pytest.raises(ClientError) as client_err:
        client.label_parameter_version(Name=test_parameter_name, Labels=["test-label"])
    assert client_err.value.response["Error"]["Message"] == "Parameter test not found."


@mock_aws
def test_label_parameter_version_invalid_parameter_version():
    client = boto3.client("ssm", region_name="us-east-1")

    test_parameter_name = "test"
    client.put_parameter(
        Name=test_parameter_name,
        Description="A test parameter",
        Value="value",
        Type="String",
    )

    with pytest.raises(ClientError) as client_err:
        client.label_parameter_version(
            Name=test_parameter_name, Labels=["test-label"], ParameterVersion=5
        )
    assert client_err.value.response["Error"]["Message"] == (
        "Systems Manager could not find version 5 of test. "
        "Verify the version and try again."
    )


@mock_aws
def test_label_parameter_version_invalid_label():
    client = boto3.client("ssm", region_name="us-east-1")

    test_parameter_name = "test"
    client.put_parameter(
        Name=test_parameter_name,
        Description="A test parameter",
        Value="value",
        Type="String",
    )
    response = client.label_parameter_version(
        Name=test_parameter_name, ParameterVersion=1, Labels=["awsabc"]
    )
    assert response["InvalidLabels"] == ["awsabc"]

    response = client.label_parameter_version(
        Name=test_parameter_name, ParameterVersion=1, Labels=["ssmabc"]
    )
    assert response["InvalidLabels"] == ["ssmabc"]

    response = client.label_parameter_version(
        Name=test_parameter_name, ParameterVersion=1, Labels=["9abc"]
    )
    assert response["InvalidLabels"] == ["9abc"]

    response = client.label_parameter_version(
        Name=test_parameter_name, ParameterVersion=1, Labels=["abc/123"]
    )
    assert response["InvalidLabels"] == ["abc/123"]

    long_name = "a" * 101
    with pytest.raises(ClientError) as client_err:
        client.label_parameter_version(
            Name=test_parameter_name, ParameterVersion=1, Labels=[long_name]
        )
    assert client_err.value.response["Error"]["Message"] == (
        "1 validation error detected: "
        f"Value '[{long_name}]' at 'labels' failed to satisfy constraint: "
        "Member must satisfy constraint: "
        "[Member must have length less than or equal to 100, Member must "
        "have length greater than or equal to 1]"
    )


@mock_aws
def test_get_parameter_history_with_label():
    client = boto3.client("ssm", region_name="us-east-1")

    test_parameter_name = "test"
    test_labels = ["test-label"]

    for i in range(3):
        client.put_parameter(
            Name=test_parameter_name,
            Description=f"A test parameter version {i}",
            Value=f"value-{i}",
            Type="String",
            Overwrite=True,
        )

    client.label_parameter_version(
        Name=test_parameter_name, ParameterVersion=1, Labels=test_labels
    )

    response = client.get_parameter_history(Name=test_parameter_name)
    parameters_response = response["Parameters"]

    for index, param in enumerate(parameters_response):
        assert param["Name"] == test_parameter_name
        assert param["Type"] == "String"
        assert param["Value"] == f"value-{index}"
        assert param["Version"] == index + 1
        assert param["Description"] == f"A test parameter version {index}"
        labels = test_labels if param["Version"] == 1 else []
        assert param["Labels"] == labels

    assert len(parameters_response) == 3


@mock_aws
def test_get_parameter_history_with_label_non_latest():
    client = boto3.client("ssm", region_name="us-east-1")

    test_parameter_name = "test"
    test_labels = ["test-label"]

    for i in range(3):
        client.put_parameter(
            Name=test_parameter_name,
            Description=f"A test parameter version {i}",
            Value=f"value-{i}",
            Type="String",
            Overwrite=True,
        )

    client.label_parameter_version(
        Name=test_parameter_name, ParameterVersion=2, Labels=test_labels
    )

    response = client.get_parameter_history(Name=test_parameter_name)
    parameters_response = response["Parameters"]

    for index, param in enumerate(parameters_response):
        assert param["Name"] == test_parameter_name
        assert param["Type"] == "String"
        assert param["Value"] == f"value-{index}"
        assert param["Version"] == index + 1
        assert param["Description"] == f"A test parameter version {index}"
        labels = test_labels if param["Version"] == 2 else []
        assert param["Labels"] == labels

    assert len(parameters_response) == 3


@mock_aws
def test_get_parameter_history_with_label_latest_assumed():
    client = boto3.client("ssm", region_name="us-east-1")

    test_parameter_name = "test"
    test_labels = ["test-label"]

    for i in range(3):
        client.put_parameter(
            Name=test_parameter_name,
            Description=f"A test parameter version {i}",
            Value=f"value-{i}",
            Type="String",
            Overwrite=True,
        )

    client.label_parameter_version(Name=test_parameter_name, Labels=test_labels)

    response = client.get_parameter_history(Name=test_parameter_name)
    parameters_response = response["Parameters"]

    for index, param in enumerate(parameters_response):
        assert param["Name"] == test_parameter_name
        assert param["Type"] == "String"
        assert param["Value"] == f"value-{index}"
        assert param["Version"] == index + 1
        assert param["Description"] == f"A test parameter version {index}"
        labels = test_labels if param["Version"] == 3 else []
        assert param["Labels"] == labels

    assert len(parameters_response) == 3


@mock_aws
def test_get_parameter_history_missing_parameter():
    client = boto3.client("ssm", region_name="us-east-1")

    try:
        client.get_parameter_history(Name="test_noexist")
        raise RuntimeError("Should have failed")
    except botocore.exceptions.ClientError as err:
        assert err.operation_name == "GetParameterHistory"
        assert err.response["Error"]["Message"] == "Parameter test_noexist not found."


@mock_aws
def test_add_remove_list_tags_for_resource():
    client = boto3.client("ssm", region_name="us-east-1")

    with pytest.raises(ClientError) as ce:
        client.add_tags_to_resource(
            ResourceId="test",
            ResourceType="Parameter",
            Tags=[{"Key": "test-key", "Value": "test-value"}],
        )
    assert ce.value.response["Error"]["Code"] == "InvalidResourceId"

    client.put_parameter(Name="test", Value="value", Type="String")

    client.add_tags_to_resource(
        ResourceId="test",
        ResourceType="Parameter",
        Tags=[{"Key": "test-key", "Value": "test-value"}],
    )
    response = client.list_tags_for_resource(
        ResourceId="test", ResourceType="Parameter"
    )
    assert len(response["TagList"]) == 1
    assert response["TagList"][0]["Key"] == "test-key"
    assert response["TagList"][0]["Value"] == "test-value"

    client.remove_tags_from_resource(
        ResourceId="test", ResourceType="Parameter", TagKeys=["test-key"]
    )

    response = client.list_tags_for_resource(
        ResourceId="test", ResourceType="Parameter"
    )
    assert len(response["TagList"]) == 0


@mock_aws
def test_send_command():
    ssm_document = "AWS-RunShellScript"
    params = {"commands": ["#!/bin/bash\necho 'hello world'"]}

    client = boto3.client("ssm", region_name="us-east-1")
    # note the timeout is determined server side, so this is a simpler check.
    before = datetime.datetime.now()

    response = client.send_command(
        Comment="some comment",
        InstanceIds=["i-123456"],
        DocumentName=ssm_document,
        TimeoutSeconds=42,
        MaxConcurrency="360",
        MaxErrors="2",
        Parameters=params,
        OutputS3Region="us-east-2",
        OutputS3BucketName="the-bucket",
        OutputS3KeyPrefix="pref",
    )
    cmd = response["Command"]

    assert cmd["CommandId"] is not None
    assert cmd["Comment"] == "some comment"
    assert cmd["DocumentName"] == ssm_document
    assert cmd["Parameters"] == params

    assert cmd["OutputS3Region"] == "us-east-2"
    assert cmd["OutputS3BucketName"] == "the-bucket"
    assert cmd["OutputS3KeyPrefix"] == "pref"

    assert cmd["ExpiresAfter"] > before
    assert cmd["DeliveryTimedOutCount"] == 0

    assert cmd["TimeoutSeconds"] == 42
    assert cmd["MaxConcurrency"] == "360"
    assert cmd["MaxErrors"] == "2"

    # test sending a command without any optional parameters
    response = client.send_command(DocumentName=ssm_document)

    cmd = response["Command"]

    assert cmd["CommandId"] is not None
    assert cmd["DocumentName"] == ssm_document


@mock_aws
def test_list_commands():
    client = boto3.client("ssm", region_name="us-east-1")

    ssm_document = "AWS-RunShellScript"
    params = {"commands": ["#!/bin/bash\necho 'hello world'"]}

    response = client.send_command(
        InstanceIds=["i-123456"],
        DocumentName=ssm_document,
        Parameters=params,
        OutputS3Region="us-east-2",
        OutputS3BucketName="the-bucket",
        OutputS3KeyPrefix="pref",
    )

    cmd = response["Command"]
    cmd_id = cmd["CommandId"]

    # get the command by id
    response = client.list_commands(CommandId=cmd_id)

    cmds = response["Commands"]
    assert len(cmds) == 1
    assert cmds[0]["CommandId"] == cmd_id

    # add another command with the same instance id to test listing by
    # instance id
    client.send_command(InstanceIds=["i-123456"], DocumentName=ssm_document)

    response = client.list_commands(InstanceId="i-123456")

    cmds = response["Commands"]
    assert len(cmds) == 2

    for cmd in cmds:
        assert "i-123456" in cmd["InstanceIds"]
        assert cmd["DeliveryTimedOutCount"] == 0

    # test the error case for an invalid command id
    with pytest.raises(ClientError):
        response = client.list_commands(CommandId=str(uuid.uuid4()))


@mock_aws
def test_get_command_invocation():
    client = boto3.client("ssm", region_name="us-east-1")

    ssm_document = "AWS-RunShellScript"
    params = {"commands": ["#!/bin/bash\necho 'hello world'"]}

    response = client.send_command(
        InstanceIds=["i-123456", "i-234567", "i-345678"],
        DocumentName=ssm_document,
        Parameters=params,
        OutputS3Region="us-east-2",
        OutputS3BucketName="the-bucket",
        OutputS3KeyPrefix="pref",
    )

    cmd = response["Command"]
    cmd_id = cmd["CommandId"]

    instance_id = "i-345678"
    invocation_response = client.get_command_invocation(
        CommandId=cmd_id, InstanceId=instance_id, PluginName="aws:runShellScript"
    )

    assert invocation_response["CommandId"] == cmd_id
    assert invocation_response["InstanceId"] == instance_id

    # test the error case for an invalid instance id
    with pytest.raises(ClientError):
        invocation_response = client.get_command_invocation(
            CommandId=cmd_id, InstanceId="i-FAKE"
        )

    # test the error case for an invalid plugin name
    with pytest.raises(ClientError):
        invocation_response = client.get_command_invocation(
            CommandId=cmd_id, InstanceId=instance_id, PluginName="FAKE"
        )


@mock_aws
def test_get_command_invocations_by_instance_tag():
    ec2 = boto3.client("ec2", region_name="us-east-1")
    ssm = boto3.client("ssm", region_name="us-east-1")
    tag_specifications = [
        {"ResourceType": "instance", "Tags": [{"Key": "Name", "Value": "test-tag"}]}
    ]
    num_instances = 3
    resp = ec2.run_instances(
        ImageId=EXAMPLE_AMI_ID,
        MaxCount=num_instances,
        MinCount=num_instances,
        TagSpecifications=tag_specifications,
    )
    instance_ids = []
    for instance in resp["Instances"]:
        instance_ids.append(instance["InstanceId"])
    assert len(instance_ids) == num_instances

    command_id = ssm.send_command(
        DocumentName="AWS-RunShellScript",
        Targets=[{"Key": "tag:Name", "Values": ["test-tag"]}],
    )["Command"]["CommandId"]

    resp = ssm.list_commands(CommandId=command_id)
    assert resp["Commands"][0]["TargetCount"] == num_instances

    for instance_id in instance_ids:
        resp = ssm.get_command_invocation(CommandId=command_id, InstanceId=instance_id)
        assert resp["Status"] == "Success"


@mock_aws
def test_parameter_version_limit():
    client = boto3.client("ssm", region_name="us-east-1")
    parameter_name = "test-param"
    for i in range(PARAMETER_VERSION_LIMIT + 1):
        client.put_parameter(
            Name=parameter_name,
            Value=f"value-{(i+1)}",
            Type="String",
            Overwrite=True,
        )

    paginator = client.get_paginator("get_parameter_history")
    page_iterator = paginator.paginate(Name=parameter_name)
    parameter_history = list(
        item for page in page_iterator for item in page["Parameters"]
    )

    assert len(parameter_history) == PARAMETER_VERSION_LIMIT
    assert parameter_history[0]["Value"] == "value-2"
    latest_version_index = PARAMETER_VERSION_LIMIT - 1
    latest_version_value = f"value-{PARAMETER_VERSION_LIMIT + 1}"
    assert parameter_history[latest_version_index]["Value"] == latest_version_value


@mock_aws
def test_parameter_overwrite_fails_when_limit_reached_and_oldest_version_has_label():
    client = boto3.client("ssm", region_name="us-east-1")
    parameter_name = "test-param"
    for i in range(PARAMETER_VERSION_LIMIT):
        client.put_parameter(
            Name=parameter_name,
            Value=f"value-{(i+1)}",
            Type="String",
            Overwrite=True,
        )
    client.label_parameter_version(
        Name=parameter_name, ParameterVersion=1, Labels=["test-label"]
    )

    with pytest.raises(ClientError) as ex:
        client.put_parameter(
            Name=parameter_name, Value="new-value", Type="String", Overwrite=True
        )
    error = ex.value.response["Error"]
    assert error["Code"] == "ParameterMaxVersionLimitExceeded"
    assert parameter_name in error["Message"]
    assert "Version 1" in error["Message"]
    assert re.search(
        (
            r"the oldest version, can't be deleted because it has a label "
            "associated with it. Move the label to another version of the "
            "parameter, and try again."
        ),
        error["Message"],
    )


@mock_aws
def test_get_parameters_includes_invalid_parameter_when_requesting_invalid_version():
    client = boto3.client("ssm", region_name="us-east-1")
    parameter_name = "test-param"
    versions_to_create = 5

    for i in range(versions_to_create):
        client.put_parameter(
            Name=parameter_name,
            Value=f"value-{(i+1)}",
            Type="String",
            Overwrite=True,
        )

    response = client.get_parameters(
        Names=[
            f"test-param:{versions_to_create + 1}",
            f"test-param:{versions_to_create - 1}",
        ]
    )

    assert len(response["InvalidParameters"]) == 1
    assert response["InvalidParameters"][0] == f"test-param:{versions_to_create + 1}"

    assert len(response["Parameters"]) == 1
    assert response["Parameters"][0]["Name"] == "test-param"
    assert response["Parameters"][0]["Value"] == "value-4"
    assert response["Parameters"][0]["Type"] == "String"


@mock_aws
def test_get_parameters_includes_invalid_parameter_when_requesting_invalid_label():
    client = boto3.client("ssm", region_name="us-east-1")
    parameter_name = "test-param"
    versions_to_create = 5

    for i in range(versions_to_create):
        client.put_parameter(
            Name=parameter_name,
            Value=f"value-{(i+1)}",
            Type="String",
            Overwrite=True,
        )

    client.label_parameter_version(
        Name=parameter_name, ParameterVersion=1, Labels=["test-label"]
    )

    response = client.get_parameters(
        Names=[
            "test-param:test-label",
            "test-param:invalid-label",
            "test-param",
            "test-param:2",
        ]
    )

    assert len(response["InvalidParameters"]) == 1
    assert response["InvalidParameters"][0] == "test-param:invalid-label"

    assert len(response["Parameters"]) == 3


@mock_aws
def test_get_parameters_should_only_return_unique_requests():
    client = boto3.client("ssm", region_name="us-east-1")
    parameter_name = "test-param"

    client.put_parameter(Name=parameter_name, Value="value", Type="String")

    response = client.get_parameters(Names=["test-param", "test-param"])

    assert len(response["Parameters"]) == 1


@mock_aws
def test_get_parameter_history_should_throw_exception_when_MaxResults_is_too_large():
    client = boto3.client("ssm", region_name="us-east-1")
    parameter_name = "test-param"

    for _ in range(100):
        client.put_parameter(
            Name=parameter_name, Value="value", Type="String", Overwrite=True
        )

    with pytest.raises(ClientError) as ex:
        client.get_parameter_history(
            Name=parameter_name, MaxResults=PARAMETER_HISTORY_MAX_RESULTS + 1
        )

    error = ex.value.response["Error"]
    assert error["Code"] == "ValidationException"
    assert error["Message"] == (
        "1 validation error detected: "
        f"Value '{PARAMETER_HISTORY_MAX_RESULTS + 1}' at 'maxResults' "
        "failed to satisfy constraint: "
        "Member must have value less than or equal to 50."
    )


@mock_aws
def test_get_parameter_history_NextTokenImplementation():
    client = boto3.client("ssm", region_name="us-east-1")
    parameter_name = "test-param"

    for _ in range(100):
        client.put_parameter(
            Name=parameter_name, Value="value", Type="String", Overwrite=True
        )

    response = client.get_parameter_history(
        Name=parameter_name, MaxResults=PARAMETER_HISTORY_MAX_RESULTS
    )  # fetch first 50

    param_history = response["Parameters"]
    next_token = response.get("NextToken", None)

    while next_token is not None:
        response = client.get_parameter_history(
            Name=parameter_name, MaxResults=7, NextToken=next_token
        )  # fetch small amounts to test MaxResults can change
        param_history.extend(response["Parameters"])
        next_token = response.get("NextToken", None)

    assert len(param_history) == 100


@mock_aws
def test_get_parameter_history_exception_when_requesting_invalid_parameter():
    client = boto3.client("ssm", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        client.get_parameter_history(Name="invalid_parameter_name")

    error = ex.value.response["Error"]
    assert error["Code"] == "ParameterNotFound"
    assert error["Message"] == "Parameter invalid_parameter_name not found."
