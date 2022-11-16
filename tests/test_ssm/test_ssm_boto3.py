import string

import boto3
import botocore.exceptions
import sure  # noqa # pylint: disable=unused-import
import datetime
import uuid

from botocore.exceptions import ClientError
import pytest

from moto import mock_ec2, mock_ssm
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
from moto.ssm.models import PARAMETER_VERSION_LIMIT, PARAMETER_HISTORY_MAX_RESULTS
from tests import EXAMPLE_AMI_ID


@mock_ssm
def test_delete_parameter():
    client = boto3.client("ssm", region_name="us-east-1")

    client.put_parameter(
        Name="test", Description="A test parameter", Value="value", Type="String"
    )

    response = client.get_parameters(Names=["test"])
    len(response["Parameters"]).should.equal(1)

    client.delete_parameter(Name="test")

    response = client.get_parameters(Names=["test"])
    len(response["Parameters"]).should.equal(0)


@mock_ssm
def test_delete_nonexistent_parameter():
    client = boto3.client("ssm", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        client.delete_parameter(Name="test_noexist")
    ex.value.response["Error"]["Code"].should.equal("ParameterNotFound")
    ex.value.response["Error"]["Message"].should.equal(
        "Parameter test_noexist not found."
    )


@mock_ssm
def test_delete_parameters():
    client = boto3.client("ssm", region_name="us-east-1")

    client.put_parameter(
        Name="test", Description="A test parameter", Value="value", Type="String"
    )

    response = client.get_parameters(Names=["test"])
    len(response["Parameters"]).should.equal(1)

    result = client.delete_parameters(Names=["test", "invalid"])
    len(result["DeletedParameters"]).should.equal(1)
    len(result["InvalidParameters"]).should.equal(1)

    response = client.get_parameters(Names=["test"])
    len(response["Parameters"]).should.equal(0)


@mock_ssm
def test_get_parameters_by_path():
    client = boto3.client("ssm", region_name="us-east-1")

    client.put_parameter(
        Name="/foo/name1", Description="A test parameter", Value="value1", Type="String"
    )

    client.put_parameter(
        Name="/foo/name2", Description="A test parameter", Value="value2", Type="String"
    )

    client.put_parameter(
        Name="/bar/name3", Description="A test parameter", Value="value3", Type="String"
    )

    client.put_parameter(
        Name="/bar/name3/name4",
        Description="A test parameter",
        Value="value4",
        Type="String",
    )

    client.put_parameter(
        Name="/baz/name1",
        Description="A test parameter (list)",
        Value="value1,value2,value3",
        Type="StringList",
    )

    client.put_parameter(
        Name="/baz/name2", Description="A test parameter", Value="value1", Type="String"
    )

    client.put_parameter(
        Name="/baz/pwd",
        Description="A secure test parameter",
        Value="my_secret",
        Type="SecureString",
        KeyId="alias/aws/ssm",
    )

    client.put_parameter(
        Name="foo", Description="A test parameter", Value="bar", Type="String"
    )

    client.put_parameter(
        Name="baz", Description="A test parameter", Value="qux", Type="String"
    )

    response = client.get_parameters_by_path(Path="/", Recursive=False)
    len(response["Parameters"]).should.equal(2)
    {p["Value"] for p in response["Parameters"]}.should.equal(set(["bar", "qux"]))
    {p["ARN"] for p in response["Parameters"]}.should.equal(
        set(
            [
                f"arn:aws:ssm:us-east-1:{ACCOUNT_ID}:parameter/foo",
                f"arn:aws:ssm:us-east-1:{ACCOUNT_ID}:parameter/baz",
            ]
        )
    )
    {
        p["LastModifiedDate"].should.be.a(datetime.datetime)
        for p in response["Parameters"]
    }

    response = client.get_parameters_by_path(Path="/", Recursive=True)
    len(response["Parameters"]).should.equal(9)

    response = client.get_parameters_by_path(Path="/foo")
    len(response["Parameters"]).should.equal(2)
    {p["Value"] for p in response["Parameters"]}.should.equal(set(["value1", "value2"]))

    response = client.get_parameters_by_path(Path="/bar", Recursive=False)
    len(response["Parameters"]).should.equal(1)
    response["Parameters"][0]["Value"].should.equal("value3")

    response = client.get_parameters_by_path(Path="/bar", Recursive=True)
    len(response["Parameters"]).should.equal(2)
    {p["Value"] for p in response["Parameters"]}.should.equal(set(["value3", "value4"]))

    response = client.get_parameters_by_path(Path="/baz")
    len(response["Parameters"]).should.equal(3)

    filters = [{"Key": "Type", "Option": "Equals", "Values": ["StringList"]}]
    response = client.get_parameters_by_path(Path="/baz", ParameterFilters=filters)
    len(response["Parameters"]).should.equal(1)
    {p["Name"] for p in response["Parameters"]}.should.equal(set(["/baz/name1"]))

    # note: 'Option' is optional (default: 'Equals')
    filters = [{"Key": "Type", "Values": ["StringList"]}]
    response = client.get_parameters_by_path(Path="/baz", ParameterFilters=filters)
    len(response["Parameters"]).should.equal(1)
    {p["Name"] for p in response["Parameters"]}.should.equal(set(["/baz/name1"]))

    filters = [{"Key": "Type", "Option": "Equals", "Values": ["String"]}]
    response = client.get_parameters_by_path(Path="/baz", ParameterFilters=filters)
    len(response["Parameters"]).should.equal(1)
    {p["Name"] for p in response["Parameters"]}.should.equal(set(["/baz/name2"]))

    filters = [
        {"Key": "Type", "Option": "Equals", "Values": ["String", "SecureString"]}
    ]
    response = client.get_parameters_by_path(Path="/baz", ParameterFilters=filters)
    len(response["Parameters"]).should.equal(2)
    {p["Name"] for p in response["Parameters"]}.should.equal(
        set(["/baz/name2", "/baz/pwd"])
    )

    filters = [{"Key": "Type", "Option": "BeginsWith", "Values": ["String"]}]
    response = client.get_parameters_by_path(Path="/baz", ParameterFilters=filters)
    len(response["Parameters"]).should.equal(2)
    {p["Name"] for p in response["Parameters"]}.should.equal(
        set(["/baz/name1", "/baz/name2"])
    )

    filters = [{"Key": "KeyId", "Option": "Equals", "Values": ["alias/aws/ssm"]}]
    response = client.get_parameters_by_path(Path="/baz", ParameterFilters=filters)
    len(response["Parameters"]).should.equal(1)
    {p["Name"] for p in response["Parameters"]}.should.equal(set(["/baz/pwd"]))

    response = client.get_parameters_by_path(Path="/", Recursive=True, MaxResults=4)
    len(response["Parameters"]).should.equal(4)
    response["NextToken"].should.equal("4")
    response = client.get_parameters_by_path(
        Path="/", Recursive=True, MaxResults=4, NextToken=response["NextToken"]
    )
    len(response["Parameters"]).should.equal(4)
    response["NextToken"].should.equal("8")
    response = client.get_parameters_by_path(
        Path="/", Recursive=True, MaxResults=4, NextToken=response["NextToken"]
    )
    len(response["Parameters"]).should.equal(1)
    response.should_not.have.key("NextToken")

    filters = [{"Key": "Name", "Values": ["error"]}]
    client.get_parameters_by_path.when.called_with(
        Path="/baz", ParameterFilters=filters
    ).should.throw(
        ClientError,
        "The following filter key is not valid: Name. "
        "Valid filter keys include: [Type, KeyId].",
    )

    filters = [{"Key": "Path", "Values": ["/error"]}]
    client.get_parameters_by_path.when.called_with(
        Path="/baz", ParameterFilters=filters
    ).should.throw(
        ClientError,
        "The following filter key is not valid: Path. "
        "Valid filter keys include: [Type, KeyId].",
    )

    filters = [{"Key": "Tier", "Values": ["Standard"]}]
    client.get_parameters_by_path.when.called_with(
        Path="/baz", ParameterFilters=filters
    ).should.throw(
        ClientError,
        "The following filter key is not valid: Tier. "
        "Valid filter keys include: [Type, KeyId].",
    )

    # Label filter in get_parameters_by_path
    client.label_parameter_version(Name="/foo/name2", Labels=["Label1"])

    filters = [{"Key": "Label", "Values": ["Label1"]}]
    response = client.get_parameters_by_path(Path="/foo", ParameterFilters=filters)
    len(response["Parameters"]).should.equal(1)
    {p["Name"] for p in response["Parameters"]}.should.equal(set(["/foo/name2"]))


@pytest.mark.parametrize("name", ["test", "my-cool-parameter"])
@mock_ssm
def test_put_parameter(name):
    client = boto3.client("ssm", region_name="us-east-1")
    response = client.put_parameter(
        Name=name, Description="A test parameter", Value="value", Type="String"
    )

    response["Version"].should.equal(1)

    response = client.get_parameters(Names=[name], WithDecryption=False)

    len(response["Parameters"]).should.equal(1)
    response["Parameters"][0]["Name"].should.equal(name)
    response["Parameters"][0]["Value"].should.equal("value")
    response["Parameters"][0]["Type"].should.equal("String")
    response["Parameters"][0]["Version"].should.equal(1)
    response["Parameters"][0]["DataType"].should.equal("text")
    response["Parameters"][0]["LastModifiedDate"].should.be.a(datetime.datetime)
    response["Parameters"][0]["ARN"].should.equal(
        f"arn:aws:ssm:us-east-1:{ACCOUNT_ID}:parameter/{name}"
    )
    initial_modification_date = response["Parameters"][0]["LastModifiedDate"]

    try:
        client.put_parameter(
            Name=name, Description="desc 2", Value="value 2", Type="String"
        )
        raise RuntimeError("Should fail")
    except botocore.exceptions.ClientError as err:
        err.operation_name.should.equal("PutParameter")
        err.response["Error"]["Message"].should.equal(
            f"Parameter {name} already exists."
        )

    response = client.get_parameters(Names=[name], WithDecryption=False)

    # without overwrite nothing change
    len(response["Parameters"]).should.equal(1)
    response["Parameters"][0]["Name"].should.equal(name)
    response["Parameters"][0]["Value"].should.equal("value")
    response["Parameters"][0]["Type"].should.equal("String")
    response["Parameters"][0]["Version"].should.equal(1)
    response["Parameters"][0]["DataType"].should.equal("text")
    response["Parameters"][0]["LastModifiedDate"].should.equal(
        initial_modification_date
    )
    response["Parameters"][0]["ARN"].should.equal(
        f"arn:aws:ssm:us-east-1:{ACCOUNT_ID}:parameter/{name}"
    )
    new_data_type = "aws:ec2:image"

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

    response["Version"].should.equal(2)

    response = client.get_parameters(Names=[name], WithDecryption=False)

    # without overwrite nothing change
    len(response["Parameters"]).should.equal(1)
    response["Parameters"][0]["Name"].should.equal(name)
    response["Parameters"][0]["Value"].should.equal("value 3")
    response["Parameters"][0]["Type"].should.equal("String")
    response["Parameters"][0]["Version"].should.equal(2)
    response["Parameters"][0]["DataType"].should_not.equal("text")
    response["Parameters"][0]["DataType"].should.equal(new_data_type)
    response["Parameters"][0]["LastModifiedDate"].should_not.equal(
        initial_modification_date
    )
    response["Parameters"][0]["ARN"].should.equal(
        f"arn:aws:ssm:us-east-1:{ACCOUNT_ID}:parameter/{name}"
    )


@mock_ssm
def test_put_parameter_empty_string_value():
    client = boto3.client("ssm", region_name="us-east-1")
    with pytest.raises(ClientError) as e:
        client.put_parameter(Name="test_name", Value="", Type="String")
    ex = e.value
    ex.operation_name.should.equal("PutParameter")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("ValidationException")
    ex.response["Error"]["Message"].should.equal(
        "1 validation error detected: "
        "Value '' at 'value' failed to satisfy constraint: "
        "Member must have length greater than or equal to 1."
    )


@mock_ssm
def test_put_parameter_invalid_names():
    client = boto3.client("ssm", region_name="us-east-1")

    invalid_prefix_err = (
        'Parameter name: can\'t be prefixed with "aws" or "ssm" (case-insensitive).'
    )

    client.put_parameter.when.called_with(
        Name="ssm_test", Value="value", Type="String"
    ).should.throw(ClientError, invalid_prefix_err)

    client.put_parameter.when.called_with(
        Name="SSM_TEST", Value="value", Type="String"
    ).should.throw(ClientError, invalid_prefix_err)

    client.put_parameter.when.called_with(
        Name="aws_test", Value="value", Type="String"
    ).should.throw(ClientError, invalid_prefix_err)

    client.put_parameter.when.called_with(
        Name="AWS_TEST", Value="value", Type="String"
    ).should.throw(ClientError, invalid_prefix_err)

    ssm_path = "/ssm_test/path/to/var"
    client.put_parameter.when.called_with(
        Name=ssm_path, Value="value", Type="String"
    ).should.throw(
        ClientError,
        'Parameter name: can\'t be prefixed with "ssm" (case-insensitive). If formed as a path, it can consist of '
        "sub-paths divided by slash symbol; each sub-path can be formed as a mix of letters, numbers and the following "
        "3 symbols .-_",
    )

    ssm_path = "/SSM/PATH/TO/VAR"
    client.put_parameter.when.called_with(
        Name=ssm_path, Value="value", Type="String"
    ).should.throw(
        ClientError,
        'Parameter name: can\'t be prefixed with "ssm" (case-insensitive). If formed as a path, it can consist of '
        "sub-paths divided by slash symbol; each sub-path can be formed as a mix of letters, numbers and the following "
        "3 symbols .-_",
    )

    aws_path = "/aws_test/path/to/var"
    client.put_parameter.when.called_with(
        Name=aws_path, Value="value", Type="String"
    ).should.throw(ClientError, f"No access to reserved parameter name: {aws_path}.")

    aws_path = "/AWS/PATH/TO/VAR"
    client.put_parameter.when.called_with(
        Name=aws_path, Value="value", Type="String"
    ).should.throw(ClientError, f"No access to reserved parameter name: {aws_path}.")


@mock_ssm
def test_put_parameter_china():
    client = boto3.client("ssm", region_name="cn-north-1")

    response = client.put_parameter(
        Name="test", Description="A test parameter", Value="value", Type="String"
    )

    response["Version"].should.equal(1)


@mock_ssm
@pytest.mark.parametrize("bad_data_type", ["not_text", "not_ec2", "something weird"])
def test_put_parameter_invalid_data_type(bad_data_type):
    client = boto3.client("ssm", region_name="us-east-1")
    with pytest.raises(ClientError) as e:
        client.put_parameter(
            Name="test_name", Value="some_value", Type="String", DataType=bad_data_type
        )
    ex = e.value
    ex.operation_name.should.equal("PutParameter")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("ValidationException")
    ex.response["Error"]["Message"].should.equal(
        f"The following data type is not supported: {bad_data_type}"
        " (Data type names are all lowercase.)"
    )


@mock_ssm
def test_get_parameter():
    client = boto3.client("ssm", region_name="us-east-1")

    client.put_parameter(
        Name="test", Description="A test parameter", Value="value", Type="String"
    )

    response = client.get_parameter(Name="test", WithDecryption=False)

    response["Parameter"]["Name"].should.equal("test")
    response["Parameter"]["Value"].should.equal("value")
    response["Parameter"]["Type"].should.equal("String")
    response["Parameter"]["DataType"].should.equal("text")
    response["Parameter"]["LastModifiedDate"].should.be.a(datetime.datetime)
    response["Parameter"]["ARN"].should.equal(
        f"arn:aws:ssm:us-east-1:{ACCOUNT_ID}:parameter/test"
    )


@mock_ssm
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

    response["Parameter"]["Name"].should.equal("test-1")
    response["Parameter"]["Value"].should.equal("value")
    response["Parameter"]["Type"].should.equal("String")
    response["Parameter"]["DataType"].should.equal("text")
    response["Parameter"]["LastModifiedDate"].should.be.a(datetime.datetime)
    response["Parameter"]["ARN"].should.equal(
        f"arn:aws:ssm:us-east-1:{ACCOUNT_ID}:parameter/test-1"
    )

    response = client.get_parameter(Name="test-2:1", WithDecryption=False)
    response["Parameter"]["Name"].should.equal("test-2")
    response["Parameter"]["Value"].should.equal("value")
    response["Parameter"]["Type"].should.equal("String")
    response["Parameter"]["DataType"].should.equal("text")
    response["Parameter"]["LastModifiedDate"].should.be.a(datetime.datetime)
    response["Parameter"]["ARN"].should.equal(
        f"arn:aws:ssm:us-east-1:{ACCOUNT_ID}:parameter/test-2"
    )

    response = client.get_parameter(Name="test-2:test-label", WithDecryption=False)
    response["Parameter"]["Name"].should.equal("test-2")
    response["Parameter"]["Value"].should.equal("value")
    response["Parameter"]["Type"].should.equal("String")
    response["Parameter"]["DataType"].should.equal("text")
    response["Parameter"]["LastModifiedDate"].should.be.a(datetime.datetime)
    response["Parameter"]["ARN"].should.equal(
        f"arn:aws:ssm:us-east-1:{ACCOUNT_ID}:parameter/test-2"
    )

    with pytest.raises(ClientError) as ex:
        client.get_parameter(Name="test-2:2:3", WithDecryption=False)
    ex.value.response["Error"]["Code"].should.equal("ParameterNotFound")
    ex.value.response["Error"]["Message"].should.equal(
        "Parameter test-2:2:3 not found."
    )

    with pytest.raises(ClientError) as ex:
        client.get_parameter(Name="test-2:2", WithDecryption=False)
    ex.value.response["Error"]["Code"].should.equal("ParameterVersionNotFound")
    ex.value.response["Error"]["Message"].should.equal(
        "Systems Manager could not find version 2 of test-2. Verify the version and try again."
    )

    with pytest.raises(ClientError) as ex:
        client.get_parameter(Name="test-3:2", WithDecryption=False)
    ex.value.response["Error"]["Code"].should.equal("ParameterNotFound")
    ex.value.response["Error"]["Message"].should.equal("Parameter test-3:2 not found.")


@mock_ssm
def test_get_parameters_errors():
    client = boto3.client("ssm", region_name="us-east-1")

    ssm_parameters = {name: "value" for name in string.ascii_lowercase[:11]}

    for name, value in ssm_parameters.items():
        client.put_parameter(Name=name, Value=value, Type="String")

    with pytest.raises(ClientError) as e:
        client.get_parameters(Names=list(ssm_parameters.keys()))
    ex = e.value
    ex.operation_name.should.equal("GetParameters")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("ValidationException")
    all_keys = ", ".join(ssm_parameters.keys())
    ex.response["Error"]["Message"].should.equal(
        "1 validation error detected: "
        f"Value '[{all_keys}]' at 'names' failed to satisfy constraint: "
        "Member must have length less than or equal to 10."
    )


@mock_ssm
def test_get_nonexistant_parameter():
    client = boto3.client("ssm", region_name="us-east-1")

    try:
        client.get_parameter(Name="test_noexist", WithDecryption=False)
        raise RuntimeError("Should of failed")
    except botocore.exceptions.ClientError as err:
        err.operation_name.should.equal("GetParameter")
        err.response["Error"]["Message"].should.equal(
            "Parameter test_noexist not found."
        )


@mock_ssm
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
    parameters.should.have.length_of(1)
    parameters[0]["Name"].should.equal("test")
    parameters[0]["Type"].should.equal("String")
    parameters[0]["DataType"].should.equal("text")
    parameters[0]["AllowedPattern"].should.equal(r".*")


@mock_ssm
def test_describe_parameters_paging():
    client = boto3.client("ssm", region_name="us-east-1")

    for i in range(50):
        client.put_parameter(Name=f"param-{i}", Value=f"value-{i}", Type="String")

    response = client.describe_parameters()
    response["Parameters"].should.have.length_of(10)
    response["NextToken"].should.equal("10")

    response = client.describe_parameters(NextToken=response["NextToken"])
    response["Parameters"].should.have.length_of(10)
    response["NextToken"].should.equal("20")

    response = client.describe_parameters(NextToken=response["NextToken"])
    response["Parameters"].should.have.length_of(10)
    response["NextToken"].should.equal("30")

    response = client.describe_parameters(NextToken=response["NextToken"])
    response["Parameters"].should.have.length_of(10)
    response["NextToken"].should.equal("40")

    response = client.describe_parameters(NextToken=response["NextToken"])
    response["Parameters"].should.have.length_of(10)
    response["NextToken"].should.equal("50")

    response = client.describe_parameters(NextToken=response["NextToken"])
    response["Parameters"].should.have.length_of(0)
    response.should_not.have.key("NextToken")


@mock_ssm
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
    parameters.should.have.length_of(1)
    parameters[0]["Name"].should.equal("param-22")
    parameters[0]["Type"].should.equal("String")
    response.should_not.have.key("NextToken")


@mock_ssm
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
    parameters.should.have.length_of(10)
    parameters[0]["Type"].should.equal("SecureString")
    response.should.have.key("NextToken").which.should.equal("10")


@mock_ssm
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
    parameters.should.have.length_of(1)
    parameters[0]["Name"].should.equal("param-10")
    parameters[0]["Type"].should.equal("SecureString")
    response.should_not.have.key("NextToken")


@mock_ssm
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
    parameters.should.have.length_of(1)
    parameters[0]["Name"].should.equal("secure-param")
    parameters[0]["Type"].should.equal("SecureString")
    response.should_not.have.key("NextToken")

    response = client.describe_parameters(
        ParameterFilters=[{"Key": "KeyId", "Values": ["alias/custom"]}]
    )

    parameters = response["Parameters"]
    parameters.should.have.length_of(1)
    parameters[0]["Name"].should.equal("custom-secure-param")
    parameters[0]["Type"].should.equal("SecureString")
    response.should_not.have.key("NextToken")

    response = client.describe_parameters(
        ParameterFilters=[{"Key": "KeyId", "Option": "BeginsWith", "Values": ["alias"]}]
    )

    parameters = response["Parameters"]
    parameters.should.have.length_of(2)
    response.should_not.have.key("NextToken")


@mock_ssm
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
    parameters.should.have.length_of(1)
    parameters[0]["Name"].should.equal("param")
    parameters[0]["Type"].should.equal("String")
    response.should_not.have.key("NextToken")

    response = client.describe_parameters(
        ParameterFilters=[{"Key": "Name", "Values": ["/param"]}]
    )

    parameters = response["Parameters"]
    parameters.should.have.length_of(1)
    parameters[0]["Name"].should.equal("param")
    parameters[0]["Type"].should.equal("String")
    response.should_not.have.key("NextToken")

    response = client.describe_parameters(
        ParameterFilters=[{"Key": "Name", "Values": ["param-2"]}]
    )

    parameters = response["Parameters"]
    parameters.should.have.length_of(1)
    parameters[0]["Name"].should.equal("/param-2")
    parameters[0]["Type"].should.equal("String")
    response.should_not.have.key("NextToken")

    response = client.describe_parameters(
        ParameterFilters=[{"Key": "Name", "Option": "BeginsWith", "Values": ["param"]}]
    )

    parameters = response["Parameters"]
    parameters.should.have.length_of(2)
    response.should_not.have.key("NextToken")

    response = client.describe_parameters(
        ParameterFilters=[{"Key": "Name", "Option": "Contains", "Values": ["ram"]}]
    )

    parameters = response["Parameters"]
    parameters.should.have.length_of(3)
    response.should_not.have.key("NextToken")

    response = client.describe_parameters(
        ParameterFilters=[{"Key": "Name", "Option": "Contains", "Values": ["/tan"]}]
    )

    parameters = response["Parameters"]
    parameters.should.have.length_of(2)
    response.should_not.have.key("NextToken")


@mock_ssm
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
    parameters.should.have.length_of(0)
    response.should_not.have.key("NextToken")

    response = client.describe_parameters(
        ParameterFilters=[{"Key": "Path", "Values": ["/"]}]
    )

    parameters = response["Parameters"]
    parameters.should.have.length_of(1)
    parameters[0]["Name"].should.equal("foo")
    parameters[0]["Type"].should.equal("String")
    response.should_not.have.key("NextToken")

    response = client.describe_parameters(
        ParameterFilters=[{"Key": "Path", "Values": ["/", "/foo"]}]
    )

    parameters = response["Parameters"]
    parameters.should.have.length_of(3)
    {parameter["Name"] for parameter in response["Parameters"]}.should.equal(
        {"/foo/name1", "/foo/name2", "foo"}
    )
    response.should_not.have.key("NextToken")

    response = client.describe_parameters(
        ParameterFilters=[{"Key": "Path", "Values": ["/foo/"]}]
    )

    parameters = response["Parameters"]
    parameters.should.have.length_of(2)
    {parameter["Name"] for parameter in response["Parameters"]}.should.equal(
        {"/foo/name1", "/foo/name2"}
    )
    response.should_not.have.key("NextToken")

    response = client.describe_parameters(
        ParameterFilters=[
            {"Key": "Path", "Option": "OneLevel", "Values": ["/bar/name3"]}
        ]
    )

    parameters = response["Parameters"]
    parameters.should.have.length_of(1)
    parameters[0]["Name"].should.equal("/bar/name3/name4")
    parameters[0]["Type"].should.equal("String")
    response.should_not.have.key("NextToken")

    response = client.describe_parameters(
        ParameterFilters=[{"Key": "Path", "Option": "Recursive", "Values": ["/fo"]}]
    )

    parameters = response["Parameters"]
    parameters.should.have.length_of(0)
    response.should_not.have.key("NextToken")

    response = client.describe_parameters(
        ParameterFilters=[{"Key": "Path", "Option": "Recursive", "Values": ["/"]}]
    )

    parameters = response["Parameters"]
    parameters.should.have.length_of(5)
    response.should_not.have.key("NextToken")

    response = client.describe_parameters(
        ParameterFilters=[
            {"Key": "Path", "Option": "Recursive", "Values": ["/foo", "/bar"]}
        ]
    )

    parameters = response["Parameters"]
    parameters.should.have.length_of(4)
    {parameter["Name"] for parameter in response["Parameters"]}.should.equal(
        {"/foo/name1", "/foo/name2", "/bar/name3", "/bar/name3/name4"}
    )
    response.should_not.have.key("NextToken")

    response = client.describe_parameters(
        ParameterFilters=[{"Key": "Path", "Option": "Recursive", "Values": ["/foo/"]}]
    )

    parameters = response["Parameters"]
    parameters.should.have.length_of(2)
    {parameter["Name"] for parameter in response["Parameters"]}.should.equal(
        {"/foo/name1", "/foo/name2"}
    )
    response.should_not.have.key("NextToken")

    response = client.describe_parameters(
        ParameterFilters=[
            {"Key": "Path", "Option": "Recursive", "Values": ["/bar/name3"]}
        ]
    )

    parameters = response["Parameters"]
    parameters.should.have.length_of(1)
    parameters[0]["Name"].should.equal("/bar/name3/name4")
    parameters[0]["Type"].should.equal("String")
    response.should_not.have.key("NextToken")


@mock_ssm
def test_describe_parameters_needs_param():
    client = boto3.client("ssm", region_name="us-east-1")
    client.describe_parameters.when.called_with(
        Filters=[{"Key": "Name", "Values": ["test"]}],
        ParameterFilters=[{"Key": "Name", "Values": ["test"]}],
    ).should.throw(
        ClientError,
        "You can use either Filters or ParameterFilters in a single request.",
    )


@pytest.mark.parametrize(
    "filters,error_msg",
    [
        (
            [{"Key": "key"}],
            "Member must satisfy regular expression pattern: tag:.+|Name|Type|KeyId|Path|Label|Tier",
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
            "Member must have length less than or equal to 1024, Member must have length greater than or equal to 1",
        ),
        (
            [{"Key": "Name", "Option": "over 10 chars"}, {"Key": "key"}],
            "2 validation errors detected:",
        ),
        (
            [{"Key": "Label"}],
            "The following filter key is not valid: Label. Valid filter keys include: [Path, Name, Type, KeyId, Tier]",
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
            "The following filter is duplicated in the request: Name. A request can contain only one occurrence of a specific filter.",
        ),
        (
            [{"Key": "Path", "Values": ["/aws", "/ssm"]}],
            'Filters for common parameters can\'t be prefixed with "aws" or "ssm" (case-insensitive).',
        ),
        (
            [{"Key": "Path", "Option": "Equals", "Values": ["test"]}],
            "The following filter option is not valid: Equals. Valid options include: [Recursive, OneLevel]",
        ),
        (
            [{"Key": "Tier", "Values": ["test"]}],
            "The following filter value is not valid: test. Valid values include: [Standard, Advanced, Intelligent-Tiering]",
        ),
        (
            [{"Key": "Type", "Values": ["test"]}],
            "The following filter value is not valid: test. Valid values include: [String, StringList, SecureString]",
        ),
        (
            [{"Key": "Name", "Option": "option", "Values": ["test"]}],
            "The following filter option is not valid: option. Valid options include: [BeginsWith, Equals].",
        ),
    ],
)
@mock_ssm
def test_describe_parameters_invalid_parameter_filters(filters, error_msg):
    client = boto3.client("ssm", region_name="us-east-1")

    with pytest.raises(ClientError) as e:
        client.describe_parameters(ParameterFilters=filters)
    e.value.response["Error"]["Message"].should.contain(error_msg)


@pytest.mark.parametrize("value", ["/###", "//", "test"])
@mock_ssm
def test_describe_parameters_invalid_path(value):
    client = boto3.client("ssm", region_name="us-east-1")

    with pytest.raises(ClientError) as e:
        client.describe_parameters(
            ParameterFilters=[{"Key": "Path", "Values": [value]}]
        )
    msg = e.value.response["Error"]["Message"]
    msg.should.contain("The parameter doesn't meet the parameter name requirements")
    msg.should.contain('The parameter name must begin with a forward slash "/".')
    msg.should.contain('It can\'t be prefixed with "aws" or "ssm" (case-insensitive).')
    msg.should.contain(
        "It must use only letters, numbers, or the following symbols: . (period), - (hyphen), _ (underscore)."
    )
    msg.should.contain(
        'Special characters are not allowed. All sub-paths, if specified, must use the forward slash symbol "/".'
    )
    msg.should.contain("Valid example: /get/parameters2-/by1./path0_.")


@mock_ssm
def test_describe_parameters_attributes():
    client = boto3.client("ssm", region_name="us-east-1")

    client.put_parameter(
        Name="aa", Value="11", Type="String", Description="my description"
    )

    client.put_parameter(Name="bb", Value="22", Type="String")

    response = client.describe_parameters()

    parameters = response["Parameters"]
    parameters.should.have.length_of(2)

    parameters[0]["Description"].should.equal("my description")
    parameters[0]["Version"].should.equal(1)
    parameters[0]["LastModifiedDate"].should.be.a(datetime.date)
    parameters[0]["LastModifiedUser"].should.equal("N/A")

    parameters[1].should_not.have.key("Description")
    parameters[1]["Version"].should.equal(1)


@mock_ssm
def test_describe_parameters_tags():
    client = boto3.client("ssm", region_name="us-east-1")

    client.put_parameter(Name="/foo/bar", Value="spam", Type="String")
    client.put_parameter(
        Name="/spam/eggs",
        Value="eggs",
        Type="String",
        Tags=[{"Key": "spam", "Value": "eggs"}],
    )

    response = client.describe_parameters(
        ParameterFilters=[{"Key": "tag:spam", "Values": ["eggs"]}]
    )

    parameters = response["Parameters"]
    parameters.should.have.length_of(1)

    parameters[0]["Name"].should.equal("/spam/eggs")


@mock_ssm
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


@mock_ssm
def test_tags_invalid_resource_id():
    client = boto3.client("ssm", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        client.list_tags_for_resource(ResourceType="Parameter", ResourceId="bar")
    assert ex.value.response["Error"]["Code"] == "InvalidResourceId"


@mock_ssm
def test_tags_invalid_resource_type():
    client = boto3.client("ssm", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        client.list_tags_for_resource(ResourceType="foo", ResourceId="bar")
    assert ex.value.response["Error"]["Code"] == "InvalidResourceType"


@mock_ssm
def test_get_parameter_invalid():
    client = client = boto3.client("ssm", region_name="us-east-1")
    response = client.get_parameters(Names=["invalid"], WithDecryption=False)

    len(response["Parameters"]).should.equal(0)
    len(response["InvalidParameters"]).should.equal(1)
    response["InvalidParameters"][0].should.equal("invalid")


@mock_ssm
def test_put_parameter_secure_default_kms():
    client = boto3.client("ssm", region_name="us-east-1")

    client.put_parameter(
        Name="test", Description="A test parameter", Value="value", Type="SecureString"
    )

    response = client.get_parameters(Names=["test"], WithDecryption=False)

    len(response["Parameters"]).should.equal(1)
    response["Parameters"][0]["Name"].should.equal("test")
    response["Parameters"][0]["Value"].should.equal("kms:alias/aws/ssm:value")
    response["Parameters"][0]["Type"].should.equal("SecureString")

    response = client.get_parameters(Names=["test"], WithDecryption=True)

    len(response["Parameters"]).should.equal(1)
    response["Parameters"][0]["Name"].should.equal("test")
    response["Parameters"][0]["Value"].should.equal("value")
    response["Parameters"][0]["Type"].should.equal("SecureString")


@mock_ssm
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

    len(response["Parameters"]).should.equal(1)
    response["Parameters"][0]["Name"].should.equal("test")
    response["Parameters"][0]["Value"].should.equal("kms:foo:value")
    response["Parameters"][0]["Type"].should.equal("SecureString")

    response = client.get_parameters(Names=["test"], WithDecryption=True)

    len(response["Parameters"]).should.equal(1)
    response["Parameters"][0]["Name"].should.equal("test")
    response["Parameters"][0]["Value"].should.equal("value")
    response["Parameters"][0]["Type"].should.equal("SecureString")


@mock_ssm
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
        param["Name"].should.equal(test_parameter_name)
        param["Type"].should.equal("String")
        param["Value"].should.equal(f"value-{index}")
        param["Version"].should.equal(index + 1)
        param["Description"].should.equal(f"A test parameter version {index}")
        param["Labels"].should.equal([])

    len(parameters_response).should.equal(3)


@mock_ssm
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
            param["Name"].should.equal(test_parameter_name)
            param["Type"].should.equal("SecureString")
            expected_plaintext_value = f"value-{index}"
            if with_decryption:
                param["Value"].should.equal(expected_plaintext_value)
            else:
                param["Value"].should.equal(
                    f"kms:alias/aws/ssm:{expected_plaintext_value}"
                )
            param["Version"].should.equal(index + 1)
            param["Description"].should.equal(f"A test parameter version {index}")

        len(parameters_response).should.equal(3)


@mock_ssm
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
    response["InvalidLabels"].should.equal([])
    response["ParameterVersion"].should.equal(1)


@mock_ssm
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
    response["InvalidLabels"].should.equal([])
    response["ParameterVersion"].should.equal(1)


@mock_ssm
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
    response["InvalidLabels"].should.equal([])
    response["ParameterVersion"].should.equal(1)
    response = client.label_parameter_version(
        Name=test_parameter_name, ParameterVersion=1, Labels=test_labels
    )
    response["InvalidLabels"].should.equal([])
    response["ParameterVersion"].should.equal(1)

    response = client.get_parameter_history(Name=test_parameter_name)
    len(response["Parameters"]).should.equal(1)
    response["Parameters"][0]["Labels"].should.equal(test_labels)


@mock_ssm
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
    response["InvalidLabels"].should.equal([])
    response["ParameterVersion"].should.equal(1)
    response = client.label_parameter_version(
        Name=test_parameter_name, ParameterVersion=2, Labels=test_labels
    )
    response["InvalidLabels"].should.equal([])
    response["ParameterVersion"].should.equal(2)

    response = client.get_parameter_history(Name=test_parameter_name)
    parameters_response = response["Parameters"]

    for index, param in enumerate(parameters_response):
        param["Name"].should.equal(test_parameter_name)
        param["Type"].should.equal("String")
        param["Value"].should.equal(f"value-{index}")
        param["Version"].should.equal(index + 1)
        param["Description"].should.equal(f"A test parameter version {index}")
        labels = test_labels if param["Version"] == 2 else []
        param["Labels"].should.equal(labels)

    len(parameters_response).should.equal(3)


@mock_ssm
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
    response["InvalidLabels"].should.equal([])
    response["ParameterVersion"].should.equal(1)
    response = client.label_parameter_version(
        Name=test_parameter_name,
        ParameterVersion=2,
        Labels=["test-label2", "test-label3"],
    )
    response["InvalidLabels"].should.equal([])
    response["ParameterVersion"].should.equal(2)

    response = client.get_parameter_history(Name=test_parameter_name)
    parameters_response = response["Parameters"]

    for index, param in enumerate(parameters_response):
        param["Name"].should.equal(test_parameter_name)
        param["Type"].should.equal("String")
        param["Value"].should.equal(f"value-{index}")
        param["Version"].should.equal(index + 1)
        param["Description"].should.equal(f"A test parameter version {index}")
        labels = (
            ["test-label2", "test-label3"]
            if param["Version"] == 2
            else (["test-label1"] if param["Version"] == 1 else [])
        )
        param["Labels"].should.equal(labels)

    len(parameters_response).should.equal(3)


@mock_ssm
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
    client.label_parameter_version.when.called_with(
        Name="test", ParameterVersion=1, Labels=test_labels
    ).should.throw(
        ClientError,
        "An error occurred (ParameterVersionLabelLimitExceeded) when calling the LabelParameterVersion operation: "
        "A parameter version can have maximum 10 labels."
        "Move one or more labels to another version and try again.",
    )


@mock_ssm
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
    client.label_parameter_version.when.called_with(
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
    ).should.throw(
        ClientError,
        "An error occurred (ParameterVersionLabelLimitExceeded) when calling the LabelParameterVersion operation: "
        "A parameter version can have maximum 10 labels."
        "Move one or more labels to another version and try again.",
    )


@mock_ssm
def test_label_parameter_version_invalid_name():
    client = boto3.client("ssm", region_name="us-east-1")

    test_parameter_name = "test"

    client.label_parameter_version.when.called_with(
        Name=test_parameter_name, Labels=["test-label"]
    ).should.throw(
        ClientError,
        "An error occurred (ParameterNotFound) when calling the LabelParameterVersion operation: "
        "Parameter test not found.",
    )


@mock_ssm
def test_label_parameter_version_invalid_parameter_version():
    client = boto3.client("ssm", region_name="us-east-1")

    test_parameter_name = "test"
    client.put_parameter(
        Name=test_parameter_name,
        Description="A test parameter",
        Value="value",
        Type="String",
    )

    client.label_parameter_version.when.called_with(
        Name=test_parameter_name, Labels=["test-label"], ParameterVersion=5
    ).should.throw(
        ClientError,
        "An error occurred (ParameterVersionNotFound) when calling the LabelParameterVersion operation: "
        "Systems Manager could not find version 5 of test. "
        "Verify the version and try again.",
    )


@mock_ssm
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
    response["InvalidLabels"].should.equal(["awsabc"])

    response = client.label_parameter_version(
        Name=test_parameter_name, ParameterVersion=1, Labels=["ssmabc"]
    )
    response["InvalidLabels"].should.equal(["ssmabc"])

    response = client.label_parameter_version(
        Name=test_parameter_name, ParameterVersion=1, Labels=["9abc"]
    )
    response["InvalidLabels"].should.equal(["9abc"])

    response = client.label_parameter_version(
        Name=test_parameter_name, ParameterVersion=1, Labels=["abc/123"]
    )
    response["InvalidLabels"].should.equal(["abc/123"])

    long_name = "a" * 101
    client.label_parameter_version.when.called_with(
        Name=test_parameter_name, ParameterVersion=1, Labels=[long_name]
    ).should.throw(
        ClientError,
        "1 validation error detected: "
        f"Value '[{long_name}]' at 'labels' failed to satisfy constraint: "
        "Member must satisfy constraint: "
        "[Member must have length less than or equal to 100, Member must have length greater than or equal to 1]",
    )


@mock_ssm
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
        param["Name"].should.equal(test_parameter_name)
        param["Type"].should.equal("String")
        param["Value"].should.equal(f"value-{index}")
        param["Version"].should.equal(index + 1)
        param["Description"].should.equal(f"A test parameter version {index}")
        labels = test_labels if param["Version"] == 1 else []
        param["Labels"].should.equal(labels)

    len(parameters_response).should.equal(3)


@mock_ssm
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
        param["Name"].should.equal(test_parameter_name)
        param["Type"].should.equal("String")
        param["Value"].should.equal(f"value-{index}")
        param["Version"].should.equal(index + 1)
        param["Description"].should.equal(f"A test parameter version {index}")
        labels = test_labels if param["Version"] == 2 else []
        param["Labels"].should.equal(labels)

    len(parameters_response).should.equal(3)


@mock_ssm
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
        param["Name"].should.equal(test_parameter_name)
        param["Type"].should.equal("String")
        param["Value"].should.equal(f"value-{index}")
        param["Version"].should.equal(index + 1)
        param["Description"].should.equal(f"A test parameter version {index}")
        labels = test_labels if param["Version"] == 3 else []
        param["Labels"].should.equal(labels)

    len(parameters_response).should.equal(3)


@mock_ssm
def test_get_parameter_history_missing_parameter():
    client = boto3.client("ssm", region_name="us-east-1")

    try:
        client.get_parameter_history(Name="test_noexist")
        raise RuntimeError("Should have failed")
    except botocore.exceptions.ClientError as err:
        err.operation_name.should.equal("GetParameterHistory")
        err.response["Error"]["Message"].should.equal(
            "Parameter test_noexist not found."
        )


@mock_ssm
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
    len(response["TagList"]).should.equal(1)
    response["TagList"][0]["Key"].should.equal("test-key")
    response["TagList"][0]["Value"].should.equal("test-value")

    client.remove_tags_from_resource(
        ResourceId="test", ResourceType="Parameter", TagKeys=["test-key"]
    )

    response = client.list_tags_for_resource(
        ResourceId="test", ResourceType="Parameter"
    )
    len(response["TagList"]).should.equal(0)


@mock_ssm
def test_send_command():
    ssm_document = "AWS-RunShellScript"
    params = {"commands": ["#!/bin/bash\necho 'hello world'"]}

    client = boto3.client("ssm", region_name="us-east-1")
    # note the timeout is determined server side, so this is a simpler check.
    before = datetime.datetime.now()

    response = client.send_command(
        InstanceIds=["i-123456"],
        DocumentName=ssm_document,
        Parameters=params,
        OutputS3Region="us-east-2",
        OutputS3BucketName="the-bucket",
        OutputS3KeyPrefix="pref",
    )
    cmd = response["Command"]

    cmd["CommandId"].should_not.be(None)
    cmd["DocumentName"].should.equal(ssm_document)
    cmd["Parameters"].should.equal(params)

    cmd["OutputS3Region"].should.equal("us-east-2")
    cmd["OutputS3BucketName"].should.equal("the-bucket")
    cmd["OutputS3KeyPrefix"].should.equal("pref")

    cmd["ExpiresAfter"].should.be.greater_than(before)
    cmd["DeliveryTimedOutCount"].should.equal(0)

    # test sending a command without any optional parameters
    response = client.send_command(DocumentName=ssm_document)

    cmd = response["Command"]

    cmd["CommandId"].should_not.be(None)
    cmd["DocumentName"].should.equal(ssm_document)


@mock_ssm
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
    len(cmds).should.equal(1)
    cmds[0]["CommandId"].should.equal(cmd_id)

    # add another command with the same instance id to test listing by
    # instance id
    client.send_command(InstanceIds=["i-123456"], DocumentName=ssm_document)

    response = client.list_commands(InstanceId="i-123456")

    cmds = response["Commands"]
    len(cmds).should.equal(2)

    for cmd in cmds:
        cmd["InstanceIds"].should.contain("i-123456")
        cmd.should.have.key("DeliveryTimedOutCount").equals(0)

    # test the error case for an invalid command id
    with pytest.raises(ClientError):
        response = client.list_commands(CommandId=str(uuid.uuid4()))


@mock_ssm
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

    invocation_response["CommandId"].should.equal(cmd_id)
    invocation_response["InstanceId"].should.equal(instance_id)

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


@mock_ec2
@mock_ssm
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
    instance_ids.should.have.length_of(num_instances)

    command_id = ssm.send_command(
        DocumentName="AWS-RunShellScript",
        Targets=[{"Key": "tag:Name", "Values": ["test-tag"]}],
    )["Command"]["CommandId"]

    resp = ssm.list_commands(CommandId=command_id)
    resp["Commands"][0]["TargetCount"].should.equal(num_instances)

    for instance_id in instance_ids:
        resp = ssm.get_command_invocation(CommandId=command_id, InstanceId=instance_id)
        resp["Status"].should.equal("Success")


@mock_ssm
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

    len(parameter_history).should.equal(PARAMETER_VERSION_LIMIT)
    parameter_history[0]["Value"].should.equal("value-2")
    latest_version_index = PARAMETER_VERSION_LIMIT - 1
    latest_version_value = f"value-{PARAMETER_VERSION_LIMIT + 1}"
    parameter_history[latest_version_index]["Value"].should.equal(latest_version_value)


@mock_ssm
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
    error["Code"].should.equal("ParameterMaxVersionLimitExceeded")
    error["Message"].should.contain(parameter_name)
    error["Message"].should.contain("Version 1")
    error["Message"].should.match(
        r"the oldest version, can't be deleted because it has a label associated with it. Move the label to another version of the parameter, and try again."
    )


@mock_ssm
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

    len(response["InvalidParameters"]).should.equal(1)
    response["InvalidParameters"][0].should.equal(
        f"test-param:{versions_to_create + 1}"
    )

    len(response["Parameters"]).should.equal(1)
    response["Parameters"][0]["Name"].should.equal("test-param")
    response["Parameters"][0]["Value"].should.equal("value-4")
    response["Parameters"][0]["Type"].should.equal("String")


@mock_ssm
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

    len(response["InvalidParameters"]).should.equal(1)
    response["InvalidParameters"][0].should.equal("test-param:invalid-label")

    len(response["Parameters"]).should.equal(3)


@mock_ssm
def test_get_parameters_should_only_return_unique_requests():
    client = boto3.client("ssm", region_name="us-east-1")
    parameter_name = "test-param"

    client.put_parameter(Name=parameter_name, Value="value", Type="String")

    response = client.get_parameters(Names=["test-param", "test-param"])

    len(response["Parameters"]).should.equal(1)


@mock_ssm
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
    error["Code"].should.equal("ValidationException")
    error["Message"].should.equal(
        "1 validation error detected: "
        f"Value '{PARAMETER_HISTORY_MAX_RESULTS + 1}' at 'maxResults' failed to satisfy constraint: "
        "Member must have value less than or equal to 50."
    )


@mock_ssm
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

    len(param_history).should.equal(100)


@mock_ssm
def test_get_parameter_history_exception_when_requesting_invalid_parameter():
    client = boto3.client("ssm", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        client.get_parameter_history(Name="invalid_parameter_name")

    error = ex.value.response["Error"]
    error["Code"].should.equal("ParameterNotFound")
    error["Message"].should.equal("Parameter invalid_parameter_name not found.")
